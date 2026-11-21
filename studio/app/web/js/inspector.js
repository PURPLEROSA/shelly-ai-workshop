// The properties panel: what you can change about the selected item, or about the project.
import { el, icon, slider, segmented, toggle, toast, debounce } from './ui.js';
import { App } from './app.js';
import { S, on, op, track, findItem, info, media, mainTrack, select } from './store.js';
import { actions } from './timeline.js';
import { zoomAt } from './player.js';

const RATIO_LABELS = { source: 'מקורי', '9:16': '9:16', '16:9': '16:9', '1:1': '1:1', '4:5': '4:5' };
const SHORTCUTS = [['נגן / עצור', 'Space'], ['פיצול בסמן', 'S'], ['מחיקת קליפ', 'Del'], ['סימון טווח', 'I / O'],
  ['חיתוך הטווח', 'X'], ['קיפריים של זום', 'K'], ['פריים אחורה / קדימה', '← / →'], ['ביטול / חזרה', 'Ctrl+Z / Y']];

export function buildInspector(host) {
  let busy = false;
  let dirty = false;
  host.addEventListener('pointerdown', () => { busy = true; });
  window.addEventListener('pointerup', () => { if (busy) { busy = false; if (dirty) { dirty = false; render(); } } });

  const sec = (title, ...kids) => el('div', { class: 'isec' }, title ? el('span', { class: 'lbl', text: title }) : null, ...kids);
  const set = (id, args, coalesce) => op('set_item', { item: id, ...args }, { coalesce });
  const actBtn = (ic, label, fn, danger) => el('button', { class: 'chip' + (danger ? ' danger' : ''), type: 'button', onclick: fn }, icon(ic), label);

  function projectPanel() {
    const d = S.derived;
    const fpsSel = el('select', { onchange: () => op('set_canvas', { fps: fpsSel.value === 'auto' ? 'auto' : +fpsSel.value }) },
      ...App.state.fps_choices.map((f) => el('option', { value: f, text: f === 'auto' ? 'אוטומטי' : `${f} fps`, selected: String(f) === String(S.doc.canvas.fps) })));
    return [
      el('div', { class: 'ihead' }, el('span', { class: 'eyebrow', text: 'PROJECT' }), el('h3', { text: 'פרויקט' }),
        el('p', { class: 'muted small', text: 'בוחרים קליפ בטיימליין כדי לערוך אותו.' })),
      sec('גודל פריים', segmented(App.state.ratios.map((r) => ({ value: r, label: RATIO_LABELS[r] || r })), S.doc.canvas.ratio,
        (v) => op('set_canvas', { ratio: v }), 'גודל פריים'),
        el('small', { class: 'muted', dir: 'ltr', text: `${d.frame.w}×${d.frame.h}` })),
      sec('קצב פריימים', fpsSel),
      sec('קיצורי מקלדת', el('dl', { class: 'keys' }, ...SHORTCUTS.flatMap(([a, k]) => [el('dt', { text: a }), el('dd', {}, el('kbd', { text: k }))]))),
    ];
  }

  function mediaPanel(tr, it) {
    const m = media(it.media);
    const inf = info(it.id);
    const isVideo = tr.kind === 'video';
    const hasSound = m.has_audio || m.kind === 'audio';
    const out = [el('div', { class: 'ihead' },
      el('span', { class: 'eyebrow', text: isVideo ? (tr.main ? 'CLIP' : 'OVERLAY') : 'AUDIO' }),
      el('h3', { text: it.label || m.name }),
      el('p', { class: 'muted small', dir: 'ltr', text: `${inf.dur.toFixed(2)}s · ${tr.name}` }))];

    if (m.kind !== 'image') {
      out.push(sec(null, slider({ label: 'מהירות', min: 0.25, max: 4, step: 0.05, value: it.speed, format: (v) => `×${(+v).toFixed(2)}`,
        onChange: (v) => set(it.id, { speed: v }) })));
    }
    if (hasSound) {
      out.push(sec(null,
        slider({ label: 'עוצמה', min: 0, max: 2, step: 0.01, value: it.volume, format: (v) => Math.round(v * 100) + '%',
          onInput: (v) => { it.volume = v; }, onChange: (v) => set(it.id, { volume: v }) }),
        toggle(it.mute, (v) => set(it.id, { mute: v }), 'השתקה'),
        slider({ label: 'פייד פנימה', min: 0, max: Math.min(5, inf.dur / 2), step: 0.05, value: it.fade_in, format: (v) => (+v).toFixed(2) + 's',
          onChange: (v) => set(it.id, { fade_in: v }) }),
        slider({ label: 'פייד החוצה', min: 0, max: Math.min(5, inf.dur / 2), step: 0.05, value: it.fade_out, format: (v) => (+v).toFixed(2) + 's',
          onChange: (v) => set(it.id, { fade_out: v }) })));
    }
    if (isVideo) {
      // colour look
      const lookGrid = el('div', { class: 'chips' },
        el('button', { class: 'chip' + (!it.look ? ' on' : ''), type: 'button', text: 'בלי', onclick: () => set(it.id, { look: '' }) }),
        ...App.state.looks.map((lk) => el('button', { class: 'chip' + (it.look === lk.id ? ' on' : ''), type: 'button', text: lk.name, onclick: () => set(it.id, { look: lk.id }) })));
      out.push(sec('לוק', lookGrid));

      // zoom
      const local = Math.max(0, Math.min(inf.dur, S.time - inf.start));
      const cur = zoomAt(it.zoom, local);
      const draft = () => { S.zoomDraft = { item: it.id, s: zs.value(), x: zx.value(), y: zy.value() }; };
      const zs = slider({ label: 'קירוב', min: 1, max: 3, step: 0.01, value: cur.s, format: (v) => `×${(+v).toFixed(2)}`, onInput: draft });
      const zx = slider({ label: 'מרכז אופקי', min: 0, max: 1, step: 0.01, value: cur.x, format: (v) => Math.round(v * 100) + '%', onInput: draft });
      const zy = slider({ label: 'מרכז אנכי', min: 0, max: 1, step: 0.01, value: cur.y, format: (v) => Math.round(v * 100) + '%', onInput: draft });
      const addKey = async () => {
        const r = await op('add_zoom_keyframe', { item: it.id, at: S.time, scale: zs.value(), x: zx.value(), y: zy.value() });
        if (r) S.zoomDraft = null;
      };
      host._addKey = addKey;
      const keys = el('div', { class: 'kflist' }, ...(it.zoom || []).map((k, i) => el('div', { class: 'kfrow' },
        el('button', { class: 'tlink', dir: 'ltr', text: `${k.t.toFixed(2)}s · ×${k.s}`, onclick: () => S.player.seek(inf.start + k.t) }),
        el('button', { class: 'ib sm', 'aria-label': 'מחיקת קיפריים', onclick: () => op('remove_zoom_keyframe', { item: it.id, index: i }) }, icon('x')))));
      out.push(sec('זום',
        el('div', { class: 'chips' },
          actBtn('zoom', 'פאנץ׳', () => op('quick_zoom', { item: it.id, kind: 'punch', at: S.time })),
          actBtn('zoom', 'דחיפה פנימה', () => op('quick_zoom', { item: it.id, kind: 'in', at: S.time })),
          actBtn('zoom', 'יציאה', () => op('quick_zoom', { item: it.id, kind: 'out', at: S.time }))),
        zs, zx, zy,
        el('div', { class: 'chips' }, actBtn('key', 'קיפריים כאן (K)', addKey),
          (it.zoom || []).length ? actBtn('x', 'ניקוי הזום', () => { S.zoomDraft = null; op('remove_zoom_keyframe', { item: it.id, index: -1 }); }) : null),
        keys));

      if (tr.main) {
        const idx = mainTrack().items.findIndex((x) => x.id === it.id);
        if (idx > 0) {
          const type = (it.transition || {}).type || 'none';
          const tsel = el('select', { onchange: () => op('set_transition', { item: it.id, type: tsel.value, duration: (it.transition || {}).dur || 0.5 }) },
            el('option', { value: 'none', text: 'חיתוך ישר', selected: type === 'none' }),
            ...App.state.transitions.map((t) => el('option', { value: t.id, text: t.name, selected: t.id === type })));
          out.push(sec('מעבר מהקליפ הקודם', tsel,
            type !== 'none' ? slider({ label: 'אורך המעבר', min: 0.1, max: 2, step: 0.05, value: it.transition.dur, format: (v) => (+v).toFixed(2) + 's',
              onChange: (v) => op('set_transition', { item: it.id, type, duration: v }) }) : null));
        }
      } else {
        out.push(sec('שכבה',
          segmented([{ value: 'normal', label: 'רגיל' }, { value: 'screen', label: 'אוברליי' }], it.blend, (v) => set(it.id, { blend: v }), 'מצב שכבה'),
          slider({ label: 'שקיפות', min: 0, max: 1, step: 0.01, value: it.opacity, format: (v) => Math.round(v * 100) + '%',
            onChange: (v) => set(it.id, { opacity: v }) })));
      }
    }
    out.push(sec('פעולות', el('div', { class: 'chips' },
      actBtn('cut', 'פיצול בסמן', actions.split), actBtn('copy', 'שכפול', actions.duplicate),
      isVideo && m.has_audio && !it.mute ? actBtn('music', 'הפרדת אודיו', async () => {
        const r = await op('detach_audio', { item: it.id });
        if (r && r.job) track(r.job, null, () => toast('האודיו הופרד לערוץ משלו.'));
      }) : null,
      actBtn('trash', 'מחיקה', actions.remove, true))));
    return out;
  }

  function textPanel(tr, it) {
    const st = it.style;
    const style = (patch) => op('set_item', { item: it.id, style: patch }, { coalesce: 'textstyle' });
    const input = el('textarea', { rows: 3, dir: 'auto' });
    input.value = it.text;
    const send = debounce(() => op('set_item', { item: it.id, text: input.value }, { coalesce: 'text-' + it.id }), 350);
    input.addEventListener('input', send);
    const font = el('select', { onchange: () => style({ font: font.value }) },
      ...App.state.fonts.map((f) => el('option', { value: f.id, text: f.label, selected: f.id === st.font })));
    const color = (label, key) => {
      const c = el('input', { type: 'color', value: st[key], 'aria-label': label, onchange: () => style({ [key]: c.value.toUpperCase() }) });
      return el('label', { class: 'color' }, c, el('span', { text: label }));
    };
    return [
      el('div', { class: 'ihead' }, el('span', { class: 'eyebrow', text: 'TITLE' }), el('h3', { text: 'טקסט על המסך' }),
        el('p', { class: 'muted small', dir: 'ltr', text: `${it.dur.toFixed(2)}s · ${tr.name}` })),
      sec('הטקסט', input),
      sec('סגנון', el('div', { class: 'chips' }, ...App.state.title_presets.map((p) =>
        el('button', { class: 'chip' + (st.preset === p.id ? ' on' : ''), type: 'button', text: p.name, onclick: () => op('set_item', { item: it.id, style: p.style }) })))),
      sec(null, el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'פונט' }), font),
        slider({ label: 'גודל', min: 0.03, max: 0.16, step: 0.002, value: st.size, format: (v) => Math.round(v * 1000) / 10 + '%', onChange: (v) => style({ size: v }) }),
        slider({ label: 'מיקום בגובה', min: 0.06, max: 0.94, step: 0.01, value: st.y, format: (v) => Math.round(v * 100) + '%', onChange: (v) => style({ y: v }) }),
        slider({ label: 'משך', min: 0.3, max: 20, step: 0.1, value: it.dur, format: (v) => (+v).toFixed(1) + 's', onChange: (v) => op('trim_item', { item: it.id, duration: v }) })),
      sec('רקע', segmented([{ value: 'none', label: 'בלי' }, { value: 'pill', label: 'פיל' }, { value: 'block', label: 'בלוק' }], st.bg, (v) => style({ bg: v }), 'רקע'),
        el('div', { class: 'colors' }, color('טקסט', 'color'), color('רקע', 'bg_color'), color('קו מתאר', 'stroke_color'))),
      sec('פעולות', el('div', { class: 'chips' }, actBtn('copy', 'שכפול', actions.duplicate), actBtn('trash', 'מחיקה', actions.remove, true))),
    ];
  }

  function render() {
    if (!S.doc || !S.derived) return;
    if (busy) { dirty = true; return; }
    host._addKey = null;
    const found = S.sel && findItem(S.sel);
    const scrollTop = host.scrollTop;
    if (!found) host.replaceChildren(...projectPanel());
    else if (found.track.kind === 'text') host.replaceChildren(...textPanel(found.track, found.item));
    else host.replaceChildren(...mediaPanel(found.track, found.item));
    host.scrollTop = scrollTop;
  }

  on('state', render);
  on('select', () => { host.scrollTop = 0; render(); });
  return { addKeyframe: () => { if (host._addKey) host._addKey(); else if (S.sel) toast('זום אפשר להוסיף לקליפ וידאו.'); else select(null); } };
}
