#!/usr/bin/env node
/*
  stills.mjs — look before you render.

  Contact sheet: one still per beat (or per time you name) on a single image.
  Strip:         every frame around one moment, to judge a transition or hunt a pop.

  node stills.mjs film.html --out sheet.png                      one still from the middle of every beat (needs FILM.bpm or --bpm)
  node stills.mjs film.html --out sheet.png --times 0.5,2.1,4    exactly these times, in seconds
  node stills.mjs film.html --out sheet.png --every 0.5          every half second
  node stills.mjs film.html --out sheet.png --count 12           twelve stills spread evenly
  node stills.mjs film.html --out strip.png --strip 4.3 [--span 0.3]   every frame from 0.3 s before 4.3 s to 0.3 s after
       [--bpm 120] [--cols 4] [--thumb 480] [--duration 15] [--fps 60]

  One sheet is quicker to review than dozens of images and keeps the session small.
*/
import path from 'node:path';
import { launch, openFilm } from './render.mjs';

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) { const a = argv[i]; if (a.startsWith('--')) o[a.slice(2)] = argv[++i]; else o._.push(a); }
  return o;
}

const a = parseArgs(process.argv.slice(2));
if (!a._[0]) { console.log('usage: node stills.mjs film.html --out sheet.png [--times a,b,c | --every s | --count n | --strip t]'); process.exit(1); }

try {
  const browser = await launch();
  const probe = await openFilm(browser, a._[0], {});
  const { film, W, H } = probe;
  await probe.context.close();
  const thumb = Number(a.thumb || 480);
  const { page, errors } = await openFilm(browser, a._[0], { scale: thumb / W });
  const fps = Number(a.fps || film.fps || 60), duration = Number(a.duration || film.duration || 0);
  const bpm = Number(a.bpm || film.bpm || 0);

  let times = [], label = t => `${t.toFixed(2)}s`;
  if (a.strip !== undefined) {
    const c = Number(a.strip), span = Number(a.span || 0.3);
    for (let f = Math.round((c - span) * fps); f <= Math.round((c + span) * fps); f++) if (f >= 0) times.push(f / fps);
    label = t => `f${Math.round(t * fps)} · ${t.toFixed(3)}s`;
  } else if (a.times) times = a.times.split(',').map(Number);
  else if (a.every) for (let t = Number(a.every) / 2; t < duration; t += Number(a.every)) times.push(t);
  else if (a.count) for (let i = 0; i < Number(a.count); i++) times.push((i + 0.5) * duration / Number(a.count));
  else if (bpm) { const b = 60 / bpm; for (let i = 0; (i + 0.5) * b < duration; i++) times.push((i + 0.5) * b); label = t => `beat ${Math.floor(t / b) + 1} · ${t.toFixed(2)}s`; }
  else throw new Error('Say which stills: --times, --every, --count, --strip, or a bpm (FILM.bpm or --bpm).');
  if (!times.length) throw new Error('No stills to take: set --duration or window.FILM.duration.');
  if (times.length > 240) throw new Error(`${times.length} stills is too many for one sheet; narrow the range.`);

  const shots = [];
  for (const t of times) {
    await page.evaluate(async x => { await window.seek(x); }, t);
    shots.push({ t, src: 'data:image/jpeg;base64,' + (await page.screenshot({ type: 'jpeg', quality: 88 })).toString('base64') });
  }

  const cols = Number(a.cols || (a.strip !== undefined ? Math.min(8, times.length) : Math.min(4, times.length)));
  const tw = a.strip !== undefined ? Math.min(thumb, 300) : thumb, th = Math.round(tw * H / W);
  const sheet = await browser.newPage({ viewport: { width: cols * (tw + 12) + 12, height: 600 } });
  await sheet.setContent(`<!doctype html><meta charset="utf-8"><style>
    body{margin:0;padding:12px 0 0 12px;background:#17181a;font:12px/1.4 ui-monospace,Menlo,monospace;color:#c9ccd1}
    .g{display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:12px;padding:0 12px 12px 0}
    figure{margin:0} img{display:block;width:${tw}px;height:${th}px;background:#000} figcaption{padding-top:4px}
    </style><div class="g">${shots.map(s => `<figure><img src="${s.src}"><figcaption>${label(s.t)}</figcaption></figure>`).join('')}</div>`);
  await sheet.waitForFunction(() => [...document.images].every(i => i.complete));
  const out = path.resolve(a.out || (a.strip !== undefined ? 'strip.png' : 'sheet.png'));
  await sheet.screenshot({ path: out, fullPage: true });
  await browser.close();
  console.log(`wrote ${out}  (${times.length} stills, ${cols} per row)`);
  if (errors.length) console.log('page errors:\n  ' + [...new Set(errors)].slice(0, 5).join('\n  '));
} catch (e) { console.error('stills failed: ' + e.message); process.exit(1); }
