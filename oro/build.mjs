// Builds two things from oro.html (the single page source):
//   index.html  one file for the web; loads the 3D library and the fonts from their CDNs
//   app/        the installable build: everything it needs is in the folder, so it runs offline.
//               This folder is what a host serves as a PWA, or what a native wrapper (Capacitor) takes as its web root.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const dir = new URL('.', import.meta.url);
const src = readFileSync(new URL('oro.html', dir), 'utf8');
const [head, body] = src.split('<!--body-->');
const SKY = '#2ea6ff';
const page = (extra, h, b) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="${SKY}">
${extra}<style>:root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}img{max-width:100%}[hidden]{display:none!important}</style>
${h.trim()}
</head>
<body>
${b.trim()}
</body>
</html>
`;
const swap = (text, from, to) => { if (!from.test(text)) throw new Error('build: expected to find ' + from); return text.replace(from, to); };

// 1. web
writeFileSync(new URL('index.html', dir), page('', head, body));

// 2. app
const appHead = swap(head, /<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/, '<link rel="stylesheet" href="fonts/fonts.css">');
const appBody = swap(body, /<script src="https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/three\.js\/r128\/three\.min\.js"><\/script>/, '<script src="vendor/three.min.js"></script>')
  + `\n<script>if('serviceWorker' in navigator&&location.protocol.startsWith('http'))addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));</script>`;
const appMeta = `<meta name="description" content="ORO. Close the circle: a one-thumb puzzle on a 3D dial.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon-180.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="ORO">
`;
const appHtml = page(appMeta, appHead, appBody);
writeFileSync(new URL('app/index.html', dir), appHtml);

writeFileSync(new URL('app/manifest.webmanifest', dir), JSON.stringify({
  name: 'ORO', short_name: 'ORO', description: 'Close the circle. A one-thumb puzzle on a 3D dial.',
  start_url: './', scope: './', display: 'standalone', orientation: 'portrait',
  background_color: SKY, theme_color: SKY, categories: ['games', 'puzzle'],
  icons: [
    { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
    { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    { src: 'icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
  ]
}, null, 2) + '\n');

// The service worker caches the whole app on first visit. Its cache name changes whenever the page does,
// so a new build replaces the old one cleanly.
const ASSETS = ['./', 'index.html', 'manifest.webmanifest', 'vendor/three.min.js', 'fonts/fonts.css', 'fonts/lilita-one.woff2', 'fonts/fredoka.woff2',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/maskable-512.png', 'icons/apple-touch-icon-180.png', 'icons/favicon-32.png'];
const ver = createHash('sha1').update(appHtml).digest('hex').slice(0, 10);
writeFileSync(new URL('app/sw.js', dir), `const CACHE='oro-${ver}',ASSETS=${JSON.stringify(ASSETS)};
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(n=>n!==CACHE).map(n=>caches.delete(n)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(r=>r||fetch(e.request)))});
`);
console.log('built oro/index.html and oro/app/ (cache oro-' + ver + ')');
