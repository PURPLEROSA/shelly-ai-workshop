// Side panels of the editor: captions, AI and export.
import { api, followJob } from './api.js';
import { el, icon, fmt, fmtSize, toast, segmented, toggle, slider, progressBar, confirmBox } from './ui.js';
import { App, openSettings } from './app.js';

const RATIO_LABELS = { source: 'מקורי', '9:16': '9:16', '1:1': '1:1', '4:5': '4:5', '16:9': '16:9' };

// --------------------------------------------------------------- captions

export function buildCaptionsPanel(e) {
  const panel = el('div', { class: 'panel', dataset: { panel: 'captions' } });
  const style = () => e.cap.style;
  const change = (patch, keepPreset = false) => {
    Object.assign(e.cap.style, patch);
    if (!keepPreset) { e.cap.style.preset = ''; markPreset(); }
    e.save();
  };

  const enabled = toggle(e.cap.enabled, (v) => { e.cap.enabled = v; panel.classList.toggle('off', !v); e.shownKey = null; e.save(); }, 'כתוביות בסרטון');
  panel.classList.toggle('off', !e.cap.enabled);

  // presets, each drawn by the real renderer
  const grid = el('div', { class: 'presets' });
  const cards = new Map();
  const markPreset = () => { for (const [id, c] of cards) c.classList.toggle('on', id === style().preset); };
  for (const p of App.state.presets) {
    const img = el('img', { alt: '', draggable: 'false' });
    const card = el('button', { type: 'button', class: 'preset', onclick: () => {
      e.cap.style = { ...p.style };
      markPreset();
      drawControls();
      e.save();
    } }, el('span', { class: 'preset-view' }, img), el('span', { class: 'preset-name', text: p.name }));
    cards.set(p.id, card);
    grid.append(card);
    fetch('/api/preview-style', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: p.style, w: 420, texts: ['ככה', 'זה', 'נראה'], active: 1 }) })
      .then((r) => r.ok ? r.blob() : null).then((b) => { if (b) img.src = URL.createObjectURL(b); }).catch(() => {});
  }
  markPreset();

  const controls = el('div', { class: 'controls' });
  const color = (label, key) => {
    const input = el('input', { type: 'color', value: style()[key], 'aria-label': label, oninput: () => change({ [key]: input.value.toUpperCase() }) });
    return el('label', { class: 'color' }, input, el('span', { text: label }));
  };
  function drawControls() {
    const s = style();
    const font = el('select', { onchange: () => change({ font: font.value }) },
      ...App.state.fonts.map((f) => el('option', { value: f.id, text: f.label + (f.hebrew ? '' : ' (לטיני בלבד)'), selected: f.id === s.font })));
    controls.replaceChildren(
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'פונט' }), font),
      slider({ label: 'גודל', min: 0.03, max: 0.14, step: 0.002, value: s.size, format: (v) => Math.round(v * 1000) / 10 + '%', onInput: (v) => change({ size: v }) }),
      slider({ label: 'מיקום בגובה', min: 0.08, max: 0.92, step: 0.01, value: s.y, format: (v) => Math.round(v * 100) + '%', onInput: (v) => change({ y: v }) }),
      slider({ label: 'מילים בכל כתובית', min: 1, max: 7, step: 1, value: s.max_words, onInput: (v) => change({ max_words: v }) }),
      el('div', { class: 'field' }, el('span', { class: 'lbl', text: 'הדגשת המילה הנאמרת' }),
        segmented([{ value: 'none', label: 'בלי' }, { value: 'color', label: 'צבע' }, { value: 'box', label: 'תיבה' }], s.highlight, (v) => change({ highlight: v }), 'הדגשת מילה')),
      el('div', { class: 'field' }, el('span', { class: 'lbl', text: 'רקע' }),
        segmented([{ value: 'none', label: 'בלי' }, { value: 'pill', label: 'פיל' }, { value: 'block', label: 'בלוק' }], s.bg, (v) => change({ bg: v }), 'רקע')),
      el('div', { class: 'colors' }, color('טקסט', 'color'), color('מילה מודגשת', 'active_color'), color('תיבת הדגשה', 'active_bg'), color('רקע', 'bg_color'), color('קו מתאר', 'stroke_color')),
      slider({ label: 'שקיפות הרקע', min: 0, max: 1, step: 0.05, value: s.bg_opacity, format: (v) => Math.round(v * 100) + '%', onInput: (v) => change({ bg_opacity: v }) }),
      slider({ label: 'קו מתאר', min: 0, max: 0.2, step: 0.01, value: s.stroke, format: (v) => Math.round(v * 100) + '%', onInput: (v) => change({ stroke: v }) }),
      slider({ label: 'צל', min: 0, max: 1, step: 0.05, value: s.shadow, format: (v) => Math.round(v * 100) + '%', onInput: (v) => change({ shadow: v }) }),
      toggle(s.strip_punct, (v) => change({ strip_punct: v }), 'בלי סימני פיסוק'));
  }
  drawControls();

  panel.append(
    el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow', text: 'CAPTIONS' }), el('h3', { text: 'כתוביות' }), enabled),
    el('div', { class: 'panel-body' },
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'סגנון' }), grid),
      el('details', { class: 'sec fold' }, el('summary', { text: 'התאמה אישית' }), controls)));
  return panel;
}

// --------------------------------------------------------------------- AI

const QUICK = [
  { label: 'להדק', text: 'להוריד חזרות, התחלות שנקטעו ומשפטים שלא מוסיפים, בלי לשנות את המסר.' },
  { label: 'גרסת 30 שניות', text: 'לקצר לגרסה של עד 30 שניות עם פתיחה חזקה.' },
  { label: 'גרסת 60 שניות', text: 'לקצר לגרסה של עד 60 שניות ולשמור על הרעיונות המרכזיים.' },
  { label: 'פתיחה חזקה', text: 'לחתוך את ההקדמה כך שהסרטון ייפתח במשפט הכי חזק.' },
];

export function buildAiPanel(e) {
  const panel = el('div', { class: 'panel', dataset: { panel: 'ai' } });
  const body = el('div', { class: 'panel-body' });
  const head = el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow', text: 'AI EDITOR' }), el('h3', { text: 'עריכה עם AI' }));
  panel.append(head, body);

  const run = async (payload, onDone, button) => {
    const bar = progressBar();
    const note = el('p', { class: 'muted small', text: 'המודל עובד…' });
    const box = el('div', { class: 'ai-wait' }, note, bar);
    button.disabled = true;
    button.after(box);
    try {
      const r = await api(`/api/projects/${e.pid}/ai`, { method: 'POST', body: payload });
      let fake = 0.1;
      const j = await followJob(r.job.id, (job) => { fake = Math.min(0.92, fake + 0.025); bar.set(fake); if (job.message) note.textContent = job.message; }, () => e.alive);
      if (!j) return;
      if (j.status === 'done') onDone(j.result); else toast(j.error || 'הפעולה נכשלה.', { error: true });
    } catch (err) {
      toast(err.message, { error: true });
    } finally {
      box.remove();
      button.disabled = false;
    }
  };

  const draw = () => {
    const ai = App.state.ai;
    body.replaceChildren();
    if (!ai.ready) {
      body.append(el('div', { class: 'card soft' },
        el('h4', { text: 'מחברים מודל, ואז מבקשים במילים' }),
        el('p', { class: 'muted', text: 'למשל ״לקצר ל-30 שניות״ או ״לפתוח במשפט הכי חזק״. אפשר מודל מקומי וחינמי דרך Ollama, או Claude ו-GPT עם מפתח API.' }),
        el('button', { class: 'btn btn-dark btn-sm', onclick: () => openSettings('ai') }, 'חיבור מודל', el('i', { class: 'ar' }, icon('spark'))),
        el('p', { class: 'muted small', text: 'בינתיים, הסרת שתיקות, מילות מילוי וחזרות עובדת בלי שום מודל, מעל התמלול.' })));
      return;
    }
    const input = el('textarea', { rows: 3, placeholder: 'מה לעשות עם הסרטון? למשל: לקצר ל-30 שניות ולפתוח במשפט הכי חזק', dir: 'auto' });
    const result = el('div', { class: 'ai-result' });
    const go = el('button', { class: 'btn btn-cta btn-sm', onclick: () => {
      if (!e.n) { toast('צריך תמלול לפני שאפשר לערוך עם AI.'); return; }
      if (!input.value.trim()) { input.focus(); return; }
      run({ mode: 'edit', instruction: input.value }, (r) => {
        result.replaceChildren();
        if (!r.indices.length) {
          result.append(el('div', { class: 'card soft' }, el('b', { text: 'אין שינויים' }), el('p', { class: 'muted', text: r.summary || 'המודל לא מצא מה לחתוך.' })));
          return;
        }
        e.setDeleted(r.indices, true);
        const list = el('ul', { class: 'cuts' });
        for (const c of r.cuts) {
          list.append(el('li', {}, el('button', { type: 'button', onclick: () => { e.video.currentTime = e.words[c.from].s; } },
            el('s', { text: c.text }), c.reason ? el('small', { text: c.reason }) : null)));
        }
        result.append(el('div', { class: 'card soft' },
          el('b', { text: `נחתכו ${r.indices.length} מילים ב-${r.cuts.length} מקומות` }),
          r.summary ? el('p', { class: 'muted', text: r.summary }) : null,
          list,
          el('button', { class: 'btn btn-ghost btn-sm plain', text: 'ביטול השינוי', onclick: () => { e.undo(); result.replaceChildren(); } })));
      }, go);
    } }, 'לערוך', el('i', { class: 'ar' }, icon('spark')));
    const quick = el('div', { class: 'chips' }, ...QUICK.map((q) => el('button', { type: 'button', class: 'chip', text: q.label, onclick: () => { input.value = q.text; input.focus(); } })));

    const textOut = el('textarea', { rows: 8, readonly: true, hidden: true, dir: 'auto' });
    const copyBtn = el('button', { class: 'btn btn-ghost btn-sm plain', hidden: true, text: 'העתקה',
      onclick: async () => { try { await navigator.clipboard.writeText(textOut.value); toast('הועתק.'); } catch { textOut.select(); } } });
    const kinds = el('div', { class: 'chips' });
    for (const k of App.state.text_kinds) {
      const b = el('button', { type: 'button', class: 'chip', text: k.label, onclick: () => {
        if (!e.n) { toast('צריך תמלול כדי לכתוב טקסטים.'); return; }
        run({ mode: 'text', kind: k.id }, (r) => { textOut.value = r.text; textOut.hidden = false; copyBtn.hidden = false; }, b);
      } });
      kinds.append(b);
    }
    body.append(
      el('p', { class: 'ai-model muted small' }, 'מחובר: ', el('b', { text: `${ai.label} · ${ai.model}` }), ' ',
        el('button', { class: 'tlink', text: 'החלפה', onclick: () => openSettings('ai') })),
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'עריכה לפי הנחיה' }), quick, input, go, result),
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'טקסטים לפוסט' }), kinds, textOut, copyBtn));
  };
  draw();
  const onSettings = () => { if (e.alive) draw(); };
  document.addEventListener('studio:settings', onSettings);
  e.cleanup.push(() => document.removeEventListener('studio:settings', onSettings));
  return panel;
}

// ----------------------------------------------------------------- export

export function buildExportPanel(e) {
  const panel = el('div', { class: 'panel', dataset: { panel: 'export' } });
  let quality = '1080';
  const ratio = segmented(App.state.ratios.map((r) => ({ value: r, label: RATIO_LABELS[r] || r })), e.ratio,
    (v) => { e.ratio = v; e.save(); }, 'פורמט');
  const qual = segmented([{ value: '720', label: '720p' }, { value: '1080', label: '1080p' }, { value: 'source', label: 'מקורי' }], quality, (v) => { quality = v; }, 'איכות');
  const summary = el('p', { class: 'muted small' });
  const list = el('div', { class: 'exports' });
  const progress = el('div', { class: 'export-prog', hidden: true });

  const drawList = () => {
    list.replaceChildren();
    const items = e.p.exports || [];
    if (!items.length) { list.append(el('p', { class: 'muted small', text: 'סרטונים שמייצאים מופיעים כאן, מוכנים להורדה.' })); return; }
    for (const x of items) {
      const url = `/api/projects/${e.pid}/exports/${encodeURIComponent(x.file)}`;
      list.append(el('div', { class: 'export-row' },
        el('div', { class: 'ex-meta' },
          el('b', { text: `${fmt(x.duration)} · ${x.width}×${x.height}` }),
          el('small', { text: `${fmtSize(x.size)}${x.captions ? ' · עם כתוביות' : ''} · ${new Date(x.created * 1000).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}` })),
        el('div', { class: 'ex-actions' },
          el('a', { class: 'btn btn-dark btn-sm', href: url + '?dl=1', download: x.file }, 'הורדה', el('i', { class: 'ar' }, icon('download'))),
          el('a', { class: 'ib sm', href: url, target: '_blank', rel: 'noopener', title: 'צפייה', 'aria-label': 'צפייה' }, icon('eye')),
          el('button', { class: 'ib sm', title: 'מחיקה', 'aria-label': 'מחיקת הייצוא', onclick: async () => {
            if (!(await confirmBox('למחוק את הקובץ?', 'הסרטון המיוצא יימחק מהמחשב. הפרויקט עצמו נשאר.', 'מחיקה'))) return;
            try { await api(url, { method: 'DELETE' }); e.p.exports = e.p.exports.filter((y) => y.file !== x.file); drawList(); } catch (err) { toast(err.message, { error: true }); }
          } }, icon('trash')))));
    }
  };

  const follow = (jobId) => {
    const bar = progressBar();
    const note = el('span', { class: 'muted small', text: 'מתחיל…' });
    progress.replaceChildren(el('div', { class: 'row between' }, note,
      el('button', { class: 'tlink', text: 'ביטול', onclick: () => api(`/api/jobs/${jobId}/cancel`, { method: 'POST' }).catch(() => {}) })), bar);
    progress.hidden = false;
    go.disabled = true;
    followJob(jobId, (j) => { bar.set(j.progress); note.textContent = `${j.message || 'מייצא…'} ${Math.round(j.progress * 100)}%`; }, () => e.alive)
      .then((j) => {
        if (!e.alive || !j) return;
        progress.hidden = true;
        go.disabled = false;
        if (j.status === 'done') {
          e.p.exports = [j.result, ...(e.p.exports || [])];
          drawList();
          toast('הסרטון מוכן.', { action: { label: 'הורדה', run: () => { const a = list.querySelector('a.btn'); if (a) a.click(); } } });
        } else if (j.status === 'error') toast(j.error || 'הייצוא נכשל.', { error: true });
      });
  };

  const go = el('button', { class: 'btn btn-cta', onclick: async () => {
    try {
      e.save.flush();
      await new Promise((r) => setTimeout(r, 120));
      const r = await api(`/api/projects/${e.pid}/export`, { method: 'POST', body: { ratio: e.ratio, quality, captions: e.cap.enabled } });
      follow(r.job.id);
    } catch (err) { toast(err.message, { error: true }); }
  } }, 'ייצוא הסרטון', el('i', { class: 'ar' }, icon('arrow')));

  const sub = (kind, label) => el('a', { class: 'chip', href: `/api/projects/${e.pid}/text.${kind}`, download: '' }, icon('download'), label);

  e.hooks.derived.push((d) => {
    const n = d.keep.length;
    summary.textContent = `אורך אחרי עריכה: ${fmt(d.out_duration)} · ${d.frame.w}×${d.frame.h}${n === 2 ? ' · חיתוך אחד' : n > 2 ? ` · ${n - 1} חיתוכים` : ''}${e.cap.enabled && d.cues.length ? ' · עם כתוביות' : ''}`;
    go.disabled = !n || !progress.hidden;
  });

  panel.append(
    el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow', text: 'EXPORT' }), el('h3', { text: 'ייצוא' })),
    el('div', { class: 'panel-body' },
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'פורמט' }), ratio,
        el('small', { class: 'muted', text: 'פורמט שונה מהמקור חותך את הסרטון סביב המרכז.' })),
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'איכות' }), qual),
      el('div', { class: 'sec' }, summary, go, progress),
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'קבצים מוכנים' }), list),
      el('div', { class: 'sec' }, el('span', { class: 'lbl', text: 'טקסט' }),
        el('div', { class: 'chips' }, sub('srt', 'כתוביות SRT'), sub('vtt', 'כתוביות VTT'), sub('txt', 'תמלול נקי')))));
  drawList();
  const running = (e.p.jobs || []).find((j) => j.kind === 'export');
  if (running) follow(running.id);
  return panel;
}
