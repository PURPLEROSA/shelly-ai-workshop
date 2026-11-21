// The editor: player, transcript editing and timeline.
import { api, followJob } from './api.js';
import { el, icon, icons, fmt, toast, modal, confirmBox, segmented, progressBar, debounce } from './ui.js';
import { App, renderTop } from './app.js';
import { buildCaptionsPanel, buildAiPanel, buildExportPanel } from './panels.js';

let E = null;
const MIN_TRIM = 0.12;
const isNarrow = () => window.matchMedia('(max-width: 899px)').matches;

export function closeEditor() {
  if (!E) return;
  E.alive = false;
  cancelAnimationFrame(E.raf);
  if (E.video) { E.video.pause(); E.video.removeAttribute('src'); E.video.load(); }
  for (const fn of E.cleanup) { try { fn(); } catch { /* ignore */ } }
  E = null;
}

export async function openEditor(pid, view) {
  closeEditor();
  const e = E = { pid, view, alive: true, cleanup: [], hooks: { derived: [] }, images: new Map() };
  view.replaceChildren(el('div', { class: 'center-msg' }, el('span', { class: 'spin dark' })));
  renderTop();
  let p;
  try {
    p = await api('/api/projects/' + pid);
  } catch (err) {
    if (!e.alive) return;
    view.replaceChildren(el('div', { class: 'center-msg' }, el('div', { class: 'card fatal' },
      el('h2', { text: 'הפרויקט לא נמצא' }), el('p', { class: 'muted', text: err.message }),
      el('a', { class: 'btn btn-dark btn-sm plain', href: '#/', text: 'חזרה לפרויקטים' }))));
    return;
  }
  if (!e.alive) return;
  e.p = p;
  if (p.status === 'error') return showError(e);
  if (p.status !== 'ready') return showPreparing(e);
  build(e);
}

function reopen(e) { if (e.alive) openEditor(e.pid, e.view); }

function showError(e) {
  e.view.replaceChildren(el('div', { class: 'center-msg' }, el('div', { class: 'card fatal' },
    el('h2', { text: 'משהו השתבש עם הסרטון הזה' }),
    el('p', { class: 'muted', text: e.p.error || 'שגיאה לא ידועה.' }),
    el('div', { class: 'row gap' },
      el('a', { class: 'btn btn-ghost btn-sm plain', href: '#/', text: 'חזרה' }),
      el('button', { class: 'btn btn-dark btn-sm plain', text: 'מחיקת הפרויקט',
        onclick: async () => { await api('/api/projects/' + e.pid, { method: 'DELETE' }); location.hash = '#/'; } })))));
}

function showPreparing(e) {
  const bar = progressBar();
  const msg = el('p', { class: 'muted', text: 'מכין את הסרטון…' });
  e.view.replaceChildren(el('div', { class: 'center-msg' }, el('div', { class: 'card prep' },
    el('span', { class: 'eyebrow', text: 'GETTING READY' }),
    el('h2', { text: e.p.name }), msg, bar,
    el('p', { class: 'muted small', text: 'אפשר להשאיר את החלון פתוח. הכל קורה במחשב שלך.' }))));
  const job = (e.p.jobs || [])[0];
  if (!job) { setTimeout(() => reopen(e), 1500); return; }
  let opened = false;
  followJob(job.id, (j) => {
    bar.set(j.progress);
    if (j.message) msg.textContent = j.message;
    // the video becomes usable as soon as the preview exists; transcription continues inside
    if (!opened && j.message && j.message.includes('תמלול')) { opened = true; reopen(e); }
  }, () => e.alive && !opened).then((j) => { if (j && !opened) reopen(e); });
}

// ------------------------------------------------------------------ build

function build(e) {
  const p = e.p;
  e.words = p.words;
  e.n = e.words.length;
  e.del = Uint8Array.from(e.words, (w) => (w.d ? 1 : 0));
  e.texts = e.words.map((w) => w.t);
  e.sent = e.texts.slice();
  e.tighten = p.tighten;
  e.ratio = p.ratio;
  e.cap = JSON.parse(JSON.stringify(p.captions));
  e.derived = p.derived;
  e.hist = [];
  e.future = [];
  e.rev = 0;
  e.spans = [];
  e.cur = -1;
  e.cursor = -1;
  e.shownKey = null;
  e.peaks = [];

  // ----- header
  const title = el('span', { class: 'title', contenteditable: 'plaintext-only', spellcheck: 'false', text: p.name, 'aria-label': 'שם הפרויקט' });
  title.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); title.blur(); } });
  title.addEventListener('blur', async () => {
    const name = title.textContent.trim();
    if (!name) { title.textContent = p.name; return; }
    if (name !== p.name) { p.name = name; try { await api('/api/projects/' + e.pid, { method: 'PATCH', body: { name } }); } catch (err) { toast(err.message, { error: true }); } }
  });
  e.badge = el('span', { class: 'len-badge', title: 'אורך מקורי ואורך אחרי עריכה' });
  e.undoBtn = el('button', { class: 'ib', 'aria-label': 'ביטול', title: 'ביטול (Ctrl+Z)', onclick: () => undo(e) }, icon('undo'));
  e.redoBtn = el('button', { class: 'ib', 'aria-label': 'ביצוע מחדש', title: 'ביצוע מחדש (Ctrl+Shift+Z)', onclick: () => redo(e) }, icon('redo'));
  renderTop({
    start: el('div', { class: 'top-start' },
      el('a', { class: 'ib', href: '#/', 'aria-label': 'חזרה לפרויקטים', title: 'חזרה' }, icon('back')), title),
    middle: el('div', { class: 'top-mid' }, e.badge, e.undoBtn, e.redoBtn),
    end: el('button', { class: 'btn btn-cta btn-sm', onclick: () => { e.setTab('export'); } }, 'ייצוא', el('i', { class: 'ar' }, icon('arrow'))),
  });

  // ----- stage
  e.video = el('video', { playsinline: true, preload: 'auto', src: `/api/projects/${e.pid}/proxy.mp4` });
  e.capLayer = el('div', { class: 'cap' });
  e.bigPlay = el('button', { class: 'bigplay', 'aria-label': 'ניגון', html: icons.play });
  e.screen = el('div', { class: 'screen' }, e.video, e.capLayer, e.bigPlay);
  e.screenWrap = el('div', { class: 'screen-wrap' }, e.screen);
  e.playBtn = el('button', { class: 'ib play', 'aria-label': 'ניגון או השהיה', html: icons.play, onclick: () => togglePlay(e) });
  e.timeLbl = el('span', { class: 'time', dir: 'ltr', text: '0:00 / 0:00' });
  const restart = el('button', { class: 'ib sm restart', 'aria-label': 'לתחילת הסרטון', title: 'לתחילת הסרטון', onclick: () => seek(e, firstKeep(e)) }, icon('start'));
  e.canvas = el('canvas', { class: 'timeline', 'aria-label': 'ציר הזמן של הסרטון', role: 'img' });
  const stage = el('div', { class: 'stage' }, e.screenWrap,
    el('div', { class: 'playbar' }, e.playBtn, restart, e.timeLbl, el('div', { class: 'tl-wrap' }, e.canvas)));
  e.screen.addEventListener('click', () => togglePlay(e));

  // ----- tabs
  const tabDefs = [
    { id: 'transcript', label: 'תמלול', ic: 'text', only: 'narrow' },
    { id: 'captions', label: 'כתוביות', ic: 'cc' },
    { id: 'ai', label: 'AI', ic: 'spark' },
    { id: 'export', label: 'ייצוא', ic: 'download' },
  ];
  const tabs = el('nav', { class: 'tabs', 'aria-label': 'כלי עריכה' });
  for (const t of tabDefs) {
    tabs.append(el('button', { type: 'button', class: t.only === 'narrow' ? 'narrow-only' : '', dataset: { tab: t.id }, onclick: () => e.setTab(t.id) }, icon(t.ic), el('span', { text: t.label })));
  }
  e.setTab = (id) => {
    e.root.dataset.tab = id;
    for (const b of tabs.children) b.classList.toggle('on', b.dataset.tab === id || (id === 'transcript' && b.dataset.tab === 'captions' && !isNarrow()));
    sizeScreen(e);
  };

  // ----- transcript column
  e.transcript = el('div', { class: 'transcript', lang: 'he' });
  e.selbar = el('div', { class: 'selbar', hidden: true });
  const work = el('div', { class: 'work' }, buildToolbar(e), e.transcript, e.selbar);

  e.root = el('section', { class: 'editor', dataset: { tab: 'captions' } }, work, stage, tabs,
    buildCaptionsPanel(e), buildAiPanel(e), buildExportPanel(e));
  e.view.replaceChildren(e.root);
  e.setTab(isNarrow() ? 'transcript' : 'captions');

  e.save = debounce(() => doSave(e), 160);
  e.setDeleted = (indices, flag) => setDeleted(e, indices, flag);
  e.undo = () => undo(e);
  e.reopen = () => reopen(e);
  e.pushHist = () => pushHist(e);

  renderTranscript(e);
  bindSelection(e);
  bindKeys(e);
  bindTimeline(e);
  onDerived(e);

  const ro = new ResizeObserver(() => { sizeScreen(e); drawTimeline(e); });
  ro.observe(e.screenWrap);
  ro.observe(e.canvas.parentElement);
  e.cleanup.push(() => ro.disconnect());

  e.video.addEventListener('play', () => syncPlayIcons(e));
  e.video.addEventListener('pause', () => syncPlayIcons(e));
  e.video.addEventListener('loadedmetadata', () => { seek(e, firstKeep(e)); });
  e.video.addEventListener('error', () => toast('לא הצלחנו לטעון את התצוגה המקדימה של הסרטון.', { error: true }));

  api(`/api/projects/${e.pid}/peaks`).then((r) => { if (e.alive) { e.peaks = r.peaks || []; drawTimeline(e); } }).catch(() => {});

  const tick = () => { if (!e.alive) return; frame(e); e.raf = requestAnimationFrame(tick); };
  e.raf = requestAnimationFrame(tick);

  // a transcription that is still running (fresh upload, or re-transcribe)
  const job = (p.jobs || []).find((j) => j.kind === 'process');
  if (job) followTranscription(e, job.id);
}

function followTranscription(e, jobId) {
  const bar = progressBar();
  const msg = el('p', { class: 'muted', text: 'מתמלל…' });
  const cancel = el('button', { class: 'tlink', text: 'ביטול', onclick: () => api(`/api/jobs/${jobId}/cancel`, { method: 'POST' }).catch(() => {}) });
  e.transcript.replaceChildren(el('div', { class: 'card inline-prog' },
    el('span', { class: 'eyebrow', text: 'TRANSCRIBING' }), el('h3', { text: 'מתמלל את הסרטון' }), msg, bar, cancel));
  followJob(jobId, (j) => { bar.set(j.progress); if (j.message) msg.textContent = j.message; }, () => e.alive)
    .then((j) => {
      if (!j || !e.alive) return;
      if (j.status === 'error') toast(j.error || 'התמלול נכשל.', { error: true });
      reopen(e);
    });
}

// ---------------------------------------------------------------- toolbar

function buildToolbar(e) {
  e.tightenSeg = segmented(
    [{ value: 0, label: 'כבוי' }, { value: 0.6, label: 'עדין' }, { value: 0.35, label: 'רגיל' }, { value: 0.2, label: 'הדוק' }],
    e.tighten || 0,
    (v) => { pushHist(e); e.tighten = v || null; refreshGaps(e); e.save(); },
    'קיצור שתיקות');
  const suggest = async (kind) => {
    try {
      const r = await api(`/api/projects/${e.pid}/suggest`, { method: 'POST', body: { kind } });
      if (r.indices.length) {
        setDeleted(e, r.indices, true);
        toast(r.summary + ' הן סומנו למחיקה.', { action: { label: 'ביטול', run: () => undo(e) } });
      } else toast(r.summary);
    } catch (err) { toast(err.message, { error: true }); }
  };
  const restoreAll = () => {
    const idx = [];
    for (let i = 0; i < e.n; i++) if (e.del[i]) idx.push(i);
    if (idx.length) setDeleted(e, idx, false); else toast('אין מחיקות לשחזר.');
  };
  return el('div', { class: 'toolbar' },
    el('div', { class: 'tool' }, el('span', { class: 'lbl', text: 'קיצור שתיקות' }), e.tightenSeg),
    el('div', { class: 'tool grow' },
      el('span', { class: 'lbl', text: 'ניקוי מהיר' }),
      el('div', { class: 'chips' },
        el('button', { class: 'chip', type: 'button', onclick: () => suggest('fillers') }, icon('cut'), 'מילות מילוי'),
        el('button', { class: 'chip', type: 'button', onclick: () => suggest('repeats') }, icon('cut'), 'חזרות'))),
    el('div', { class: 'tool-end' },
      el('button', { class: 'ib sm', type: 'button', title: 'שחזור כל המחיקות', 'aria-label': 'שחזור כל המחיקות', onclick: restoreAll }, icon('restore')),
      el('button', { class: 'ib sm', type: 'button', title: 'תמלול מחדש', 'aria-label': 'תמלול מחדש', onclick: () => retranscribeDialog(e) }, icon('mic'))));
}

function retranscribeDialog(e) {
  const st = App.state;
  const model = el('select', {}, ...st.models.map((m) => el('option', { value: m.id, text: m.label, selected: m.id === (e.p.transcript.model || st.settings.transcribe.model) })));
  const lang = el('select', {}, ...st.languages.map((l) => el('option', { value: l.id, text: l.label, selected: l.id === (e.p.transcript.language || st.settings.transcribe.language) })));
  const m = modal({
    title: 'תמלול מחדש',
    body: el('div', {},
      el('p', { class: 'muted', text: 'התמלול החדש מחליף את הנוכחי, כולל המחיקות והתיקונים שנעשו בו.' }),
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'מודל' }), model),
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'שפה' }), lang),
      el('div', { class: 'row end gap' },
        el('button', { class: 'btn btn-dark btn-sm', onclick: async () => {
          try {
            const r = await api(`/api/projects/${e.pid}/transcribe`, { method: 'POST', body: { model: model.value, language: lang.value } });
            m.close();
            followTranscription(e, r.job.id);
          } catch (err) { toast(err.message, { error: true }); }
        } }, 'להתחיל', el('i', { class: 'ar' }, icon('mic'))))),
  });
}

// ------------------------------------------------------------- transcript

function renderTranscript(e) {
  e.spans = [];
  e.gaps = [];
  const t = e.transcript;
  if (!e.n) {
    const tr = e.p.transcript;
    if ((e.p.jobs || []).some((j) => j.kind === 'process')) return;
    t.replaceChildren(el('div', { class: 'card inline-prog' },
      el('h3', { text: tr.status === 'error' ? 'התמלול לא הצליח' : 'עדיין אין תמלול' }),
      el('p', { class: 'muted', text: tr.error || 'אפשר לתמלל את הסרטון עכשיו. זה קורה כולו במחשב.' }),
      e.p.media.has_audio ? el('button', { class: 'btn btn-dark btn-sm', onclick: () => retranscribeDialog(e) }, 'תמלול', el('i', { class: 'ar' }, icon('mic'))) : null));
    return;
  }
  const frag = document.createDocumentFragment();
  let para = null;
  const gapChip = (i, gap) => {
    const chip = el('span', { class: 'gap', dataset: { i, gap: gap.toFixed(2) }, title: 'שתיקה', text: gap.toFixed(1) + ' שנ׳' });
    e.gaps.push(chip);
    return chip;
  };
  for (let i = 0; i < e.n; i++) {
    const w = e.words[i];
    const prev = e.words[i - 1];
    const gap = prev ? w.s - prev.e : w.s;
    if (!para || w.b) {
      para = el('p', { class: 'para' }, el('span', { class: 'ts', dir: 'ltr', text: fmt(w.s) }));
      frag.append(para);
    }
    if (gap >= 0.8) para.append(gapChip(i, gap), ' ');
    const span = el('span', { class: 'w', dataset: { i } });
    e.spans.push(span);
    para.append(span, ' ');
  }
  const tail = e.p.media.duration - e.words[e.n - 1].e;
  if (tail >= 0.8 && para) para.append(gapChip(e.n, tail));
  t.replaceChildren(frag);
  refreshWords(e);
  refreshGaps(e);
}

function refreshWords(e, indices) {
  const paint = (i) => {
    const span = e.spans[i];
    if (!span) return;
    const w = e.words[i];
    const text = e.texts[i];
    if (span.textContent !== (text || '∅')) span.textContent = text || '∅';
    span.classList.toggle('del', !!e.del[i]);
    span.classList.toggle('low', w.p < 0.5 && text === w.t && !w.o);
    span.classList.toggle('edited', text !== (w.o || w.t) || (!!w.o && text === w.t));
  };
  if (indices) indices.forEach(paint); else for (let i = 0; i < e.n; i++) paint(i);
}

function refreshGaps(e) {
  for (const chip of e.gaps || []) {
    const i = +chip.dataset.i;
    const gap = +chip.dataset.gap;
    const edge = i === 0 || i === e.n;
    const neighborsKept = edge ? true : !e.del[i - 1] && !e.del[i];
    const trimmed = e.tighten != null && neighborsKept && (edge ? gap > Math.max(e.tighten / 2, 0.3) : gap > e.tighten + MIN_TRIM);
    chip.classList.toggle('trimmed', trimmed);
  }
  if (e.tightenSeg) {
    // a value saved elsewhere may sit between the presets: light up the nearest one
    const t = e.tighten || 0;
    e.tightenSeg.setValue(t ? [0.6, 0.35, 0.2].reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a)) : 0);
  }
}

// ------------------------------------------------------------ edit state

function snapshot(e) { return { del: e.del.slice(), texts: e.texts.slice(), tighten: e.tighten }; }

function pushHist(e) {
  e.hist.push(snapshot(e));
  if (e.hist.length > 200) e.hist.shift();
  e.future = [];
  syncUndo(e);
}

function restore(e, s) {
  e.del = s.del.slice();
  e.texts = s.texts.slice();
  e.tighten = s.tighten;
  refreshWords(e);
  refreshGaps(e);
  syncUndo(e);
  e.save();
}

function undo(e) {
  if (!e.hist.length) return;
  e.future.push(snapshot(e));
  restore(e, e.hist.pop());
}

function redo(e) {
  if (!e.future.length) return;
  e.hist.push(snapshot(e));
  restore(e, e.future.pop());
}

function syncUndo(e) {
  e.undoBtn.disabled = !e.hist.length;
  e.redoBtn.disabled = !e.future.length;
}

function setDeleted(e, indices, flag) {
  const changed = indices.filter((i) => i >= 0 && i < e.n && !!e.del[i] !== !!flag);
  if (!changed.length) return;
  pushHist(e);
  for (const i of changed) e.del[i] = flag ? 1 : 0;
  refreshWords(e, changed);
  refreshGaps(e);
  e.save();
}

async function doSave(e) {
  if (!e.alive) return;
  const rev = ++e.rev;
  const t = {};
  for (let i = 0; i < e.n; i++) if (e.texts[i] !== e.sent[i]) t[i] = e.texts[i];
  const body = { d: Array.from(e.del).join(''), t, tighten: e.tighten, ratio: e.ratio, captions: e.cap, rev };
  try {
    const r = await api(`/api/projects/${e.pid}/edit`, { method: 'PUT', body });
    if (!e.alive) return;
    for (const k of Object.keys(t)) e.sent[+k] = t[k];
    if (rev !== e.rev) return; // a newer save is on its way
    e.derived = r.derived;
    onDerived(e);
  } catch (err) {
    if (e.alive) toast('השמירה נכשלה: ' + err.message, { error: true });
  }
}

function onDerived(e) {
  const d = e.derived;
  const src = e.p.media.duration;
  e.badge.replaceChildren(
    el('span', { dir: 'ltr', text: fmt(src) }),
    el('span', { class: 'arrow', html: icons.arrow }),
    el('b', { dir: 'ltr', text: fmt(d.out_duration) }));
  e.badge.classList.toggle('changed', Math.abs(src - d.out_duration) > 0.05);
  e.root.dataset.orient = d.frame.w > d.frame.h ? 'land' : 'port';
  e.capLayer.style.top = (d.band.top * 100) + '%';
  e.capLayer.style.height = (d.band.height * 100) + '%';
  e.shownKey = null;
  e.lastT = -1; // repaint the clock: the edited length may have changed
  syncUndo(e);
  sizeScreen(e);
  drawTimeline(e);
  preloadCaptions(e);
  for (const fn of e.hooks.derived) fn(d);
}

// ----------------------------------------------------------------- player

function firstKeep(e) { const k = e.derived.keep; return k.length ? k[0][0] : 0; }

function rangeIndex(keep, t) {
  let lo = 0, hi = keep.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (keep[mid][0] <= t) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return ans;
}

export function srcToOut(e, t) {
  const keep = e.derived.keep;
  let acc = 0;
  for (const [a, b] of keep) {
    if (t <= a) return acc;
    if (t < b) return acc + (t - a);
    acc += b - a;
  }
  return acc;
}

function seek(e, t) {
  const v = e.video;
  const max = isFinite(v.duration) ? v.duration : e.p.media.duration;
  try { v.currentTime = Math.max(0, Math.min(max - 0.01, t)); } catch { /* not ready yet */ }
}

function togglePlay(e) {
  const v = e.video;
  const keep = e.derived.keep;
  if (!v.paused) { v.pause(); return; }
  if (!keep.length) { toast('כל המילים מסומנות למחיקה, אין מה לנגן.'); return; }
  const last = keep[keep.length - 1][1];
  if (v.currentTime >= last - 0.06) seek(e, keep[0][0]);
  v.play().catch(() => {});
}

function syncPlayIcons(e) {
  const playing = !e.video.paused;
  e.playBtn.innerHTML = playing ? icons.pause : icons.play;
  e.bigPlay.classList.toggle('hide', playing);
}

function frame(e) {
  const v = e.video;
  const keep = e.derived.keep;
  const t = v.currentTime || 0;
  if (!v.paused && !v.seeking && keep.length) {
    const k = rangeIndex(keep, t);
    if (k === -1) seek(e, keep[0][0]);
    else if (t >= keep[k][1] - 0.015) {
      if (k + 1 < keep.length) seek(e, keep[k + 1][0]);
      else v.pause();
    }
  }
  if (t !== e.lastT) {
    e.lastT = t;
    e.timeLbl.textContent = `${fmt(srcToOut(e, t))} / ${fmt(e.derived.out_duration)}`;
    drawPlayhead(e, t);
    markCurrent(e, t);
  }
  showCaption(e, t);
}

function markCurrent(e, t) {
  if (!e.n) return;
  let lo = 0, hi = e.n - 1, idx = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (e.words[mid].s <= t + 0.02) { idx = mid; lo = mid + 1; } else hi = mid - 1;
  }
  if (idx >= 0 && t > e.words[idx].e + 0.25) idx = -1;
  if (idx === e.cur) return;
  if (e.cur >= 0 && e.spans[e.cur]) e.spans[e.cur].classList.remove('cur');
  e.cur = idx;
  if (idx < 0) return;
  const span = e.spans[idx];
  span.classList.add('cur');
  if (!e.video.paused && window.getSelection().isCollapsed) {
    const box = e.transcript.getBoundingClientRect();
    const r = span.getBoundingClientRect();
    if (r.top < box.top + 40 || r.bottom > box.bottom - 60) {
      e.transcript.scrollTo({ top: e.transcript.scrollTop + (r.top - box.top) - box.height * 0.35, behavior: 'smooth' });
    }
  }
}

// --------------------------------------------------------------- captions

function capWidth(e) {
  const px = (e.screen.clientWidth || 360) * Math.min(window.devicePixelRatio || 1, 2);
  for (const w of [360, 540, 720, 1080]) if (px <= w * 1.15) return w;
  return 1080;
}

function capImage(e, key) {
  const id = key + '@' + e.capW;
  let img = e.images.get(id);
  if (!img) {
    img = new Image();
    img.decoding = 'async';
    img.alt = '';
    img.draggable = false;
    img.src = `/api/cap/${key}.png?w=${e.capW}`;
    e.images.set(id, img);
  }
  return img;
}

function preloadCaptions(e) {
  e.capW = capWidth(e);
  const token = (e.preloadToken = {});
  if (!e.cap.enabled) return;
  const cues = e.derived.cues;
  if (!cues.length) return;
  const now = srcToOut(e, e.video.currentTime || 0);
  let start = cues.findIndex((c) => c.e > now);
  if (start < 0) start = 0;
  const order = [];
  const seen = new Set();
  for (let n = 0; n < cues.length; n++) {
    const k = cues[(start + n) % cues.length].k;
    if (!seen.has(k)) { seen.add(k); order.push(k); }
  }
  if (e.images.size > 2500) {
    for (const id of e.images.keys()) if (!seen.has(id.split('@')[0])) e.images.delete(id);
  }
  let i = 0;
  const pump = () => {
    if (!e.alive || e.preloadToken !== token || i >= order.length) return;
    const img = capImage(e, order[i++]);
    if (img.complete) { pump(); return; }
    img.addEventListener('load', pump, { once: true });
    img.addEventListener('error', pump, { once: true });
  };
  // the first few start at once so the caption under the playhead appears immediately
  setTimeout(() => { for (let n = 0; n < 4; n++) pump(); }, e.images.size ? 220 : 0);
}

function showCaption(e, t) {
  let key = '';
  if (e.cap.enabled) {
    const keep = e.derived.keep;
    const k = rangeIndex(keep, t);
    if (k >= 0 && t < keep[k][1] + 0.001) {
      const out = srcToOut(e, t);
      const cues = e.derived.cues;
      let lo = 0, hi = cues.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (cues[mid].e <= out) lo = mid + 1; else if (cues[mid].s > out) hi = mid - 1; else { key = cues[mid].k; break; }
      }
    }
  }
  if (key === e.shownKey) return;
  e.shownKey = key;
  if (!key) { e.capLayer.replaceChildren(); return; }
  e.capLayer.replaceChildren(capImage(e, key));
}

function sizeScreen(e) {
  const wrap = e.screenWrap;
  const f = e.derived.frame;
  const cs = getComputedStyle(wrap);
  const availW = wrap.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const availH = wrap.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  if (availW <= 0 || availH <= 0) return;
  const ratio = f.w / f.h;
  let w = availW, h = w / ratio;
  if (h > availH) { h = availH; w = h * ratio; }
  e.screen.style.width = Math.floor(w) + 'px';
  e.screen.style.height = Math.floor(h) + 'px';
  const cw = capWidth(e);
  if (cw !== e.capW) { e.capW = cw; e.shownKey = null; }
}

// --------------------------------------------------------------- timeline

function drawTimeline(e) {
  const c = e.canvas;
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  if (!w || !h) return;
  if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
  const g = c.getContext('2d', { willReadFrequently: true });
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  const dur = e.p.media.duration || 1;
  const keep = e.derived.keep;
  const x = (t) => (t / dur) * w;
  const css = getComputedStyle(document.documentElement);
  const ink = css.getPropertyValue('--ink').trim() || '#303039';
  const mag = css.getPropertyValue('--mag').trim() || '#B93372';

  // cut regions: soft pink with a diagonal hatch
  g.fillStyle = '#F4B8CA55';
  g.fillRect(0, 0, w, h);
  g.save();
  g.beginPath(); g.rect(0, 0, w, h); g.clip();
  g.strokeStyle = '#B9337233'; g.lineWidth = 1;
  for (let i = -h; i < w; i += 7) { g.beginPath(); g.moveTo(i, h); g.lineTo(i + h, 0); g.stroke(); }
  g.restore();
  // kept regions
  g.fillStyle = '#ffffff';
  for (const [a, b] of keep) g.fillRect(x(a), 0, Math.max(1, x(b) - x(a)), h);

  // waveform
  const peaks = e.peaks;
  const mid = h / 2;
  if (peaks.length) {
    const bars = Math.floor(w / 3);
    for (let i = 0; i < bars; i++) {
      const t = ((i + 0.5) / bars) * dur;
      const a0 = Math.floor((i / bars) * peaks.length);
      const a1 = Math.max(a0 + 1, Math.floor(((i + 1) / bars) * peaks.length));
      let v = 0;
      for (let j = a0; j < a1 && j < peaks.length; j++) if (peaks[j] > v) v = peaks[j];
      const k = rangeIndex(keep, t);
      const kept = k >= 0 && t < keep[k][1];
      const bh = Math.max(2, (v / 100) * (h - 12));
      g.fillStyle = kept ? ink : '#b9337266';
      g.fillRect(i * 3, mid - bh / 2, 2, bh);
    }
  }
  e.tlPaint = g.getImageData(0, 0, c.width, c.height);
  e.tlMag = mag;
  drawPlayhead(e, e.video.currentTime || 0);
}

function drawPlayhead(e, t) {
  const c = e.canvas;
  if (!e.tlPaint || !c.width) return;
  const g = c.getContext('2d', { willReadFrequently: true });
  const dpr = window.devicePixelRatio || 1;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.putImageData(e.tlPaint, 0, 0);
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = c.clientWidth, h = c.clientHeight;
  const px = Math.max(1, Math.min(w - 1, (t / (e.p.media.duration || 1)) * w));
  g.fillStyle = e.tlMag;
  g.fillRect(px - 1, 0, 2, h);
  g.beginPath(); g.arc(px, 5, 5, 0, Math.PI * 2); g.fill();
}

function bindTimeline(e) {
  const c = e.canvas;
  let dragging = false;
  const at = (ev) => {
    const r = c.getBoundingClientRect();
    return Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * (e.p.media.duration || 0);
  };
  c.addEventListener('pointerdown', (ev) => { dragging = true; c.setPointerCapture(ev.pointerId); seek(e, at(ev)); });
  c.addEventListener('pointermove', (ev) => { if (dragging) seek(e, at(ev)); });
  const stop = () => { dragging = false; };
  c.addEventListener('pointerup', stop);
  c.addEventListener('pointercancel', stop);
}

// -------------------------------------------------------------- selection

function selectedWords(e) {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount || sel.isCollapsed) return [];
  const r = sel.getRangeAt(0);
  if (!e.transcript.contains(r.commonAncestorContainer)) return [];
  const out = [];
  const wr = document.createRange();
  for (let i = 0; i < e.n; i++) {
    wr.selectNodeContents(e.spans[i]);
    if (r.compareBoundaryPoints(Range.START_TO_END, wr) <= 0) continue;   // selection ends before this word
    if (r.compareBoundaryPoints(Range.END_TO_START, wr) >= 0) { if (out.length) break; continue; } // starts after it
    out.push(i);
  }
  return out;
}

function bindSelection(e) {
  const update = () => {
    if (!e.alive) return;
    const idx = selectedWords(e);
    if (!idx.length) { e.selbar.hidden = true; return; }
    const allDel = idx.every((i) => e.del[i]);
    const anyDel = idx.some((i) => e.del[i]);
    const secs = idx.reduce((a, i) => a + (e.words[i].e - e.words[i].s), 0);
    const clear = () => { window.getSelection().removeAllRanges(); e.selbar.hidden = true; };
    const btns = [];
    if (!allDel) btns.push(el('button', { class: 'btn btn-dark btn-sm', onclick: () => { setDeleted(e, idx, true); clear(); } }, 'מחיקה', el('i', { class: 'ar' }, icon('cut'))));
    if (anyDel) btns.push(el('button', { class: 'btn btn-ghost btn-sm plain', onclick: () => { setDeleted(e, idx, false); clear(); } }, 'שחזור'));
    if (idx.length === 1) btns.push(el('button', { class: 'btn btn-ghost btn-sm plain', onclick: () => { clear(); editWord(e, idx[0]); } }, 'תיקון'));
    btns.push(el('button', { class: 'ib sm', 'aria-label': 'ניגון מכאן', title: 'ניגון מכאן',
      onclick: () => { clear(); seek(e, e.words[idx[0]].s); if (e.video.paused && !e.del[idx[0]]) e.video.play().catch(() => {}); } }, icon('play')));
    e.selbar.replaceChildren(
      el('span', { class: 'sel-info', text: `${idx.length === 1 ? 'מילה אחת' : idx.length + ' מילים'} · ${secs.toFixed(1)} שנ׳` }),
      ...btns);
    e.selbar.hidden = false;
  };
  const onSel = debounce(update, 90);
  document.addEventListener('selectionchange', onSel);
  e.cleanup.push(() => document.removeEventListener('selectionchange', onSel));
  e.selbar.addEventListener('mousedown', (ev) => ev.preventDefault()); // keep the selection alive
  e.selectedWords = () => selectedWords(e);

  e.transcript.addEventListener('click', (ev) => {
    const span = ev.target.closest && ev.target.closest('.w');
    if (!span || !window.getSelection().isCollapsed) return;
    const i = +span.dataset.i;
    e.cursor = i;
    seek(e, e.words[i].s + 0.001);
  });
  e.transcript.addEventListener('dblclick', (ev) => {
    const span = ev.target.closest && ev.target.closest('.w');
    if (span && ev.altKey) editWord(e, +span.dataset.i);
  });
}

function editWord(e, i) {
  const w = e.words[i];
  const input = el('input', { type: 'text', value: e.texts[i], dir: 'auto', maxlength: 80 });
  const apply = () => {
    const val = input.value.replace(/\s+/g, ' ').trim();
    if (val !== e.texts[i]) { pushHist(e); e.texts[i] = val; refreshWords(e, [i]); e.save(); }
    m.close();
  };
  input.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); apply(); } });
  const orig = w.o || w.t;
  const m = modal({
    title: 'תיקון מילה',
    body: el('div', {},
      el('p', { class: 'muted', text: 'התיקון משנה את הטקסט בתמלול ובכתוביות. הקול נשאר כמו שהוא.' }),
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'המילה' }), input),
      el('div', { class: 'row end gap' },
        orig !== e.texts[i] ? el('button', { class: 'btn btn-ghost btn-sm plain', text: `חזרה ל״${orig}״`, onclick: () => { input.value = orig; apply(); } }) : null,
        el('button', { class: 'btn btn-dark btn-sm plain', text: 'שמירה', onclick: apply }))),
  });
  setTimeout(() => { input.focus(); input.select(); }, 30);
}

function bindKeys(e) {
  const onKey = (ev) => {
    if (!e.alive) return;
    const tag = (ev.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || ev.target.isContentEditable) return;
    if (document.querySelector('.modal-wrap')) return;
    const mod = ev.ctrlKey || ev.metaKey;
    if (ev.code === 'Space' && !mod) { ev.preventDefault(); togglePlay(e); return; }
    if (mod && ev.key.toLowerCase() === 'z') { ev.preventDefault(); if (ev.shiftKey) redo(e); else undo(e); return; }
    if (mod && ev.key.toLowerCase() === 'y') { ev.preventDefault(); redo(e); return; }
    if (ev.key === 'Delete' || ev.key === 'Backspace') {
      const idx = selectedWords(e);
      if (idx.length) {
        ev.preventDefault();
        setDeleted(e, idx, !idx.every((i) => e.del[i]));
        window.getSelection().removeAllRanges();
      } else if (e.cursor >= 0) {
        ev.preventDefault();
        setDeleted(e, [e.cursor], !e.del[e.cursor]);
      }
    }
  };
  document.addEventListener('keydown', onKey);
  e.cleanup.push(() => document.removeEventListener('keydown', onKey));
}
