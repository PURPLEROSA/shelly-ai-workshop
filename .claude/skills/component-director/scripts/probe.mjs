#!/usr/bin/env node
/*
  probe.mjs — put a piece through its states in a real browser, photograph each one, and check the contract.

  node probe.mjs piece.html                       default gestures: hover, sweep, press, hold, drag, throw, leave, keys
  node probe.mjs http://localhost:5173/demo       a piece running in a dev server (React, Vue, anything)
  node probe.mjs piece.html --out probe/          where sheet.png and report.json go (default: ./probe-<name>/)
  node probe.mjs piece.html --steps steps.json    your own gestures in place of the default set (format below)
  node probe.mjs piece.html --rtl                 add a pass with <html dir="rtl">
  node probe.mjs piece.html --variant he=?lang=he add a pass with this query string (repeatable)
  node probe.mjs piece.html --target ".knob"      aim the gestures at this element
  node probe.mjs piece.html --size 1200x750 --root "[data-piece]" --cols 4 --thumb 420 --strict

  What it looks for on the page
    [data-piece]        the root of the piece. Required (or pass --root).
    data-ambient        on the root, if the piece moves at rest on purpose.
    data-grab           on the element people press and drag. Gestures are aimed at it; without it they go to a
                        slider or switch inside the piece if there is one, and otherwise to the piece as a whole.
    window.PIECE        optional handle: { scrub(p), set(p) }. scrub(p) draws the settled state for p in 0..1 at once,
                        set(p) goes there the way a person would see it. With scrub the probe photographs the
                        in-betweens and proves the same p always gives the same picture.

  What it reports
    FAIL  script errors, no root, sideways overflow on a phone
    WARN  no response to any input, never settles, a loop that runs while nothing moves or off screen,
          no keyboard path or no visible focus, motion under prefers-reduced-motion, slow frames, a drag that
          selects text, mouse-only input,
          text under 11 px or targets under 36 px on a phone, requests to other hosts
    Exit code is 1 on any FAIL (and on any WARN with --strict), so it can gate a build.

  Steps file: a JSON array. Positions are fractions of the gesture target's box, [0,0] top left, [1,1] bottom right.
    {"move":[0.5,0.5]} {"down":[0.2,0.5]} {"up":true} {"click":[0.5,0.5]} {"drag":[[0.2,0.5],[0.8,0.5]],"ms":400}
    {"key":"ArrowRight"} {"type":"hello"} {"wheel":300} {"wait":500} {"set":1} {"scrub":0.5} {"shot":"label"}

  Frame times come from a headless browser drawing in software: read them as a comparison between two
  versions of a piece, not as what a visitor's laptop will do. Feel is still judged by a person.
*/
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const o = { _: [], variant: [] };
  const flags = new Set(['rtl', 'strict', 'ambient', 'help']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const k = a.slice(2);
    if (flags.has(k)) o[k] = true; else if (k === 'variant') o.variant.push(argv[++i]); else o[k] = argv[++i];
  }
  return o;
}

async function launch() {
  let chromium;
  try { ({ chromium } = require('playwright')); }
  catch { throw new Error('Playwright is not installed. Run: npm i -D playwright && npx playwright install chromium'); }
  const exe = process.env.CHROMIUM_PATH && existsSync(process.env.CHROMIUM_PATH) ? process.env.CHROMIUM_PATH : undefined;
  return chromium.launch({ executablePath: exe, args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const toUrl = (f, query = '') => {
  const base = /^https?:\/\//.test(f) ? f : pathToFileURL(path.resolve(f)).href;
  if (!query) return base;
  const q = query.replace(/^\?/, '');
  return base + (base.includes('?') ? '&' : '?') + q;
};

// Counts requestAnimationFrame calls and, while P.rec is on, records the gap between two frames of a running
// loop: only a frame that was requested from inside the previous frame counts, so a loop that input wakes
// for one frame at a time is not mistaken for a slow one.
const INSTRUMENT = () => {
  const raf = window.requestAnimationFrame.bind(window);
  const P = (window.__probe = { calls: 0, frames: [], rec: false });
  let last = 0, inFrame = false;
  window.requestAnimationFrame = (cb) => {
    P.calls++;
    const chained = inFrame;
    return raf((t) => {
      if (P.rec && chained && last && t - last < 250) P.frames.push(t - last);
      last = t; inFrame = true;
      try { cb(t); } finally { inFrame = false; }
    });
  };
};
const FORCE_RTL = () => {
  const set = () => { if (document.documentElement) { document.documentElement.setAttribute('dir', 'rtl'); return true; } return false; };
  if (!set()) new MutationObserver((_, mo) => { if (set()) mo.disconnect(); }).observe(document, { childList: true });
};

async function open(browser, url, a, ctxOpts = {}, init = []) {
  const [W, H] = (a.size || '1200x750').split('x').map(Number);
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, ...ctxOpts });
  await context.addInitScript(INSTRUMENT);
  for (const f of init) await context.addInitScript(f);
  const page = await context.newPage();
  const errors = [], external = new Set();
  const origin = new URL(url).origin;
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('request', (r) => { const u = r.url(); if (/^https?:/.test(u) && new URL(u).origin !== origin) external.add(new URL(u).host); });
  await page.goto(url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await sleep(450);
  const sel = a.root || '[data-piece]';
  const root = page.locator(sel).first();
  const found = (await root.count()) > 0;
  const box = found ? await root.boundingBox() : null;
  // Where gestures are aimed: --target, else [data-grab], else a slider or switch inside the piece, else the piece.
  const aim = found ? await page.evaluate(([s, t]) => {
    const r = document.querySelector(s), one = '[role=slider],input[type=range],[role=switch],input[type=checkbox]';
    const el = (t && document.querySelector(t)) || r.querySelector('[data-grab]') || (r.matches('[data-grab],' + one) ? r : r.querySelector(one)) || r;
    const b = el.getBoundingClientRect();
    const what = el === r ? 'the whole piece' : el.tagName.toLowerCase() + (el.getAttribute('role') ? `[role=${el.getAttribute('role')}]` : '') + (el.hasAttribute('data-grab') ? '[data-grab]' : '');
    return { x: b.left, y: b.top, width: b.width, height: b.height, what };
  }, [sel, a.target || '']) : null;
  return { context, page, errors, external, root, found, box, aim, sel };
}

const at = (box, [fx, fy]) => [box.x + box.width * fx, box.y + box.height * fy];
async function glide(page, from, to, ms = 300, n = 0) {
  n = n || Math.max(6, Math.round(ms / 16));
  for (let i = 1; i <= n; i++) { await page.mouse.move(from[0] + (to[0] - from[0]) * (i / n), from[1] + (to[1] - from[1]) * (i / n)); await sleep(ms / n); }
}
const rafCalls = (page) => page.evaluate(() => window.__probe.calls);
async function rafRate(page, ms = 600) { const a = await rafCalls(page); await sleep(ms); return Math.round(((await rafCalls(page)) - a) / (ms / 1000)); }
async function record(page, fn) {
  await page.evaluate(() => { window.__probe.frames = []; window.__probe.rec = true; });
  await fn();
  const f = await page.evaluate(() => { window.__probe.rec = false; return window.__probe.frames; });
  if (f.length < 8) return null;
  const s = [...f].sort((x, y) => x - y), q = (p) => s[Math.min(s.length - 1, Math.floor(s.length * p))];
  return { frames: f.length, p50: +q(0.5).toFixed(1), p95: +q(0.95).toFixed(1), long: f.filter((x) => x > 34).length };
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (!a._[0] || a.help) { console.log(readFileSync(new URL(import.meta.url)).toString().split('*/')[0].replace(/^[^\n]*\n\/\*\n?/, '')); process.exit(a.help ? 0 : 1); }
  const target = a._[0];
  const name = path.basename(target.replace(/[?#].*$/, '')).replace(/\.[a-z]+$/i, '') || 'piece';
  const outDir = path.resolve(a.out || `probe-${name}`);
  mkdirSync(outDir, { recursive: true });
  const browser = await launch();
  const shots = [], checks = [];
  const add = (level, id, msg, data) => checks.push({ level, id, msg, ...(data ? { data } : {}) });

  // A blank page that compares two screenshots and returns the share of pixels that changed.
  const lab = await (await browser.newContext()).newPage();
  const diff = (b1, b2) => lab.evaluate(async ([x, y]) => {
    const load = (s) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = 'data:image/png;base64,' + s; });
    const [i1, i2] = await Promise.all([load(x), load(y)]);
    if (i1.width !== i2.width || i1.height !== i2.height) return 1;
    const c = document.createElement('canvas'); c.width = i1.width; c.height = i1.height;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(i1, 0, 0); const d1 = g.getImageData(0, 0, c.width, c.height).data;
    g.drawImage(i2, 0, 0); const d2 = g.getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let k = 0; k < d1.length; k += 4) if (Math.abs(d1[k] - d2[k]) > 10 || Math.abs(d1[k + 1] - d2[k + 1]) > 10 || Math.abs(d1[k + 2] - d2[k + 2]) > 10) n++;
    return n / (d1.length / 4);
  }, [b1.toString('base64'), b2.toString('base64')]);
  const pct = (x) => (x * 100).toFixed(x < 0.001 ? 3 : 1) + '%';

  // ---------- pass 1: desktop, pointer and keys ----------
  const url = toUrl(target);
  const d = await open(browser, url, a);
  const { page } = d;
  const snap = async (label, group = 'pointer') => { const buf = await page.screenshot(); shots.push({ label, group, buf }); return buf; };
  if (!d.found) {
    add('FAIL', 'root', `no element matches ${d.sel}. Put data-piece="name" on the root of the piece, or pass --root.`);
  } else {
    const box = d.aim, whole = d.box;
    const info = await page.evaluate((sel) => {
      const r = document.querySelector(sel), P = window.PIECE;
      return { name: r.getAttribute('data-piece') || (P && P.name) || '', ambient: r.hasAttribute('data-ambient'), decorative: r.getAttribute('aria-hidden') === 'true' || r.hasAttribute('data-decorative'),
        scrub: !!(P && typeof P.scrub === 'function'), set: !!(P && typeof P.set === 'function'), dir: getComputedStyle(r).direction };
    }, d.sel);
    const ambient = info.ambient || !!a.ambient;
    add('INFO', 'root', `${d.sel}${info.name ? ` "${info.name}"` : ''} · ${Math.round(whole.width)}×${Math.round(whole.height)} px on a ${a.size || '1200x750'} stage · dir ${info.dir}${ambient ? ' · ambient' : ''} · gestures aimed at ${d.aim.what} (${Math.round(d.aim.width)}×${Math.round(d.aim.height)})`);

    await page.mouse.move(4, 4);
    await sleep(500);
    const rest = await snap('rest');
    const restRate = await rafRate(page, 600);
    const rest2 = await page.screenshot();
    const restMove = await diff(rest, rest2);
    if (!ambient && restMove > 0.0005) add('WARN', 'rest', `moves at rest (${pct(restMove)} of pixels changed in 0.6 s). If that is the design, put data-ambient on the root.`);
    if (restMove <= 0.0005 && restRate > 20) add('WARN', 'idle-loop', `requestAnimationFrame runs ${restRate} times a second while nothing on screen changes. Let the loop sleep at rest.`);
    else add('PASS', 'idle-loop', restMove <= 0.0005 ? `asleep at rest (${restRate} frames a second requested)` : `ambient motion at rest (${restRate} frames a second)`);

    const centre = at(box, [0.5, 0.5]);
    const reacts = {};
    let pacing = [];
    if (a.steps) {
      const steps = JSON.parse(readFileSync(a.steps, 'utf8'));
      let cur = [4, 4];
      for (const s of steps) {
        if (s.move) { const to = at(box, s.move); await glide(page, cur, to, s.ms || 250); cur = to; }
        else if (s.down) { const to = at(box, s.down); await glide(page, cur, to, 120); cur = to; await page.mouse.down(); }
        else if (s.up) await page.mouse.up();
        else if (s.click) { const to = at(box, s.click); await glide(page, cur, to, 150); cur = to; await page.mouse.down(); await sleep(60); await page.mouse.up(); }
        else if (s.drag) { const p0 = at(box, s.drag[0]), p1 = at(box, s.drag[1]); await glide(page, cur, p0, 120); await page.mouse.down(); const r = await record(page, () => glide(page, p0, p1, s.ms || 400)); if (r) pacing.push({ during: 'drag', ...r }); await page.mouse.up(); cur = p1; }
        else if (s.key) await page.keyboard.press(s.key);
        else if (s.type) await page.keyboard.type(s.type, { delay: 40 });
        else if (s.wheel) await page.mouse.wheel(0, s.wheel);
        else if (s.wait) await sleep(s.wait);
        else if (s.set !== undefined) await page.evaluate((p) => window.PIECE && window.PIECE.set && window.PIECE.set(p), s.set);
        else if (s.scrub !== undefined) await page.evaluate((p) => window.PIECE && window.PIECE.scrub && window.PIECE.scrub(p), s.scrub);
        else if (s.shot) { const b = await snap(s.shot); reacts[s.shot] = await diff(rest, b); }
      }
      await page.mouse.up();
    } else {
      await glide(page, [4, 4], centre, 260);
      await sleep(380);
      reacts.hover = await diff(rest, await snap('hover'));

      const left = at(box, [0.04, 0.5]), right = at(box, [0.96, 0.5]);
      await glide(page, centre, left, 180);
      const sweep = await record(page, () => glide(page, left, right, 800));
      if (sweep) pacing.push({ during: 'sweep', ...sweep });
      await sleep(120);
      reacts.sweep = await diff(rest, await snap('pointer at right edge'));

      await glide(page, right, centre, 220);
      await page.mouse.down();
      await sleep(220);
      reacts.press = await diff(rest, await snap('press'));
      await sleep(700);
      reacts.hold = await diff(rest, await snap('hold 0.9 s'));
      await page.mouse.up();
      await sleep(450);
      reacts.release = await diff(rest, await snap('release'));

      const p0 = at(box, [0.3, 0.5]), p1 = at(box, [0.74, 0.5]);
      await glide(page, centre, p0, 200);
      await page.mouse.down();
      const dr = await record(page, () => glide(page, p0, p1, 420));
      if (dr) pacing.push({ during: 'drag', ...dr });
      reacts.drag = await diff(rest, await snap('drag, still held'));
      await page.mouse.up();
      const picked = await page.evaluate(() => String(window.getSelection ? window.getSelection() : '').length);
      if (picked) { add('WARN', 'selection', `dragging selected ${picked} characters of text. Put user-select: none on the surface people drag across.`); await page.evaluate(() => window.getSelection().removeAllRanges()); }
      await sleep(160);
      await snap('0.16 s after letting go');
      await sleep(1300);
      reacts.afterDrag = await diff(rest, await snap('settled after drag'));
    }

    await glide(page, at(box, [0.74, 0.5]), [4, 4], 200);
    await sleep(1000);
    const left1 = await snap('pointer gone');
    await sleep(500);
    const left2 = await page.screenshot();
    const still = await diff(left1, left2);
    if (!ambient) {
      if (still > 0.0005) add('WARN', 'settle', `still moving 1.5 s after the pointer left (${pct(still)} of pixels changed in 0.5 s). Springs should reach rest and stop.`);
      else add('PASS', 'settle', 'comes to rest after input');
    }

    // keys
    let focused = false;
    for (let i = 0; i < 10 && !focused; i++) {
      await page.keyboard.press('Tab');
      focused = await page.evaluate((sel) => { const r = document.querySelector(sel); return !!r && r.contains(document.activeElement) && document.activeElement !== document.body; }, d.sel);
    }
    if (!focused) {
      if (info.decorative) add('INFO', 'keys', 'marked decorative (aria-hidden or data-decorative): no keyboard path expected');
      else add('WARN', 'keys', 'nothing in the piece takes keyboard focus. A control needs a real button, input or tabindex; a decoration should say aria-hidden="true".');
    } else {
      await sleep(250);
      const f = await snap('keyboard focus', 'keys');
      const ring = await diff(left1, f);
      const what = await page.evaluate(() => { const e = document.activeElement; return `${e.tagName.toLowerCase()}${e.getAttribute('role') ? `[role=${e.getAttribute('role')}]` : ''}${e.getAttribute('aria-label') ? ` "${e.getAttribute('aria-label')}"` : ''}`; });
      if (ring < 0.00015) add('WARN', 'focus', `${what} takes focus but nothing visible changes. Draw a focus ring with :focus-visible.`);
      else add('PASS', 'focus', `${what} takes focus and shows it`);
      for (const k of ['ArrowRight', 'ArrowRight', 'ArrowRight']) { await page.keyboard.press(k); await sleep(90); }
      await sleep(500);
      const k1 = await snap('→ → →', 'keys');
      await page.keyboard.press('Enter');
      await sleep(600);
      const k2 = await snap('Enter', 'keys');
      await page.keyboard.press('Space');
      await sleep(600);
      const k3 = await snap('Space', 'keys');
      reacts.keys = Math.max(await diff(f, k1), await diff(k1, k2), await diff(k2, k3));
      if (reacts.keys < 0.0005) add('WARN', 'keys', 'focusable, but arrows, Enter and Space change nothing');
      else add('PASS', 'keys', 'responds to the keyboard');
    }

    const best = Object.entries(reacts).sort((x, y) => y[1] - x[1])[0];
    if (!best || best[1] < 0.0005) add('WARN', 'response', 'nothing visibly responded to hover, press, drag or keys');
    else add('PASS', 'response', 'responds to: ' + Object.entries(reacts).filter(([, v]) => v >= 0.0005).map(([k, v]) => `${k} ${pct(v)}`).join(', '));

    if (pacing.length) {
      const worst = pacing.reduce((m, p) => (p.p95 > m.p95 ? p : m));
      const line = pacing.map((p) => `${p.during}: median ${p.p50} ms, 95th ${p.p95} ms, ${p.long} of ${p.frames} over 34 ms`).join(' · ');
      add(worst.p95 > 40 ? 'WARN' : 'PASS', 'frames', line + (worst.p95 > 40 ? '. Slow even for a headless browser: look for layout work or a large canvas redraw per frame.' : ''), pacing);
    } else add('INFO', 'frames', 'no requestAnimationFrame activity during pointer input (CSS-driven, or it did not react)');

    // scrub
    if (info.scrub) {
      const ps = [0, 0.25, 0.5, 0.75, 1], bufs = [];
      for (const p of ps) { await page.evaluate((v) => window.PIECE.scrub(v), p); await sleep(140); bufs.push(await snap(`scrub ${p}`, 'scrub')); }
      await page.evaluate(() => window.PIECE.scrub(0.5)); await sleep(140);
      const again = await diff(bufs[2], await page.screenshot());
      const stepsDiffer = [];
      for (let i = 1; i < bufs.length; i++) stepsDiffer.push(await diff(bufs[i - 1], bufs[i]));
      if (again > 0.0005 && !ambient) add('WARN', 'scrub', `scrub(0.5) gave two different pictures (${pct(again)} apart). The settled state should depend on p alone: seed the random numbers and keep time out of it.`);
      else if (stepsDiffer.some((x) => x < 0.0003)) add('WARN', 'scrub', `scrub changes nothing between ${ps.filter((_, i) => i && stepsDiffer[i - 1] < 0.0003).map((p, i) => `${ps[ps.indexOf(p) - 1]} and ${p}`).join('; ')}. Spread the change over the whole range or the control feels dead there.`);
      else add('PASS', 'scrub', 'PIECE.scrub(p) is repeatable and every quarter looks different');
    } else add('WARN', 'scrub', 'no window.PIECE.scrub(p). Without it the in-between states cannot be photographed or reproduced.');

    // off screen
    const off = await page.evaluate((sel) => {
      const sp = document.createElement('div'); sp.style.cssText = 'height:300vh;flex:none;grid-column:1/-1'; sp.id = '__probe_spacer';
      document.body.prepend(sp); window.scrollTo(0, 0);
      return document.querySelector(sel).getBoundingClientRect().top > window.innerHeight + 80;
    }, d.sel);
    if (!off) add('INFO', 'offscreen', 'could not push the piece off screen in this layout: check by hand that its loop stops when scrolled away');
    else {
      await sleep(350);
      if (info.set) await page.evaluate(() => { window.PIECE.set(0); window.PIECE.set(1); });
      const rate = await rafRate(page, 800);
      if (rate > 6) add('WARN', 'offscreen', `keeps requesting ${rate} frames a second while scrolled out of view. Gate the loop with an IntersectionObserver.`);
      else add('PASS', 'offscreen', `sleeps off screen (${rate} frames a second${ambient || info.set ? '' : ', but nothing was asking it to move'})`);
    }
    await page.evaluate(() => document.getElementById('__probe_spacer')?.remove());

    if (d.errors.length) add('FAIL', 'errors', `${d.errors.length} script error(s): ${[...new Set(d.errors)].slice(0, 4).join(' | ')}`);
    else add('PASS', 'errors', 'no script errors');
    if (d.external.size) add('WARN', 'self-contained', `loads from other hosts: ${[...d.external].join(', ')}. A piece that is pasted elsewhere should bring what it needs or degrade without it.`);
    else add('PASS', 'self-contained', 'no requests to other hosts');

    // ---------- pass 2: prefers-reduced-motion ----------
    {
      const r = await open(browser, url, a, { reducedMotion: 'reduce' });
      await r.page.mouse.move(4, 4); await sleep(400);
      const r1 = await r.page.screenshot(); shots.push({ label: 'rest', group: 'reduced motion', buf: r1 });
      await sleep(600);
      const moving = await diff(r1, await r.page.screenshot());
      let jump = null;
      if (info.set) {
        await r.page.evaluate(() => window.PIECE.set(1));
        await sleep(120);
        const s1 = await r.page.screenshot(); shots.push({ label: 'set(1) after 0.12 s', group: 'reduced motion', buf: s1 });
        await sleep(900);
        const s2 = await r.page.screenshot(); shots.push({ label: 'set(1) after 1 s', group: 'reduced motion', buf: s2 });
        jump = await diff(s1, s2);
      } else {
        const c = at(r.aim, [0.5, 0.5]);
        await glide(r.page, [4, 4], c, 200); await sleep(300);
        shots.push({ label: 'hover', group: 'reduced motion', buf: await r.page.screenshot() });
      }
      if (moving > 0.0005) add('WARN', 'reduced-motion', `still moves at rest under prefers-reduced-motion (${pct(moving)} of pixels in 0.6 s). Hold a designed still frame instead.`);
      else if (jump !== null && jump > 0.004) add('WARN', 'reduced-motion', `set(1) still animates under prefers-reduced-motion (${pct(jump)} of pixels changed between 0.12 s and 1 s). Jump to the settled state, or cross-fade.`);
      else add('PASS', 'reduced-motion', jump !== null ? 'holds still at rest and changes state without travel' : 'holds still at rest');
      if (r.errors.length) add('FAIL', 'errors', `under reduced motion: ${[...new Set(r.errors)].slice(0, 3).join(' | ')}`);
      await r.context.close();
    }

    // ---------- pass 3: phone, touch ----------
    {
      const t = await open(browser, url, { ...a, size: '390x844' }, { hasTouch: true, isMobile: true });
      if (t.found) {
        const m = await t.page.evaluate((sel) => {
          const r = document.querySelector(sel), b = r.getBoundingClientRect();
          let minFont = 99, minText = '';
          const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT);
          while (w.nextNode()) {
            const n = w.currentNode, el = n.parentElement;
            if (!n.textContent.trim() || !el) continue;
            const cs = getComputedStyle(el), bb = el.getBoundingClientRect();
            if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05 || bb.width < 2 || el.closest('[aria-hidden="true"]')) continue;
            const f = parseFloat(cs.fontSize) * (new DOMMatrixReadOnly(cs.transform === 'none' ? undefined : cs.transform).a || 1);
            if (f < minFont) { minFont = f; minText = n.textContent.trim().slice(0, 24); }
          }
          const small = [...r.querySelectorAll('button,a[href],input,select,textarea,[role=button],[role=switch],[role=slider],[role=tab],[tabindex]:not([tabindex="-1"])')]
            .map((e) => ({ e, b: e.getBoundingClientRect() })).filter(({ b }) => b.width > 0 && (b.width < 36 || b.height < 36))
            .map(({ e, b }) => `${e.tagName.toLowerCase()} ${Math.round(b.width)}×${Math.round(b.height)}`);
          return { vw: window.innerWidth, overflow: document.scrollingElement.scrollWidth - window.innerWidth, left: b.left, right: b.right - window.innerWidth, minFont, minText, small, touchAction: getComputedStyle(r).touchAction };
        }, t.sel);
        const cdp = await t.context.newCDPSession(t.page);
        const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y }] });
        const tb = t.aim, c = at(tb, [0.5, 0.5]);
        const t0 = await t.page.screenshot(); shots.push({ label: 'rest', group: 'phone 390', buf: t0 });
        await t.page.touchscreen.tap(c[0], c[1]); await sleep(500);
        const t1 = await t.page.screenshot(); shots.push({ label: 'tap', group: 'phone 390', buf: t1 });
        const q0 = at(tb, [0.25, 0.5]), q1 = at(tb, [0.75, 0.5]);
        await touch('touchStart', q0[0], q0[1]);
        for (let i = 1; i <= 14; i++) { await touch('touchMove', q0[0] + (q1[0] - q0[0]) * (i / 14), q0[1]); await sleep(18); }
        const t2 = await t.page.screenshot(); shots.push({ label: 'touch drag, held', group: 'phone 390', buf: t2 });
        await touch('touchEnd', q1[0], q1[1]); await sleep(900);
        shots.push({ label: 'after touch drag', group: 'phone 390', buf: await t.page.screenshot() });
        const touched = Math.max(await diff(t0, t1), await diff(t1, t2));
        if (m.vw > 392) add('FAIL', 'phone', `does not fit a 390 px phone: the content is ${m.vw} px wide, so the browser zooms the whole page out to show it`);
        else if (m.overflow > 1 || m.right > 1 || m.left < -1) add('FAIL', 'phone', `does not fit a 390 px phone: ${m.overflow > 1 ? `page scrolls sideways by ${Math.round(m.overflow)} px` : `piece runs ${Math.round(Math.max(m.right, -m.left))} px past the edge`}`);
        else add('PASS', 'phone', `fits a 390 px phone${touched >= 0.0005 ? ' and responds to touch' : ''} · touch-action: ${m.touchAction}`);
        if (touched < 0.0005 && (reacts.press > 0.0005 || reacts.drag > 0.0005)) add('WARN', 'touch', 'responds to the mouse but not to tap or touch drag. Use pointer events, and set touch-action on the dragged element.');
        if (m.minFont < 11) add('WARN', 'phone-text', `smallest text on a phone is ${m.minFont.toFixed(1)} px ("${m.minText}")`);
        if (m.small.length) add('WARN', 'phone-targets', `touch targets under 36 px: ${m.small.slice(0, 5).join(', ')}`);
        if (t.errors.length) add('FAIL', 'errors', `on a phone: ${[...new Set(t.errors)].slice(0, 3).join(' | ')}`);
      }
      await t.context.close();
    }

    // ---------- optional passes: rtl, variants ----------
    const extra = [];
    if (a.rtl) extra.push({ label: 'rtl', url, init: [FORCE_RTL] });
    for (const v of a.variant) { const i = v.indexOf('='); extra.push({ label: v.slice(0, i), url: toUrl(target, v.slice(i + 1)), init: [] }); }
    for (const x of extra) {
      const v = await open(browser, x.url, a, {}, x.init);
      if (!v.found) { add('FAIL', x.label, `no ${v.sel} in this variant`); await v.context.close(); continue; }
      await v.page.mouse.move(4, 4); await sleep(400);
      shots.push({ label: 'rest', group: x.label, buf: await v.page.screenshot() });
      if (info.scrub) for (const p of [0.5, 1]) { await v.page.evaluate((q) => window.PIECE.scrub(q), p); await sleep(140); shots.push({ label: `scrub ${p}`, group: x.label, buf: await v.page.screenshot() }); }
      else { await glide(v.page, [4, 4], at(v.aim, [0.5, 0.5]), 200); await sleep(350); shots.push({ label: 'hover', group: x.label, buf: await v.page.screenshot() }); }
      const m = await v.page.evaluate((sel) => ({ overflow: document.scrollingElement.scrollWidth - window.innerWidth, dir: getComputedStyle(document.querySelector(sel)).direction }), v.sel);
      if (v.errors.length) add('FAIL', x.label, `script errors: ${[...new Set(v.errors)].slice(0, 3).join(' | ')}`);
      else if (m.overflow > 1) add('FAIL', x.label, `page scrolls sideways by ${Math.round(m.overflow)} px`);
      else add('PASS', x.label, `renders without errors or overflow · dir ${m.dir}. Read the sheet: mirrored layout, unreversed words, gestures pointing the right way.`);
      await v.context.close();
    }
  }
  await d.context.close();

  // ---------- contact sheet ----------
  const cols = Number(a.cols || 4), thumb = Number(a.thumb || 420);
  if (shots.length) {
    const sheet = await (await browser.newContext({ viewport: { width: cols * (thumb + 12) + 12, height: 400 }, deviceScaleFactor: 1 })).newPage();
    const tone = { FAIL: '#ff6b6b', WARN: '#f5b041', PASS: '#58d68d', INFO: '#8aa' };
    const html = `<body style="margin:0;background:#17171a;color:#ddd;font:12px/1.4 ui-monospace,Menlo,monospace;padding:12px">
      <div style="font-size:14px;color:#fff;margin-bottom:6px">${name} · probe</div>
      <div style="margin-bottom:10px">${checks.map((c) => `<div><span style="color:${tone[c.level]}">${c.level}</span> ${c.id} — ${c.msg.replace(/</g, '&lt;')}</div>`).join('')}</div>
      <div style="display:grid;grid-template-columns:repeat(${cols},${thumb}px);gap:12px">${shots.map((s) => `<figure style="margin:0"><figcaption style="padding:2px 0 4px"><span style="color:#8aa">${s.group}</span> · ${s.label}</figcaption><img src="data:image/png;base64,${s.buf.toString('base64')}" style="display:block;max-width:${thumb}px;max-height:${Math.round(thumb * 0.9)}px;outline:1px solid #333"></figure>`).join('')}</div></body>`;
    await sheet.setContent(html, { waitUntil: 'load' });
    await sheet.screenshot({ path: path.join(outDir, 'sheet.png'), fullPage: true });
  }
  await browser.close();

  const order = { FAIL: 0, WARN: 1, PASS: 2, INFO: 3 };
  const sorted = [...checks].sort((x, y) => order[x.level] - order[y.level]);
  writeFileSync(path.join(outDir, 'report.json'), JSON.stringify({ target, at: new Date().toISOString(), checks: sorted, shots: shots.map((s) => `${s.group} · ${s.label}`) }, null, 1));
  for (const c of sorted) console.log(`${c.level.padEnd(4)} ${c.id.padEnd(15)} ${c.msg}`);
  const fails = checks.filter((c) => c.level === 'FAIL').length, warns = checks.filter((c) => c.level === 'WARN').length;
  console.log(`\n${fails} fail, ${warns} warn · ${shots.length} stills on ${path.join(outDir, 'sheet.png')}`);
  process.exit(fails || (a.strict && warns) ? 1 : 0);
}

main().catch((e) => { console.error(String(e && e.stack ? e.stack : e)); process.exit(2); });
