const CACHE='oro-e4c898c57b',ASSETS=["./","index.html","manifest.webmanifest","vendor/three.min.js","fonts/fonts.css","fonts/lilita-one.woff2","fonts/fredoka.woff2","icons/icon-192.png","icons/icon-512.png","icons/maskable-512.png","icons/apple-touch-icon-180.png","icons/favicon-32.png"];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(n=>n!==CACHE).map(n=>caches.delete(n)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(r=>r||fetch(e.request)))});
