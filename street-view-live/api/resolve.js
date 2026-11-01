// Expands Google Maps short links (maps.app.goo.gl / goo.gl/maps) to the full URL,
// so a link shared from the Google Maps phone app can be pasted directly.
const ALLOWED = /^(maps\.app\.goo\.gl|goo\.gl|(www\.)?google\.[a-z.]+|maps\.google\.[a-z.]+)$/i;

export default async function handler(req, res) {
  const raw = String(req.query.url || '');
  let u;
  try { u = new URL(raw); } catch { return res.status(400).json({ error: 'bad url' }); }
  if (u.protocol !== 'https:' || !ALLOWED.test(u.hostname)) return res.status(400).json({ error: 'not a google maps link' });

  let current = u.toString();
  for (let i = 0; i < 6; i++) {
    const r = await fetch(current, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0' } });
    const loc = r.headers.get('location');
    if (!loc || r.status < 300 || r.status >= 400) break;
    current = new URL(loc, current).toString();
  }
  res.status(200).json({ url: current });
}
