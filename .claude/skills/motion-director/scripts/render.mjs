#!/usr/bin/env node
/*
  render.mjs — turn a seek(t) page into an MP4, frame by frame.

  The page must expose  window.seek(t)  (sync or async) that draws time t in seconds.
  Optional:  window.FILM = { width, height, fps, duration }   defaults for the flags below
             window.ready                                      promise resolved when assets are loaded
             window.renderAudio()                              returns the soundtrack as a base64 WAV

  node render.mjs film.html --out film.mp4
       [--fps 60] [--duration 15] [--from 0] [--to 15]
       [--width 1920] [--height 1080] [--scale 1]
       [--subframes 3] [--shutter 0.5]      motion blur: subframes blended per frame, shutter in frames
       [--audio track.wav] [--no-audio] [--loudnorm]
       [--crf 16] [--png] [--quality 95] [--preview]

  --preview renders half size at 30 fps with no motion blur: watch this before paying for the full render.
  Needs Playwright (Chromium) and ffmpeg. Nothing is played back live, so a slow machine cannot drop frames.
*/
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { existsSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const k = a.slice(2);
    if (['no-audio', 'loudnorm', 'png', 'preview', 'help'].includes(k)) o[k] = true;
    else o[k] = argv[++i];
  }
  return o;
}

export async function launch() {
  let chromium;
  try { ({ chromium } = require('playwright')); }
  catch { throw new Error('Playwright is not installed. Run: npm i -D playwright && npx playwright install chromium'); }
  const exe = process.env.CHROMIUM_PATH && existsSync(process.env.CHROMIUM_PATH) ? process.env.CHROMIUM_PATH : undefined;
  return chromium.launch({ executablePath: exe, args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--autoplay-policy=no-user-gesture-required'] });
}

export function pageUrl(file) {
  if (/^https?:\/\//.test(file)) return file + (file.includes('?') ? '&' : '?') + 'render=1';
  const abs = path.resolve(file);
  if (!existsSync(abs)) throw new Error(`No such file: ${abs}`);
  return pathToFileURL(abs).href + '?render=1';
}

export async function openFilm(browser, file, { width, height, scale = 1 } = {}) {
  const probe = await browser.newPage();
  await probe.goto(pageUrl(file), { waitUntil: 'load' });
  await probe.waitForFunction(() => typeof window.seek === 'function', null, { timeout: 30000 })
    .catch(() => { throw new Error('The page never defined window.seek(t).'); });
  const film = await probe.evaluate(() => window.FILM || {});
  await probe.close();
  const W = Number(width || film.width || 1920), H = Number(height || film.height || 1080);
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: Number(scale) });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e.message || e)));
  await page.goto(pageUrl(file), { waitUntil: 'load' });
  await page.waitForFunction(() => typeof window.seek === 'function');
  await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; if (window.ready) await window.ready; });
  return { page, context, film, W, H, errors };
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.help || !a._[0]) { console.log('usage: node render.mjs film.html --out film.mp4 [--fps 60] [--subframes 3] [--preview] ...'); process.exit(a.help ? 0 : 1); }
  const browser = await launch();
  const scale = a.preview ? 0.5 : Number(a.scale || 1);
  const { page, film, W, H, errors } = await openFilm(browser, a._[0], { width: a.width, height: a.height, scale });
  const fps = a.preview ? 30 : Number(a.fps || film.fps || 60);
  const from = Number(a.from || 0), to = Number(a.to || a.duration || film.duration || 0);
  if (!(to > from)) throw new Error('Set a duration: --duration <seconds>, or window.FILM.duration in the page.');
  const S = a.preview ? 1 : Math.max(1, Number(a.subframes || 3));
  const shutter = Number(a.shutter || 0.5);
  const out = path.resolve(a.out || 'film.mp4');
  const frames = Math.round((to - from) * fps);
  const type = a.png ? 'png' : 'jpeg';

  // soundtrack: a file wins, else whatever the page can render itself
  let audio = a.audio ? path.resolve(a.audio) : null, tmp = null;
  if (!audio && !a['no-audio']) {
    const b64 = await page.evaluate(async () => (typeof window.renderAudio === 'function' ? await window.renderAudio() : null));
    if (b64) { tmp = mkdtempSync(path.join(tmpdir(), 'film-')); audio = path.join(tmp, 'track.wav'); writeFileSync(audio, Buffer.from(b64, 'base64')); }
  }

  // tmix averages each frame with the S-1 before it; keeping every S-th frame leaves one blended frame per output frame
  const vf = [];
  if (S > 1) vf.push(`tmix=frames=${S}`, `select='eq(mod(n\\,${S})\\,${S - 1})'`, `setpts=N/(${fps}*TB)`);
  vf.push('scale=trunc(iw/2)*2:trunc(ih/2)*2');
  const ff = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', type === 'png' ? 'png' : 'mjpeg', '-framerate', String(fps * S), '-i', '-'];
  if (audio) ff.push('-ss', String(from), '-i', audio);
  ff.push('-vf', vf.join(','), '-r', String(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', String(a.crf || (a.preview ? 24 : 16)), '-pix_fmt', 'yuv420p', '-movflags', '+faststart');
  if (audio) ff.push(...(a.loudnorm ? ['-af', 'loudnorm=I=-14:TP=-1.5:LRA=11'] : []), '-c:a', 'aac', '-b:a', '192k', '-t', String(to - from));
  ff.push(out);
  const enc = spawn('ffmpeg', ff, { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => { enc.on('error', rej); enc.on('close', c => (c === 0 ? res() : rej(new Error(`ffmpeg exited with ${c}`)))); });
  enc.stdin.on('error', () => {});

  console.log(`${W}x${H}${scale !== 1 ? ` @${scale}x` : ''}, ${fps} fps, ${frames} frames, ${S} subframe${S > 1 ? 's' : ''}${audio ? ', with audio' : ''}`);
  const t0 = Date.now();
  for (let i = 0; i < frames; i++) {
    for (let k = 0; k < S; k++) {
      const offset = S > 1 ? ((k + 0.5) / S - 0.5) * shutter : 0;      // shutter centred on the frame time
      const t = Math.max(0, from + (i + offset) / fps);
      await page.evaluate(async x => { await window.seek(x); }, t);
      const shot = await page.screenshot({ type, ...(type === 'jpeg' ? { quality: Number(a.quality || 95) } : {}) });
      if (!enc.stdin.write(shot)) await new Promise(r => enc.stdin.once('drain', r));
    }
    if (i % Math.max(1, Math.round(fps)) === 0 || i === frames - 1) {
      const el = (Date.now() - t0) / 1000;
      process.stdout.write(`\r  frame ${i + 1}/${frames}  ${el.toFixed(0)}s elapsed, about ${((el / (i + 1)) * (frames - i - 1)).toFixed(0)}s left   `);
    }
  }
  enc.stdin.end();
  await done;
  await browser.close();
  if (tmp) rmSync(tmp, { recursive: true, force: true });
  console.log(`\nwrote ${out}`);
  if (errors.length) console.log(`page errors while rendering (${errors.length}):\n  ` + [...new Set(errors)].slice(0, 5).join('\n  '));
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  main().catch(e => { console.error('\nrender failed: ' + e.message); process.exit(1); });
}
