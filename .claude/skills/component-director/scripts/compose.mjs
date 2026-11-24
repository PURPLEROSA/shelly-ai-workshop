#!/usr/bin/env node
// compose.mjs — lift pieces out of their own files and set them into one page.
//
// A piece file carries three marked blocks (scripts/piece-starter.html has them):
//     <style data-for="name"> ... </style>          the piece's styles, scoped under its own class
//     <!-- piece:start --> ... <!-- piece:end -->   its markup
//     <script data-for="name"> ... </script>        its script
// Everything else in a piece file (the stage, the ?lang switch, its copy of the kit) is for viewing it alone
// and is left behind.
//
// A shell is an ordinary HTML page with three kinds of marker:
//     <!-- pieces:css -->                 in <head>: every piece's styles go here
//     <!-- piece: ../path/piece.html -->  in <body>: that piece's markup goes here (path relative to the shell)
//     <!-- pieces:js -->                  before the page's own script: one copy of the kit, then every piece's script
//
//     node compose.mjs shell.html --out page.html
//     node compose.mjs shell.html --out page.html --artifact page.artifact.html
//
// --out       a complete page: open it, deploy it.
// --artifact  the same page for a host that supplies its own <html>, <head> and <body> and blocks other
//             hosts (a Claude artifact): the wrapper tags are dropped, lang and dir are set by script, and
//             local files named in url(...) (looked up beside the --out page) are inlined as data URIs.
//             Google Fonts links are kept.
//
// The page themes the pieces through custom properties (each piece lists its own in a comment above its
// styles) and talks to them through window.PIECES[name]: scrub(p), set(p), and hello() where a piece has one.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : null; };
const shellPath = args.find((a, i) => !a.startsWith('--') && (i === 0 || !args[i - 1].startsWith('--')));
if (!shellPath || !opt('out')) { console.log('usage: node compose.mjs shell.html --out page.html [--artifact page.artifact.html]'); process.exit(1); }

const here = path.dirname(fileURLToPath(import.meta.url));
const shellDir = path.dirname(path.resolve(shellPath));
const outDir = path.dirname(path.resolve(opt('out')));
let page = readFileSync(shellPath, 'utf8');
const fail = (msg) => { console.error('compose: ' + msg); process.exit(1); };

const pieces = [];
page = page.replace(/<!--\s*piece:\s*(\S+)\s*-->/g, (_, rel) => {
  const file = path.resolve(shellDir, rel);
  if (!existsSync(file)) fail(`no such piece file: ${rel}`);
  const src = readFileSync(file, 'utf8');
  const css = [...src.matchAll(/<style data-for="([^"]+)">([\s\S]*?)<\/style>/g)];
  const js = [...src.matchAll(/<script data-for="([^"]+)">([\s\S]*?)<\/script>/g)];
  const html = src.match(/<!-- piece:start -->([\s\S]*?)<!-- piece:end -->/);
  if (!css.length || !js.length || !html) fail(`${rel} is missing a marked block (style data-for, piece:start/end, script data-for)`);
  const name = css[0][1];
  // A rule for the piece that sits in a stage block would be left behind and the piece would arrive half styled.
  const cls = (html[1].match(/class="([^"\s]+)[^"]*"[^>]*data-piece=|data-piece="[^"]*"[^>]*class="([^"\s]+)/) || []).slice(1).find(Boolean);
  const stage = [...src.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join('\n');
  if (cls && new RegExp(`(^|[\\s,}])\\.${cls}[\\s.{:,>]`).test(stage)) fail(`${rel}: a rule for .${cls} is in a stage <style> block. Move it into <style data-for="${name}">.`);
  if (pieces.some((p) => p.name === name)) fail(`two pieces are both called "${name}"`);
  pieces.push({ name, rel, css: css.map((m) => m[2].trim()).join('\n'), js: js.map((m) => m[2].trim()).join('\n') });
  return html[1].trim();
});
if (!pieces.length) fail('the shell names no pieces. Add <!-- piece: path/to/piece.html --> where each one goes.');
for (const marker of ['<!-- pieces:css -->', '<!-- pieces:js -->']) if (!page.includes(marker)) fail(`the shell has no ${marker} marker`);

// A class the page styles by its bare name would also restyle a piece that uses the same name inside itself.
const own = [...page.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) => m[1].replace(/\/\*[\s\S]*?\*\//g, '')).join('\n');
const pageClasses = new Set([...own.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)].map((m) => m[1]));
for (const p of pieces) {
  const inner = new Set([...p.css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/\.(-?[A-Za-z_][\w-]*)/g)].map((m) => m[1]));
  const rootClass = (p.css.match(/\.(-?[A-Za-z_][\w-]*)\s*\{/) || [])[1];
  const clash = [...inner].filter((c) => c !== rootClass && pageClasses.has(c));
  if (clash.length) fail(`the page and the piece "${p.name}" both style .${clash.join(', .')}. Rename the page's class: a piece keeps its inner names.`);
}

const ids = [...page.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
const twice = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
if (twice.length) console.warn(`compose: warning, repeated id: ${twice.join(', ')}`);

const kit = readFileSync(path.join(here, 'kit.js'), 'utf8').trim();
page = page.replace('<!-- pieces:css -->', () => `<style>\n/* pieces: ${pieces.map((p) => p.name).join(', ')} (set in by compose.mjs; edit the piece files, not this block) */\n${pieces.map((p) => `/* ---- ${p.name} ---- */\n${p.css}`).join('\n\n')}\n</style>`);
page = page.replace('<!-- pieces:js -->', () => `<script>\n${kit}\n</script>\n${pieces.map((p) => `<script>\n/* ---- ${p.name} ---- */\n${p.js}\n</script>`).join('\n')}`);

writeFileSync(opt('out'), page);
console.log(`${opt('out')}: ${pieces.length} pieces (${pieces.map((p) => p.name).join(', ')}), ${(page.length / 1024).toFixed(0)} KB`);

if (opt('artifact')) {
  const mime = { '.otf': 'font/otf', '.ttf': 'font/ttf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' };
  const htmlTag = page.match(/<html\b([^>]*)>/i), attr = (n) => (htmlTag && htmlTag[1].match(new RegExp(`${n}="([^"]*)"`)) || [])[1];
  const head = (page.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i) || [, ''])[1], body = (page.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i) || [, ''])[1];
  let out = head.replace(/<meta charset[^>]*>\s*/i, '').replace(/<meta name="viewport"[^>]*>\s*/i, '').replace(/<link rel="(preconnect|preload)"[^>]*>\s*/gi, '').trim();
  const lang = attr('lang'), dir = attr('dir');
  if (lang || dir) out += `\n<script>${lang ? `document.documentElement.lang=${JSON.stringify(lang)};` : ''}${dir ? `document.documentElement.dir=${JSON.stringify(dir)};` : ''}</script>`;
  out += '\n' + body.trim() + '\n';
  let inlined = 0;
  out = out.replace(/url\((['"]?)([^'")]+)\1\)/g, (all, q, ref) => {
    if (/^(data:|https?:|#)/.test(ref)) return all;
    const file = path.resolve(outDir, ref), type = mime[path.extname(file).toLowerCase()];      // the page names its assets relative to itself
    if (!existsSync(file) || !type) return all;
    inlined++;
    return `url(data:${type};base64,${readFileSync(file).toString('base64')})`;
  });
  writeFileSync(opt('artifact'), out);
  console.log(`${opt('artifact')}: wrapper tags dropped, ${inlined} local file(s) inlined, ${(out.length / 1024).toFixed(0)} KB`);
}
