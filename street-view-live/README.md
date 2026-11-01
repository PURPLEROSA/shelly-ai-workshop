# STREET VIEW · MAGIC 8 LIVE

Pick a spot in Google Street View, upload a character, write the situation, choose a camera,
and Gemini (Nano Banana) shoots the character there.

## Vercel
Root Directory: `street-view-live` · Framework: Other · no build step.

Environment Variables (Project → Settings → Environment Variables):

| Key | What |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Google Cloud key with **Maps JavaScript API**, **Street View Static API**, **Geocoding API** enabled. Restrict by HTTP referrer to the Vercel domain. |
| `GEMINI_API_KEY` | From aistudio.google.com/app/apikey (billing enabled for image models). |
| `GEMINI_IMAGE_MODEL` | Optional. Overrides the first model tried. Default chain: `gemini-3-pro-image-preview` → `gemini-3.1-flash-image-preview` → `gemini-2.5-flash-image`. |
| `ACCESS_CODE` | Optional. If set, the app asks for this code before generating (protects your Gemini credits). |

Without env vars the app still works: paste keys into the 🔑 box (stored in that browser only).

## Files
- `index.html` — the studio (Maps, upload, situation, camera picker, results)
- `api/generate.js` — builds the prompt (camera specs live here) and calls Gemini with model fallback
- `api/resolve.js` — expands `maps.app.goo.gl` short links
- `api/config.js` — tells the browser which keys exist server-side
