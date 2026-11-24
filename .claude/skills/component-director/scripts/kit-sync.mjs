#!/usr/bin/env node
// kit-sync.mjs — copy scripts/kit.js into pieces, between the markers it carries.
//
// A piece has to be one file that runs anywhere, so it carries its own copy of the kit.
// Put these two markers in the piece's script, on one line:
//
//     /* kit:start */ /* kit:end */
//
// then run:
//
//     node kit-sync.mjs piece.html [more.html ...]     write the current kit into each file
//     node kit-sync.mjs --check piece.html             exit 1 if a file's copy differs from kit.js
//
// Only the block between the markers is touched.
import { readFileSync, writeFileSync } from 'node:fs';

const args = process.argv.slice(2);
const check = args[0] === '--check';
const files = check ? args.slice(1) : args;
if (!files.length) { console.log('usage: node kit-sync.mjs [--check] piece.html [more.html ...]'); process.exit(1); }

const kit = readFileSync(new URL('./kit.js', import.meta.url), 'utf8').trim();
const block = /\/\* kit:start[\s\S]*?\/\* kit:end \*\//;
let stale = 0;
for (const f of files) {
  const src = readFileSync(f, 'utf8');
  if (!block.test(src)) { console.log(`${f}: no kit markers, left alone`); continue; }
  const next = src.replace(block, () => kit);
  if (next === src) { console.log(`${f}: up to date`); continue; }
  if (check) { console.log(`${f}: differs from kit.js`); stale++; continue; }
  writeFileSync(f, next);
  console.log(`${f}: kit written`);
}
process.exit(stale ? 1 : 0);
