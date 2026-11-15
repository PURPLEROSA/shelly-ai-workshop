// Wraps oro.html (the page source) into a standalone index.html that opens from disk or any static host.
import { readFileSync, writeFileSync } from 'node:fs';
const dir = new URL('.', import.meta.url);
const src = readFileSync(new URL('oro.html', dir), 'utf8');
const [head, body] = src.split('<!--body-->');
const out = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a1024" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f2dfd4" media="(prefers-color-scheme: light)">
<style>:root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}img{max-width:100%}[hidden]{display:none!important}</style>
${head.trim()}
</head>
<body>
${body.trim()}
</body>
</html>
`;
writeFileSync(new URL('index.html', dir), out);
console.log('built oro/index.html', out.length, 'bytes');
