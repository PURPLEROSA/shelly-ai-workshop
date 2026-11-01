// עיצוב בהשראת האתר shelly-agents-workshop: תכלת, ורוד, נייר, דיו וסגול
const sharp = require('sharp');
const fs = require('fs');

const C = {
  blue: 'DDF4FF', blueDeep: 'BFE3F2', pink: 'F4B8CA', rose: 'D996AA', paper: 'F7F2ED',
  ink: '3C3C40', muted: '585860', purple: '72536F', white: 'FFFDFB', line: 'D6CBD5',
  pale: 'EEF8FF', paleLine: 'CFE6F5',
  tPink: 'F8D3DF', tMint: 'E3EEDD', tButter: 'F6E7C8', tBlue: 'D6EEFA', tLilac: 'E9DDF0',
};
const H = 'Bamberger FM Black';
const B = 'Heebo';
const W = 13.333, X0 = 0.75, X1 = 12.583, CW = X1 - X0;
const IC = 'assets/ic/';

function t(s, text, x, y, w, h, o = {}) {
  const base = {
    x, y, w, h, fontFace: B, fontSize: 14, color: C.ink, align: 'right', rtlMode: true,
    valign: 'top', margin: 0, isTextBox: true, lang: 'he-IL', lineSpacingMultiple: 1.12,
  };
  s.addText(text, Object.assign(base, o));
}
// English / LTR text
function en(s, text, x, y, w, h, o = {}) {
  t(s, text, x, y, w, h, Object.assign({ rtlMode: false, align: 'left', lang: 'en-US' }, o));
}
// "[...]" segments become purple bold runs
function runs(str, o = {}) {
  const out = [];
  str.split(/(\[[^\]]+\])/).forEach(p => {
    if (!p) return;
    if (p.startsWith('[')) out.push({ text: p, options: Object.assign({}, o, { color: C.purple, bold: true }) });
    else out.push({ text: p, options: Object.assign({}, o) });
  });
  return out;
}

function chrome(s, label, o = {}) {
  const col = o.light ? C.white : C.ink;
  t(s, [{ text: 'שלי אור גיסר', options: {} }, { text: '.', options: { color: o.light ? C.pink : C.purple } }],
    9.4, 0.38, 3.18, 0.5, { fontFace: H, fontSize: 20, color: col });
  if (label) en(s, label, X0, 0.47, 6, 0.3, { fontSize: 9, bold: true, charSpacing: 2, color: col });
}

function head(s, kicker, title, purplePart, o = {}) {
  const ltr = kicker && /^[\d–\-\s:'·.]+$/.test(kicker);
  if (kicker) t(s, kicker, X0, 1.0, CW, 0.3, Object.assign({ fontSize: 12, bold: true, color: C.purple }, ltr ? { rtlMode: false } : {}));
  const r = [{ text: title, options: {} }];
  if (purplePart) r.push({ text: purplePart, options: { color: C.purple } });
  s.addText(r, { placeholder: 'title', rtlMode: true, align: 'right', lang: 'he-IL' });
}

function rr(s, x, y, w, h, fill, line, r = 0.14, lw = 0.75) {
  s.addShape('roundRect', { x, y, w, h, fill: fill ? { color: fill } : { type: 'none' }, line: line ? { color: line, width: lw } : { type: 'none' }, rectRadius: r });
}
function card(s, x, y, w, h, fill = C.white, line = C.line, r = 0.16) { rr(s, x, y, w, h, fill, line, r); }
function box(s, x, y, w, h, fill = C.paper) {
  s.addShape('rect', { x, y, w, h, fill: { color: fill }, line: { color: C.ink, width: 0.75 } });
}
function hline(s, x, y, w, color = C.ink, wt = 0.75) {
  s.addShape('line', { x, y, w, h: 0, line: { color, width: wt } });
}
function icon(s, name, x, y, sz, variant = '') {
  s.addImage({ path: IC + name + variant + '.png', x, y, w: sz, h: sz, altText: name });
}
function tile(s, name, x, y, sz = 0.56, bg = C.tPink, variant = '') {
  rr(s, x, y, sz, sz, bg, null, 0.12);
  icon(s, name, x + sz * 0.22, y + sz * 0.22, sz * 0.56, variant);
}
function pill(s, text, x, y, w, o = {}) {
  const h = o.h || 0.42;
  rr(s, x, y, w, h, o.fill || C.white, o.line === undefined ? C.ink : o.line, h / 2);
  t(s, text, x, y, w, h, { align: 'center', valign: 'middle', fontSize: o.size || 13, bold: true, color: o.color || C.ink });
}
function numPill(s, num, x, y) {
  rr(s, x, y, 0.62, 0.34, null, C.ink, 0.17);
  en(s, num, x, y, 0.62, 0.34, { align: 'center', valign: 'middle', fontSize: 11 });
}
function checks(s, items, x, y, w, h, o = {}) {
  const arr = items.map((it, i) => ({
    text: '\u200F✓\u00A0\u00A0' + it, options: { breakLine: i < items.length - 1, paraSpaceAfter: o.gap || 8 },
  }));
  t(s, arr, x, y, w, h, { fontSize: o.size || 14, color: o.color || C.ink });
}
function btn(s, text, x, y, w, h = 0.62) {
  rr(s, x, y, w, h, C.ink, null, 0.09);
  t(s, text, x + 0.7, y, w - 0.95, h, { valign: 'middle', bold: true, fontSize: 15, color: C.white });
  t(s, '←', x + 0.2, y, 0.5, h, { valign: 'middle', fontSize: 20, color: C.white, align: 'center' });
}
function arrow(s, x, y, w = 0.5, h = 0.5, color = C.purple) {
  t(s, '←', x, y, w, h, { align: 'center', valign: 'middle', fontSize: 24, color, bold: true });
}
// prompt card in the site's "you give / you get" style
function prompt(s, x, y, w, h, label, text, o = {}) {
  card(s, x, y, w, h, o.fill || C.white);
  t(s, label, x + 0.25, y + 0.18, w - 0.5, 0.3, { fontSize: 11, bold: true, color: C.muted });
  rr(s, x + 0.22, y + 0.55, w - 0.44, h - 0.77, C.pale, C.paleLine, 0.1);
  const tx = Object.assign({ fontSize: o.size || 14, bold: true, lineSpacingMultiple: 1.2 }, o.ltr ? { rtlMode: false, align: 'left', lang: 'en-US' } : {});
  t(s, o.ltr ? text : runs(text), x + 0.42, y + 0.7, w - 0.84, h - 1.05, tx);
}
function tip(s, x, y, w, h, label, text, o = {}) {
  rr(s, x, y, w, h, o.fill || C.pink, o.line || null, 0.16);
  t(s, label, x + 0.3, y + 0.16, w - 0.6, 0.42, { fontFace: H, fontSize: 18, color: C.purple });
  t(s, runs(text), x + 0.3, y + 0.58, w - 0.6, h - 0.7, { fontSize: o.size || 14 });
}

async function crop(src, aspect, name, gravity = 'center') {
  const out = 'assets/crop/' + name;
  if (fs.existsSync(out)) return out;
  fs.mkdirSync('assets/crop', { recursive: true });
  const m = await sharp(src).metadata();
  let w = m.width, h = Math.round(m.width / aspect);
  if (h > m.height) { h = m.height; w = Math.round(m.height * aspect); }
  const top = gravity === 'south' ? m.height - h : Math.round((m.height - h) / 2);
  await sharp(src).extract({ left: Math.round((m.width - w) / 2), top, width: w, height: h })
    .flatten({ background: '#FFFDFB' }).jpeg({ quality: 84 }).toFile(out);
  return out;
}
// tilted photo frame with pink offset, like the hero image on the site
function photo(s, path, x, y, w, h, rot = -3, back = C.pink) {
  s.addShape('rect', { x: x - 0.2, y: y + 0.2, w, h, fill: { color: back }, line: { type: 'none' }, rotate: rot - 1.5 });
  s.addShape('rect', { x, y, w, h, fill: { color: C.white }, line: { color: C.ink, width: 0.75 }, rotate: rot });
  s.addImage({ path, x: x + 0.14, y: y + 0.14, w: w - 0.28, h: h - 0.28, rotate: rot, altText: 'תמונה' });
}
function robot(s, name, x, y, sz) {
  s.addImage({ path: 'assets/img/mini-agent-' + name + '.png', x, y, w: sz, h: sz, altText: 'סוכן' });
}

module.exports = { C, H, B, W, X0, X1, CW, t, en, runs, chrome, head, rr, card, box, hline, icon, tile, pill, numPill, checks, btn, arrow, prompt, tip, crop, photo, robot };
