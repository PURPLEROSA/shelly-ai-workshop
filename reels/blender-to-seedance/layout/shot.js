// usage: node shot.js <out.png> '<cfg json>'
const { chromium } = require('playwright'); const path = require('path'); const http = require('http'); const fs = require('fs');
(async () => {
  const [out, cfg, page = 'overlay.html'] = process.argv.slice(2); const root = __dirname;
  const srv = http.createServer((req, res) => {
    const f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(f, (e, b) => { if (e) { res.writeHead(404); res.end(); } else { res.writeHead(200, { 'Content-Type': ({svg:'image/svg+xml',html:'text/html',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp'})[f.split('.').pop().toLowerCase()] || 'application/octet-stream' }); res.end(b); } });
  }).listen(0);
  const port = srv.address().port;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.goto(`http://127.0.0.1:${port}/${page}?cfg=${encodeURIComponent(cfg || '{}')}`);
  await p.waitForSelector('body[data-ready="1"]');
  await p.locator('#c').screenshot({ path: out });
  await b.close(); srv.close();
})();
