// node build.js  ->  grok-bot-workshop.pptx
const pptxgen = require('pptxgenjs');
const path = require('path');
const L = require('./lib');
const { C, H, B } = L;

const SKILL = process.env.PPTX_SKILL || '/root/.claude/skills/synced/b6a9d79b-29d0-41c4-becc-3dad364cd46c_c6773d2e-8047-4318-9607-6d5299b9a9fa/pptx';
const THEME = {
  name: 'Shelly Agents Workshop', headFontFace: H, bodyFontFace: B,
  colors: { dk1: C.ink, lt1: C.white, dk2: C.purple, lt2: C.blue, accent1: C.pink, accent2: C.purple, accent3: C.rose,
    accent4: C.blueDeep, accent5: C.paper, accent6: C.muted, hlink: C.purple, folHlink: C.rose },
};

(async () => {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';
  pres.author = 'שלי אור גיסר';
  pres.title = 'סוכנים מאפס עם Grok Bot';
  pres.theme = { headFontFace: H, bodyFontFace: B };

  const titlePh = { name: 'title', type: 'title', x: L.X0, y: 1.3, w: L.CW, h: 0.95 };
  const titleOpts = { fontFace: H, fontSize: 38, color: C.ink, align: 'right', valign: 'top', margin: 0, rtlMode: true };
  const num = { x: 0.5, y: 6.98, w: 0.8, h: 0.3, fontFace: B, fontSize: 10, color: C.muted, align: 'left' };
  const foot = (col) => ({ text: { text: 'סוכנים מאפס עם Grok · 2.11', options: { x: 8.6, y: 6.98, w: 4.0, h: 0.3, fontFace: B, fontSize: 10, color: col, align: 'right', rtlMode: true } } });
  for (const [name, bg] of [['BLUE', C.blue], ['PAPER', C.paper], ['PINK', C.pink]]) {
    pres.defineSlideMaster({ title: name, background: { color: bg }, slideNumber: num,
      objects: [foot(C.muted), { placeholder: { options: Object.assign({}, titlePh, titleOpts), text: '' } }] });
  }
  pres.defineSlideMaster({ title: 'DIVIDER', background: { color: C.pink }, slideNumber: num, objects: [] });
  pres.defineSlideMaster({ title: 'DIVIDER_BLUE', background: { color: C.blue }, slideNumber: num, objects: [] });
  pres.defineSlideMaster({ title: 'INK', background: { color: C.ink }, slideNumber: Object.assign({}, num, { color: 'BFBFC4' }), objects: [] });

  const ctx = { pres, titleOpts };
  ctx.slide = (layout, section, notes) => {
    const s = pres.addSlide({ masterName: layout, sectionTitle: section });
    if (notes) s.addNotes(notes);
    return s;
  };
  ctx.section = (title) => pres.addSection({ title });

  await require('./slides-a')(ctx);
  await require('./slides-b')(ctx);

  const out = 'grok-bot-workshop.pptx';
  await pres.writeFile({ fileName: out });
  try {
    const { applyTheme } = require(path.join(SKILL, 'scripts/apply_theme.js'));
    await applyTheme(out, THEME);
  } catch (e) { console.warn('theme colors not applied:', e.message.split('\n')[0]); }
  console.log('wrote', out);
})();
