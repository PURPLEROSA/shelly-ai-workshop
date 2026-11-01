// Street View × character × situation × camera → one photograph, via Gemini image models.
// Body: { street, avatars[], situation, camera, aspect, place, geminiKey?, code? }
//   street  — base64 JPEG captured from Street View in the browser
//   avatars — 1–3 base64 JPEGs of the same character

const CAMERAS = {
  iphone: {
    label: 'iPhone 17 Pro',
    spec: 'Shot on an iPhone 17 Pro main camera (24mm equivalent, f/1.78). Authentic smartphone photo: computational HDR, crisp detail, deep depth of field, natural phone colour science, slightly bright shadows. Looks like a real photo a friend took on the street and posted to Instagram.'
  },
  selfie: {
    label: 'Selfie',
    spec: 'Front-camera smartphone selfie taken at arm\'s length by the person themself. Slight wide-angle distortion close to the lens, the person\'s arm reaching toward the camera at the frame edge, face well lit, the location visible behind them. Casual, authentic, unposed social-media feel.'
  },
  leica: {
    label: 'Leica M11 · 35mm',
    spec: 'Shot on a Leica M11 with a 35mm Summilux at f/2. Classic street photography: candid moment, the person caught mid-action, beautiful micro-contrast, natural rendering, subtle vignetting, honest documentary colours. Feels like a Magnum street photograph.'
  },
  portrait85: {
    label: 'Canon R5 · 85mm f/1.2',
    spec: 'Shot on a Canon EOS R5 with an RF 85mm f/1.2 at f/1.4. Professional portrait: tack-sharp eyes, creamy smooth bokeh, background softly melted but the location still recognisable, flattering compression, rich skin tones.'
  },
  wide24: {
    label: 'Sony A7 IV · 24mm',
    spec: 'Shot on a Sony A7 IV with a 24mm f/1.4 lens at f/4. Environmental portrait: the location dominates the frame, the person placed with intention inside it, strong leading lines from the street, sharp front to back.'
  },
  fuji: {
    label: 'Fujifilm X100VI',
    spec: 'Shot on a Fujifilm X100VI (23mm, f/2) with the Classic Chrome film simulation. Muted teal-and-amber tones, gentle contrast, subtle grain, the soft-edged glow of the fixed lens wide open. Effortless, stylish everyday look.'
  },
  portra: {
    label: 'Kodak Portra 400 · 35mm',
    spec: 'Shot on 35mm analogue film, Kodak Portra 400, with a Contax T2. Warm pastel colour palette, visible fine film grain, soft highlight roll-off, slight halation around light sources, true analogue imperfection. Nostalgic and real.'
  },
  disposable: {
    label: 'Disposable + flash',
    spec: 'Shot on a cheap disposable film camera with the direct on-camera flash firing. Harsh frontal flash, bright subject against a darker background, red-eye risk, saturated colours, heavy grain, slight light leak, early-2000s party snapshot energy.'
  },
  polaroid: {
    label: 'Polaroid SX-70',
    spec: 'Shot on a Polaroid SX-70 instant camera. Soft focus, dreamy faded colours, lifted blacks, creamy highlights, the slightly chemical colour shifts of instant film. Present only the image area (no white frame, no border).'
  },
  hasselblad: {
    label: 'Hasselblad X2D · medium format',
    spec: 'Shot on a Hasselblad X2D 100C medium-format camera with an 80mm lens. High-fashion editorial: immense detail and tonal depth, sculpted light, magazine-cover polish, deliberate styling and posture, like a Vogue street editorial.'
  },
  paparazzi: {
    label: 'Paparazzi · 200mm',
    spec: 'Paparazzi photo shot from across the street on a 70–200mm telephoto at 200mm. Strong background compression, the person caught unaware, partially framed by passers-by or a car out of focus in the foreground, slight motion, tabloid candid authenticity.'
  },
  drone: {
    label: 'Drone · from above',
    spec: 'Shot from a DJI drone hovering about 8 metres above, angled down at 45 degrees. The person seen from above inside the street layout, the geometry of the location reading clearly, crisp aerial clarity, small but recognisable figure.'
  }
};

const ASPECTS = new Set(['1:1', '4:5', '3:4', '9:16', '16:9']);

const MODELS = [
  process.env.GEMINI_IMAGE_MODEL,
  'gemini-3-pro-image-preview',
  'gemini-3.1-flash-image-preview',
  'gemini-2.5-flash-image'
].filter(Boolean);

function buildPrompt({ situation, camera, place, avatarCount }) {
  const cam = CAMERAS[camera] || CAMERAS.iphone;
  const refs = avatarCount > 1
    ? `IMAGES 2–${avatarCount + 1} are reference photos of ONE person (the same character from different angles).`
    : 'IMAGE 2 is a reference photo of a person.';
  return [
    `You are given ${avatarCount + 1} images. IMAGE 1 is a real Google Street View capture of a location${place ? ` (${place})` : ''}. ${refs}`,
    'Create ONE new photorealistic photograph of this exact person physically present in this exact location, living the situation below.',
    '',
    'SITUATION (may be written in Hebrew; interpret it faithfully and stage it naturally):',
    situation || 'Standing naturally in the street, relaxed, as if a friend just called their name.',
    '',
    'IDENTITY — highest priority:',
    '- Preserve the face, facial structure, skin tone, hair, body type and identity EXACTLY as in the reference photo(s). Do not beautify, slim, age or alter them.',
    '- Keep their clothing from the reference unless the situation asks for something else.',
    '',
    'LOCATION:',
    '- Keep the place from IMAGE 1 clearly recognisable: architecture, storefronts, signage, street furniture, colours and atmosphere.',
    '- You may reframe it as a real photographer standing there would, but it must read as the same spot.',
    '- Correct perspective and scale; feet (or seat) grounded on the real surface; light direction, colour temperature and shadows matching the scene.',
    '- Remove every Street View artefact: no blur patches, no stitching seams, no Google logos, no navigation arrows, no watermark.',
    '',
    `CAMERA — ${cam.label}:`,
    cam.spec,
    '',
    'OUTPUT: a single real-looking photograph. No text, no captions, no borders, no collage.'
  ].join('\n');
}

async function callGemini({ model, key, prompt, images, aspect, withAspect }) {
  const parts = [{ text: prompt }, ...images.map(data => ({ inline_data: { mime_type: 'image/jpeg', data } }))];
  const body = { contents: [{ role: 'user', parts }], generationConfig: { responseModalities: ['TEXT', 'IMAGE'] } };
  if (withAspect) body.generationConfig.imageConfig = { aspectRatio: aspect };

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 110_000);
  let resp, data;
  try {
    resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key },
      body: JSON.stringify(body),
      signal: ctrl.signal
    });
    data = await resp.json().catch(() => ({}));
  } finally {
    clearTimeout(timer);
  }
  if (!resp.ok) {
    const err = new Error(data?.error?.message || `HTTP ${resp.status}`);
    err.status = resp.status;
    throw err;
  }
  const cand = data?.candidates?.[0];
  for (const p of cand?.content?.parts || []) {
    const inline = p.inlineData || p.inline_data;
    if (inline?.data) return { mime: inline.mimeType || inline.mime_type || 'image/png', data: inline.data };
  }
  const reason = cand?.finishReason || data?.promptFeedback?.blockReason || 'NO_IMAGE';
  const err = new Error(`no image returned (${reason})`);
  err.status = 422;
  err.reason = reason;
  throw err;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  const b = req.body || {};

  if (process.env.ACCESS_CODE && b.code !== process.env.ACCESS_CODE) {
    return res.status(401).json({ error: 'code', message: 'קוד גישה שגוי.' });
  }
  const key = process.env.GEMINI_API_KEY || (typeof b.geminiKey === 'string' ? b.geminiKey.trim() : '');
  if (!key) return res.status(400).json({ error: 'nokey', message: 'חסר Gemini API Key.' });

  const street = typeof b.street === 'string' ? b.street : '';
  const avatars = Array.isArray(b.avatars) ? b.avatars.filter(a => typeof a === 'string' && a.length > 100).slice(0, 3) : [];
  if (street.length < 100) return res.status(400).json({ error: 'nostreet', message: 'לא התקבל פריים מ-Street View.' });
  if (!avatars.length) return res.status(400).json({ error: 'noavatar', message: 'לא התקבלה תמונת דמות.' });

  const aspect = ASPECTS.has(b.aspect) ? b.aspect : '9:16';
  const camera = CAMERAS[b.camera] ? b.camera : 'iphone';
  const situation = String(b.situation || '').slice(0, 1200);
  const place = String(b.place || '').slice(0, 200);
  const prompt = buildPrompt({ situation, camera, place, avatarCount: avatars.length });
  const images = [street, ...avatars];

  let lastErr;
  for (const model of MODELS) {
    for (const withAspect of [true, false]) {
      try {
        const out = await callGemini({ model, key, prompt, images, aspect, withAspect });
        return res.status(200).json({ image: `data:${out.mime};base64,${out.data}`, model, camera: CAMERAS[camera].label, prompt });
      } catch (e) {
        lastErr = e;
        if (e.status === 400 && withAspect && !/api key/i.test(e.message)) continue; // retry without imageConfig
        break;
      }
    }
    // only fall through to the next model when this one is missing / not allowed for the key
    if (![404, 403].includes(lastErr?.status) && !/not found|not supported|permission/i.test(lastErr?.message || '')) break;
  }

  const msg = lastErr?.message || 'generation failed';
  let he = msg;
  if (/quota|rate|exhausted/i.test(msg)) he = 'עברת את מכסת Gemini. מחכים דקה ומנסים שוב, או בודקים חיוב ב-AI Studio.';
  else if (/api key not valid|invalid.*key|API_KEY_INVALID/i.test(msg)) he = 'מפתח Gemini לא תקין.';
  else if (/SAFETY|PROHIBITED|IMAGE_SAFETY|blocked/i.test(msg)) he = 'Gemini חסם את הבקשה מסיבות בטיחות. מנסחים אחרת את הסיטואציה או מחליפים תמונת דמות.';
  else if (/NO_IMAGE|STOP/i.test(msg)) he = 'המודל החזיר טקסט במקום תמונה. לוחצים שוב, זה בדרך כלל עובר בניסיון השני.';
  else if (lastErr?.name === 'AbortError') he = 'היצירה לקחה יותר מדי זמן. מנסים שוב.';
  return res.status(lastErr?.status && lastErr.status < 600 ? lastErr.status : 500).json({ error: 'gen', message: he, detail: msg, prompt });
}

export { CAMERAS, buildPrompt };
