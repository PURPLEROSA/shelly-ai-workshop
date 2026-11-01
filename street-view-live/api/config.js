// Public config for the browser. The Maps key is a browser key by nature
// (Maps JavaScript API loads client-side) — restrict it by HTTP referrer in Google Cloud.
export default function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).json({
    mapsKey: process.env.GOOGLE_MAPS_API_KEY || null,
    hasGeminiKey: Boolean(process.env.GEMINI_API_KEY),
    needsCode: Boolean(process.env.ACCESS_CODE)
  });
}
