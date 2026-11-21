// The library panel: media and stock, transcript, captions, titles, narration, sound, AI and export.
import { api, uploadFile, followJob } from './api.js';
import { el, icon, fmt, fmtSize, dims, toast, confirmBox, segmented, toggle, slider, progressBar, debounce, modal } from './ui.js';
import { App, openSettings } from './app.js';
import { S, on, op, track, refresh, findItem, info, media, mainTrack, select, tlAt, srcAt, mainAt, covers } from './store.js';

const TABS = [
  { id: 'media', label: 'מדיה', ic: 'film' }, { id: 'transcript', label: 'תמלול', ic: 'text' },
  { id: 'captions', label: 'כתוביות', ic: 'cc' }, { id: 'text', label: 'טקסט', ic: 'type' },
  { id: 'voice', label: 'קריינות', ic: 'mic' }, { id: 'sound', label: 'סאונד', ic: 'music' },
  { id: 'ai', label: 'AI', ic: 'spark' }, { id: 'export', label: 'ייצוא', ic: 'download' },
];
const RATIO_LABELS = { source: 'מקורי', '9:16': '9:16', '16:9': '16:9', '1:1': '1:1', '4:5': '4:5' };
const LANGS = [['en', 'אנגלית'], ['he', 'עברית'], ['ar', 'ערבית'], ['ru', 'רוסית'], ['fr', 'צרפתית'], ['es', 'ספרדית']];

const head = (eyebrow, title, extra) => el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow', text: eyebrow }), el('h3', { text: title }), extra || null);
const sec = (label, ...kids) => el('div', { class: 'sec' }, label ? el('span', { class: 'lbl', text: label }) : null, ...kids);

// A job started by an operation: shows progress next to `anchor`, then reloads the project.
async function runJob(anchor, promise, onDone, labelDone) {
  const bar = progressBar();
  const note = el('span', { class: 'muted small', text: 'מתחיל…' });
  const box = el('div', { class: 'jobbox' }, note, bar);
  if (anchor.tagName === 'BUTTON') anchor.disabled = true;
  anchor.after(box);
  try {
    const r = await promise;
    if (!r || !r.job) return;
    let fake = 0.05;
    const job = await track(r.job, (j) => { fake = Math.max(j.progress, Math.min(0.92, fake + 0.01)); bar.set(fake); if (j.message) note.textContent = j.message; });
    if (job && job.status === 'done') { if (labelDone) toast(labelDone); onDone && onDone(job.result); }
  } finally {
    box.remove();
    if (anchor.tagName === 'BUTTON') anchor.disabled = false;
  }
}

// ------------------------------------------------------------------ media

function mediaPanel() {
  const input = el('input', { type: 'file', accept: 'video/*,audio/*,image/*', multiple: true, hidden: true,
    onchange: () => { for (const f of input.files) uploadMedia(f, false); input.value = ''; } });
  const drop = el('label', { class: 'dropmini', tabindex: '0' }, input, icon('upload'), el('b', { text: 'העלאת קבצים' }),
    el('small', { text: 'וידאו, אודיו או תמונות. אפשר גם לגרור לכאן.' }));
  for (const ev of ['dragenter', 'dragover']) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); });
  for (const ev of ['dragleave', 'drop']) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); });
  drop.addEventListener('drop', (e) => { for (const f of e.dataTransfer.files) uploadMedia(f, false); });

  const src = el('input', { type: 'text', dir: 'ltr', placeholder: 'נתיב קובץ במחשב, או קישור ישיר' });
  const imp = el('button', { class: 'btn btn-ghost btn-sm plain', type: 'button', text: 'ייבוא', onclick: () => {
    if (!src.value.trim()) { src.focus(); return; }
    runJob(imp, op('import_media', { source: src.value.trim() }), () => { src.value = ''; });
  } });
  const importRow = App.state.local ? el('div', { class: 'row gap nowrap' }, src, imp) : null;
  const list = el('div', { class: 'medialist' });

  function card(m) {
    const thumb = el('div', { class: 'mthumb k-' + m.kind });
    if (m.kind !== 'audio' && m.status === 'ready') {
      const img = el('img', { src: `/api/projects/${S.pid}/media/${m.id}/thumb.jpg`, alt: '', loading: 'lazy', draggable: 'false' });
      img.onerror = () => img.remove();
      thumb.append(img);
    } else thumb.append(icon(m.kind === 'audio' ? 'music' : 'film'));
    const meta = m.status === 'preparing' ? 'בהכנה…' : m.status === 'error' ? (m.error || 'שגיאה')
      : [m.kind === 'image' ? 'תמונה' : fmt(m.duration), m.width ? dims(m.width, m.height) : '',
        m.transcript.status === 'running' ? 'מתמלל…' : m.word_count ? 'מתומלל' : ''].filter(Boolean).join(' · ');
    const usable = m.status === 'ready';
    const c = el('div', { class: 'mcard' + (m.status === 'error' ? ' err' : ''), draggable: usable ? 'true' : 'false' },
      thumb,
      el('div', { class: 'mmeta' }, el('b', { text: m.name, title: m.name }), el('small', { text: meta })),
      usable ? el('button', { class: 'ib sm', title: 'הוספה לטיימליין בסמן', 'aria-label': 'הוספה לטיימליין',
        onclick: async () => { const r = await op('add_clip', { media: m.id, at: S.time }); if (r && r.item) select(r.item); } }, icon('plus')) : null,
      usable && (m.has_audio || m.kind === 'audio') && m.transcript.status !== 'running' && !m.word_count
        ? el('button', { class: 'ib sm', title: 'תמלול', 'aria-label': 'תמלול הקובץ', onclick: (e) => runJob(e.currentTarget.closest('.mcard'), op('transcribe', { media: m.id })) }, icon('mic')) : null,
      el('button', { class: 'ib sm', title: 'הסרה מהפרויקט', 'aria-label': 'הסרת הקובץ', onclick: async () => {
        if (await confirmBox('להסיר את הקובץ?', `״${m.name}״ יוסר מהפרויקט, כולל כל מקום שבו הוא מופיע בטיימליין.`, 'הסרה')) op('remove_media', { media: m.id });
      } }, icon('trash')));
    c.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/studio-media', m.id); e.dataTransfer.effectAllowed = 'copy'; });
    return c;
  }

  // ----- stock
  let kind = 'video';
  const q = el('input', { type: 'search', placeholder: 'מה לחפש? עדיף באנגלית', dir: 'auto' });
  const results = el('div', { class: 'stockgrid' });
  const ideas = el('div', { class: 'chips' });
  const search = async () => {
    if (!q.value.trim()) { q.focus(); return; }
    results.replaceChildren(el('span', { class: 'spin dark' }));
    try {
      const r = await api(`/api/projects/${S.pid}/ops`, { method: 'POST', body: { op: 'search_stock', args: { kind, query: q.value.trim(), portrait: S.derived.frame.h >= S.derived.frame.w } } });
      const res = r.result;
      results.replaceChildren();
      for (const n of res.notes) results.append(el('p', { class: 'note' }, n, ' ', el('button', { class: 'tlink', text: 'להגדרות', onclick: () => openSettings('stock') })));
      if (!res.results.length && !res.notes.length) results.append(el('p', { class: 'muted small', text: 'לא נמצאו תוצאות. מנסים מילה אחרת.' }));
      for (const x of res.results) results.append(stockCard(x));
    } catch (e) { results.replaceChildren(el('p', { class: 'muted small', text: e.message })); }
  };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
  const kinds = segmented(App.state.stock_kinds.map((k) => ({ value: k.id, label: k.label })), kind, (v) => {
    kind = v;
    ideas.replaceChildren(...(v === 'overlay' ? App.state.overlay_ideas.map((t) => el('button', { class: 'chip', type: 'button', text: t, onclick: () => { q.value = t; search(); } })) : []));
    results.replaceChildren();
  }, 'סוג חומר');

  function stockCard(x) {
    const view = el('div', { class: 'sthumb' });
    if (x.kind === 'music') {
      view.append(icon('music'));
      view.append(el('audio', { src: x.preview, controls: true, preload: 'none' }));
    } else {
      view.append(el('img', { src: x.thumb, alt: '', loading: 'lazy' }));
      if (x.kind !== 'image' && x.preview) {
        view.addEventListener('mouseenter', () => { if (!view.querySelector('video')) view.append(el('video', { src: x.preview, muted: true, loop: true, autoplay: true, playsinline: true })); });
        view.addEventListener('mouseleave', () => { const v = view.querySelector('video'); if (v) v.remove(); });
      }
    }
    const add = el('button', { class: 'ib sm', title: 'הוספה בסמן', 'aria-label': 'הוספה לטיימליין', onclick: () => runJob(add, op('add_stock', { token: x.token, at: S.time }), (r) => { if (r && r.item) select(r.item); }, 'נוסף לטיימליין.') }, icon('plus'));
    return el('div', { class: 'scard' + (x.kind === 'music' ? ' wide' : '') }, view,
      el('div', { class: 'smeta' }, el('b', { text: x.title || x.provider, title: x.title }), el('small', { text: [x.author, x.provider, x.duration ? fmt(x.duration) : ''].filter(Boolean).join(' · ') })), add);
  }

  const node = el('div', { class: 'panel', dataset: { panel: 'media' } },
    head('MEDIA', 'מדיה'),
    el('div', { class: 'panel-body' },
      sec(null, drop, importRow),
      sec('הקבצים בפרויקט', list),
      sec('מאגר חינמי', kinds, el('div', { class: 'row gap nowrap' }, q, el('button', { class: 'ib', 'aria-label': 'חיפוש', onclick: search }, icon('search'))), ideas, results)));
  const update = () => {
    const items = Object.values(S.doc.media).filter((m) => !['sfx', 'detached'].includes(m.origin));
    list.replaceChildren(...(items.length ? items.map(card) : [el('p', { class: 'muted small', text: 'עדיין אין קבצים. מעלים למעלה, או מחפשים במאגר.' })]));
  };
  return { node, update };
}

export async function uploadMedia(file, add, at) {
  const q = `?name=${encodeURIComponent(file.name)}&add=${add ? 1 : 0}${at != null ? `&at=${at}` : ''}`;
  const t = toast(`מעלה את ${file.name}…`, { ttl: 600000 });
  try {
    const r = await uploadFile(`/api/projects/${S.pid}/media${q}`, file, (f) => { t.firstChild.textContent = `מעלה את ${file.name}… ${Math.round(f * 100)}%`; });
    t.firstChild.textContent = `מכין את ${file.name}…`;
    await refresh();
    await track(r.job.id, (j) => { if (j.message) t.firstChild.textContent = `${j.message} ${Math.round(j.progress * 100)}%`; });
  } catch (e) {
    toast(e.message, { error: true });
  } finally {
    t.remove();
  }
}

// ------------------------------------------------------------- transcript

function transcriptPanel() {
  const body = el('div', { class: 'transcript', lang: 'he' });
  const selbar = el('div', { class: 'selbar', hidden: true });
  let spans = {};       // mid -> [span]
  let sig = '';
  let cur = null;

  const sweep = async (name, label) => {
    const r = await op(name);
    if (!r) return;
    const n = r.words_cut ?? r.words_restored ?? 0;
    toast(n ? `${label}: ${n} מילים.` : 'לא נמצא מה לשנות.', n ? { action: { label: 'ביטול', run: () => op('undo') } } : {});
  };
  const tools = el('div', { class: 'toolbar' }, el('div', { class: 'chips' },
    el('button', { class: 'chip', type: 'button', onclick: () => sweep('remove_fillers', 'נחתכו מילות מילוי') }, icon('cut'), 'מילות מילוי'),
    el('button', { class: 'chip', type: 'button', onclick: () => sweep('remove_repeats', 'נחתכו חזרות') }, icon('cut'), 'חזרות'),
    el('button', { class: 'chip', type: 'button', onclick: () => sweep('restore_all_words', 'שוחזרו') }, icon('restore'), 'שחזור הכל')));

  // media that carry speech and sit on the timeline, in order of appearance
  const sources = () => {
    const out = [];
    for (const tr of [mainTrack(), ...S.doc.tracks.filter((t) => t.kind === 'audio')]) {
      for (const it of tr.items) if (!out.includes(it.media)) out.push(it.media);
    }
    return out;
  };
  const itemsOf = (mid) => {
    const out = [];
    for (const tr of S.doc.tracks) if (tr.kind !== 'text') for (const it of tr.items) if (it.media === mid && (tr.main || tr.kind === 'audio')) out.push(it);
    return out;
  };

  function build() {
    spans = {};
    const frag = document.createDocumentFragment();
    let any = false;
    for (const mid of sources()) {
      const m = media(mid);
      const words = S.words[mid];
      if (!(m.has_audio || m.kind === 'audio') || m.origin === 'sfx' || m.origin === 'stock') continue;
      any = true;
      const title = el('div', { class: 'tsrc' }, el('b', { text: m.name }),
        el('button', { class: 'tlink', text: m.word_count ? 'תמלול מחדש' : 'תמלול', onclick: () => retranscribe(m) }));
      frag.append(title);
      if (m.transcript.status === 'running') { frag.append(el('p', { class: 'muted', text: 'מתמלל את הקובץ…' })); continue; }
      if (!words || !words.length) {
        frag.append(el('p', { class: 'muted', text: m.transcript.error || 'עדיין אין תמלול לקובץ הזה.' }));
        continue;
      }
      const its = itemsOf(mid);
      const inClip = (w) => its.some((it) => w.e > it.in && w.s < it.out);
      spans[mid] = [];
      let para = null;
      words.forEach((w, i) => {
        const prev = words[i - 1];
        if (!para || w.b) {
          para = el('p', { class: 'para' }, el('span', { class: 'ts', dir: 'ltr', text: fmt(w.s) }));
          frag.append(para);
        }
        const gap = prev ? w.s - prev.e : w.s;
        if (gap >= 0.8) para.append(el('span', { class: 'gap', text: gap.toFixed(1) + ' שנ׳' }), ' ');
        const sp = el('span', { class: 'w' + (w.d ? ' del' : '') + (!inClip(w) ? ' off' : '') + (w.o ? ' edited' : '') + (w.p < 0.5 && !w.o ? ' low' : ''),
          dataset: { m: mid, i }, text: w.t || '∅' });
        spans[mid].push(sp);
        para.append(sp, ' ');
      });
    }
    if (!any) frag.append(el('p', { class: 'muted', text: 'כשיהיה בטיימליין קליפ עם דיבור, התמלול שלו יופיע כאן.' }));
    body.replaceChildren(frag);
    cur = null;
  }

  function retranscribe(m) {
    const st = App.state;
    const model = el('select', {}, ...st.models.map((x) => el('option', { value: x.id, text: x.label, selected: x.id === (m.transcript.model || st.settings.transcribe.model) })));
    const lang = el('select', {}, ...st.languages.map((x) => el('option', { value: x.id, text: x.label, selected: x.id === (m.transcript.language || st.settings.transcribe.language) })));
    const go = el('button', { class: 'btn btn-dark btn-sm', onclick: async () => {
      const r = await op('transcribe', { media: m.id, model: model.value, language: lang.value });
      if (r && r.job) { dlg.close(); refresh(); track(r.job); }
    } }, 'להתחיל', el('i', { class: 'ar' }, icon('mic')));
    const dlg = modal({ title: 'תמלול', body: el('div', {},
      m.word_count ? el('p', { class: 'muted', text: 'התמלול החדש מחליף את הנוכחי, כולל המחיקות והתיקונים שנעשו בו.' }) : null,
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'מודל' }), model),
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'שפה' }), lang),
      el('div', { class: 'row end gap' }, go)) });
  }

  function selected() {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) return null;
    const r = sel.getRangeAt(0);
    if (!body.contains(r.commonAncestorContainer)) return null;
    const wr = document.createRange();
    for (const [mid, list] of Object.entries(spans)) {
      const idx = [];
      for (let i = 0; i < list.length; i++) {
        wr.selectNodeContents(list[i]);
        if (r.compareBoundaryPoints(Range.START_TO_END, wr) <= 0) continue;
        if (r.compareBoundaryPoints(Range.END_TO_START, wr) >= 0) { if (idx.length) break; continue; }
        idx.push(i);
      }
      if (idx.length) return { mid, idx };
    }
    return null;
  }

  const seekWord = (mid, i) => {
    const w = S.words[mid][i];
    const it = itemsOf(mid).find((x) => w.s >= x.in - 0.01 && w.s < x.out) || itemsOf(mid)[0];
    if (it) S.player.seek(tlAt(it.id, w.s) + 0.001);
  };

  const onSel = debounce(() => {
    if (!S.alive || !body.isConnected) return;
    const s = selected();
    if (!s) { selbar.hidden = true; return; }
    const words = S.words[s.mid];
    const lo = s.idx[0], hi = s.idx[s.idx.length - 1];
    const allDel = s.idx.every((i) => words[i].d);
    const anyDel = s.idx.some((i) => words[i].d);
    const secs = s.idx.reduce((a, i) => a + (words[i].e - words[i].s), 0);
    const clear = () => { window.getSelection().removeAllRanges(); selbar.hidden = true; };
    const btns = [];
    if (!allDel) btns.push(el('button', { class: 'btn btn-dark btn-sm', onclick: () => { op('delete_words', { media: s.mid, from: lo, to: hi }); clear(); } }, 'מחיקה', el('i', { class: 'ar' }, icon('cut'))));
    if (anyDel) btns.push(el('button', { class: 'btn btn-ghost btn-sm plain', onclick: () => { op('restore_words', { media: s.mid, from: lo, to: hi }); clear(); } }, 'שחזור'));
    if (s.idx.length === 1) btns.push(el('button', { class: 'btn btn-ghost btn-sm plain', onclick: () => { clear(); editWord(s.mid, lo); } }, 'תיקון'));
    btns.push(el('button', { class: 'ib sm', 'aria-label': 'ניגון מכאן', title: 'ניגון מכאן', onclick: () => { clear(); seekWord(s.mid, lo); S.player.play(); } }, icon('play')));
    selbar.replaceChildren(el('span', { class: 'sel-info', text: `${s.idx.length === 1 ? 'מילה אחת' : s.idx.length + ' מילים'} · ${secs.toFixed(1)} שנ׳` }), ...btns);
    selbar.hidden = false;
  }, 90);
  document.addEventListener('selectionchange', onSel);
  selbar.addEventListener('mousedown', (e) => e.preventDefault());

  function editWord(mid, i) {
    const w = S.words[mid][i];
    const input = el('input', { type: 'text', value: w.t, dir: 'auto', maxlength: 80 });
    const apply = (val) => { op('edit_word', { media: mid, index: i, text: val }); dlg.close(); };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); apply(input.value); } });
    const dlg = modal({ title: 'תיקון מילה', body: el('div', {},
      el('p', { class: 'muted', text: 'התיקון משנה את הטקסט בתמלול ובכתוביות. הקול נשאר כמו שהוא.' }),
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'המילה' }), input),
      el('div', { class: 'row end gap' },
        w.o ? el('button', { class: 'btn btn-ghost btn-sm plain', text: `חזרה ל״${w.o}״`, onclick: () => apply(w.o) }) : null,
        el('button', { class: 'btn btn-dark btn-sm plain', text: 'שמירה', onclick: () => apply(input.value) }))) });
    setTimeout(() => { input.focus(); input.select(); }, 30);
  }

  body.addEventListener('click', (e) => {
    const sp = e.target.closest && e.target.closest('.w');
    if (!sp || !window.getSelection().isCollapsed) return;
    seekWord(sp.dataset.m, +sp.dataset.i);
  });

  function mark() {
    if (!body.isConnected || !S.derived) return;
    let hit = null;
    const id = mainAt(S.time);
    const found = id && findItem(id);
    if (found && spans[found.item.media]) {
      const mid = found.item.media;
      const src = srcAt(id, S.time);
      const words = S.words[mid];
      let lo = 0, hi = words.length - 1, k = -1;
      while (lo <= hi) { const m = (lo + hi) >> 1; if (words[m].s <= src + 0.02) { k = m; lo = m + 1; } else hi = m - 1; }
      if (k >= 0 && src <= words[k].e + 0.25) hit = spans[mid][k];
    }
    if (hit === cur) return;
    if (cur) cur.classList.remove('cur');
    cur = hit;
    if (!hit) return;
    hit.classList.add('cur');
    if (S.playing && window.getSelection().isCollapsed) {
      const box = body.getBoundingClientRect();
      const r = hit.getBoundingClientRect();
      if (r.top < box.top + 30 || r.bottom > box.bottom - 50) body.scrollTo({ top: body.scrollTop + (r.top - box.top) - box.height * 0.35, behavior: 'smooth' });
    }
  }
  on('time', mark);

  const node = el('div', { class: 'panel', dataset: { panel: 'transcript' } }, head('TRANSCRIPT', 'תמלול'), tools, body, selbar);
  const update = () => {
    // rebuild only when the words or the clips that use them changed
    const next = JSON.stringify([sources().map((mid) => [mid, media(mid).transcript.status, (S.words[mid] || []).map((w) => (w.d ? 1 : 0) + w.t).join('|')]),
      S.doc.tracks.map((t) => t.items.map((i) => [i.media, i.in, i.out]))]);
    if (next !== sig) { sig = next; const top = body.scrollTop; build(); body.scrollTop = top; }
    mark();
  };
  return { node, update, destroy: () => document.removeEventListener('selectionchange', onSel) };
}

// --------------------------------------------------------------- captions

function captionsPanel() {
  const cap = () => S.doc.captions;
  const set = (args, coalesce) => op('set_captions', args, { coalesce });
  const enabled = toggle(false, (v) => set({ enabled: v }), 'כתוביות בסרטון');
  const grid = el('div', { class: 'presets' });
  const cards = new Map();
  for (const p of App.state.presets) {
    const img = el('img', { alt: '', draggable: 'false' });
    const card = el('button', { type: 'button', class: 'preset', onclick: () => set({ preset: p.id }) }, el('span', { class: 'preset-view' }, img), el('span', { class: 'preset-name', text: p.name }));
    cards.set(p.id, card);
    grid.append(card);
    api('/api/preview-style', { method: 'POST', body: { style: p.style, w: 420, texts: ['ככה', 'זה', 'נראה'], active: 1 } })
      .then((r) => r.blob()).then((b) => { img.src = URL.createObjectURL(b); }).catch(() => {});
  }
  const controls = el('div', { class: 'controls' });
  const mode = segmented([{ value: 'original', label: 'מקור' }, { value: 'translated', label: 'תרגום' }, { value: 'both', label: 'שניהם' }], 'original', (v) => {
    const have = Object.values(S.doc.media).some((m) => (m.languages || []).includes(lang.value));
    if (v !== 'original' && !have) { toast('קודם מתרגמים: בוחרים שפה ולוחצים ״תרגום״.'); mode.setValue(cap().mode); return; }
    set({ mode: v, language: lang.value });
  }, 'שפת הכתוביות');
  const lang = el('select', {}, ...LANGS.map(([id, label]) => el('option', { value: id, text: label })));
  const trBtn = el('button', { class: 'btn btn-dark btn-sm', type: 'button', onclick: () => {
    if (!App.state.ai.ready) { toast('לתרגום צריך מודל AI.', { action: { label: 'חיבור', run: () => openSettings('ai') } }); return; }
    runJob(trBtn, op('translate_captions', { language: lang.value, mode: cap().mode === 'both' ? 'both' : 'translated' }), null, 'הכתוביות תורגמו.');
  } }, 'תרגום', el('i', { class: 'ar' }, icon('spark')));
  let styleSig = '';

  function drawControls() {
    const s = cap().style;
    const change = (patch) => set({ style: patch }, 'capstyle');
    const color = (label, key) => {
      const input = el('input', { type: 'color', value: s[key], 'aria-label': label, onchange: () => change({ [key]: input.value.toUpperCase() }) });
      return el('label', { class: 'color' }, input, el('span', { text: label }));
    };
    const font = el('select', { onchange: () => change({ font: font.value }) },
      ...App.state.fonts.map((f) => el('option', { value: f.id, text: f.label + (f.hebrew ? '' : ' (לטיני בלבד)'), selected: f.id === s.font })));
    controls.replaceChildren(
      el('label', { class: 'field' }, el('span', { class: 'lbl', text: 'פונט' }), font),
      slider({ label: 'גודל', min: 0.03, max: 0.14, step: 0.002, value: s.size, format: (v) => Math.round(v * 1000) / 10 + '%', onChange: (v) => change({ size: v }) }),
      slider({ label: 'מיקום בגובה', min: 0.08, max: 0.92, step: 0.01, value: s.y, format: (v) => Math.round(v * 100) + '%', onChange: (v) => change({ y: v }) }),
      slider({ label: 'מילים בכל כתובית', min: 1, max: 7, step: 1, value: s.max_words, onChange: (v) => change({ max_words: v }) }),
      el('div', { class: 'field' }, el('span', { class: 'lbl', text: 'הדגשת המילה הנאמרת' }),
        segmented([{ value: 'none', label: 'בלי' }, { value: 'color', label: 'צבע' }, { value: 'box', label: 'תיבה' }], s.highlight, (v) => change({ highlight: v }), 'הדגשת מילה')),
      el('div', { class: 'field' }, el('span', { class: 'lbl', text: 'רקע' }),
        segmented([{ value: 'none', label: 'בלי' }, { value: 'pill', label: 'פיל' }, { value: 'block', label: 'בלוק' }], s.bg, (v) => change({ bg: v }), 'רקע')),
      el('div', { class: 'colors' }, color('טקסט', 'color'), color('מילה מודגשת', 'active_color'), color('תיבת הדגשה', 'active_bg'), color('רקע', 'bg_color'), color('קו מתאר', 'stroke_color')),
      slider({ label: 'שקיפות הרקע', min: 0, max: 1, step: 0.05, value: s.bg_opacity, format: (v) => Math.round(v * 100) + '%', onChange: (v) => change({ bg_opacity: v }) }),
      slider({ label: 'קו מתאר', min: 0, max: 0.2, step: 0.01, value: s.stroke, format: (v) => Math.round(v * 100) + '%', onChange: (v) => change({ stroke: v }) }),
      slider({ label: 'צל', min: 0, max: 1, step: 0.05, value: s.shadow, format: (v) => Math.round(v * 100) + '%', onChange: (v) => change({ shadow: v }) }),
      toggle(s.strip_punct, (v) => change({ strip_punct: v }), 'בלי סימני פיסוק'));
  }

  const node = el('div', { class: 'panel', dataset: { panel: 'captions' } },
    head('CAPTIONS', 'כתוביות', enabled),
    el('div', { class: 'panel-body' },
      sec('סגנון', grid),
      sec('שפה', mode, el('div', { class: 'row gap nowrap' }, lang, trBtn),
        el('small', { class: 'muted', text: 'דיבור בעברית עם כתוביות באנגלית, להפך, או שתי השפות יחד.' })),
      el('details', { class: 'sec fold' }, el('summary', { text: 'התאמה אישית' }), controls)));
  const update = () => {
    const c = cap();
    enabled.input.checked = c.enabled;
    node.classList.toggle('off', !c.enabled);
    for (const [id, card] of cards) card.classList.toggle('on', id === c.style.preset);
    mode.setValue(c.mode);
    lang.value = c.lang;
    const next = JSON.stringify(c.style);
    if (next !== styleSig && !controls.contains(document.activeElement)) { styleSig = next; drawControls(); }
  };
  return { node, update };
}

// ------------------------------------------------------------------- text

function textPanel() {
  const grid = el('div', { class: 'presets' });
  for (const p of App.state.title_presets) {
    const img = el('img', { alt: '', draggable: 'false' });
    grid.append(el('button', { type: 'button', class: 'preset', onclick: async () => {
      const r = await op('add_text', { text: 'כותרת חדשה', at: S.time, duration: 3, preset: p.id });
      if (r && r.item) { select(r.item); toast('הכותרת נוספה. את הטקסט משנים בצד שמאל.'); }
    } }, el('span', { class: 'preset-view' }, img), el('span', { class: 'preset-name', text: p.name })));
    api('/api/preview-style', { method: 'POST', body: { style: p.style, w: 420, texts: ['כותרת', 'לדוגמה'], active: -1 } })
      .then((r) => r.blob()).then((b) => { img.src = URL.createObjectURL(b); }).catch(() => {});
  }
  const node = el('div', { class: 'panel', dataset: { panel: 'text' } }, head('TITLES', 'טקסט'),
    el('div', { class: 'panel-body' }, sec('בוחרים סגנון, והכותרת נוספת בסמן', grid),
      el('p', { class: 'muted small', text: 'את המיקום והמשך משנים בגרירה בטיימליין, ואת הטקסט והעיצוב בפאנל המאפיינים.' })));
  return { node, update: () => {} };
}

// ------------------------------------------------------------------ voice

function voicePanel() {
  const body = el('div', { class: 'panel-body' });
  let loaded = '';
  let voices = [];

  async function draw() {
    const v = App.state.voice;
    body.replaceChildren();
    if (!v.ready) {
      body.append(el('div', { class: 'card soft' },
        el('h4', { text: 'קריינות בקול שבוחרים, או בקול שלך' }),
        el('p', { class: 'muted', text: 'כותבים טקסט ומקבלים קריינות על הטיימליין. אפשר גם לשבט את הקול שלך מקטע דיבור של 10 עד 30 שניות. צריך מפתח API של Cartesia או ElevenLabs.' }),
        el('button', { class: 'btn btn-dark btn-sm', onclick: () => openSettings('voice') }, 'חיבור שירות קול', el('i', { class: 'ar' }, icon('mic')))));
      return;
    }
    const lang = el('select', { onchange: () => load(true) }, el('option', { value: 'he', text: 'עברית' }), el('option', { value: 'en', text: 'אנגלית' }));
    const sel = el('select', {}, el('option', { value: '', text: 'טוען קולות…' }));
    const load = async (force) => {
      if (!force && loaded === v.provider + lang.value && voices.length) { fill(); return; }
      try {
        const r = await api('/api/voices?language=' + lang.value);
        voices = r.voices;
        loaded = v.provider + lang.value;
        fill();
      } catch (e) { sel.replaceChildren(el('option', { value: '', text: e.message })); }
    };
    const fill = () => {
      sel.replaceChildren(...voices.map((x) => el('option', { value: x.id, text: (x.mine ? '★ ' : '') + x.name, selected: x.id === v.voice })));
      if (!voices.length) sel.append(el('option', { value: '', text: 'לא נמצאו קולות בשפה הזו' }));
    };
    const text = el('textarea', { rows: 5, placeholder: 'הטקסט לקריינות', dir: 'auto' });
    const go = el('button', { class: 'btn btn-cta btn-sm', onclick: () => {
      if (!text.value.trim()) { text.focus(); return; }
      runJob(go, op('add_narration', { text: text.value, at: S.time, voice: sel.value || undefined, language: lang.value }), (r) => { if (r && r.item) select(r.item); }, 'הקריינות נוספה בסמן.');
    } }, 'הקלטה והוספה בסמן', el('i', { class: 'ar' }, icon('mic')));

    const name = el('input', { type: 'text', placeholder: 'שם לקול, למשל: הקול שלי', dir: 'auto' });
    const clone = el('button', { class: 'btn btn-dark btn-sm', onclick: () => {
      let a = S.range.a, b = S.range.b;
      let id = null;
      if (a != null && b != null) id = mainAt((a + b) / 2);
      else if (S.sel && findItem(S.sel).track.kind !== 'text') { id = S.sel; const inf = info(id); a = inf.start; b = Math.min(inf.start + inf.dur, inf.start + 60); }
      if (!id) { toast('מסמנים על הטיימליין טווח של 10 עד 30 שניות דיבור (I ו-O), או בוחרים קליפ.'); return; }
      const it = findItem(id).item;
      runJob(clone, op('clone_voice', { media: it.media, from: srcAt(id, Math.min(a, b)), to: srcAt(id, Math.max(a, b)), name: name.value || 'הקול שלי', language: lang.value }),
        async () => { await import('./app.js').then((m) => m.refreshState()); loaded = ''; draw(); }, 'הקול שובט ונבחר לקריינות.');
    } }, 'שיבוט מהטווח המסומן', el('i', { class: 'ar' }, icon('spark')));
    const mine = el('div', { class: 'kflist' }, ...v.cloned.map((c) => el('div', { class: 'kfrow' }, el('span', { text: '★ ' + c.name }),
      App.state.local ? el('button', { class: 'ib sm', 'aria-label': 'מחיקת הקול', onclick: async () => {
        if (!(await confirmBox('למחוק את הקול?', `הקול ״${c.name}״ יימחק גם משירות הקול.`, 'מחיקה'))) return;
        await api('/api/voices/' + encodeURIComponent(c.id), { method: 'DELETE' });
        await import('./app.js').then((m) => m.refreshState()); loaded = ''; draw();
      } }, icon('trash')) : null)));
    body.append(
      el('p', { class: 'ai-model muted small' }, 'מחובר: ', el('b', { text: v.label }), ' ', el('button', { class: 'tlink', text: 'החלפה', onclick: () => openSettings('voice') })),
      sec('קריינות מטקסט', el('div', { class: 'row gap nowrap' }, sel, lang), text, go),
      sec('הקול שלך', el('p', { class: 'muted small', text: 'מסמנים בטיימליין קטע דיבור נקי של 10 עד 30 שניות (מקש I בתחילתו, O בסופו), נותנים שם ולוחצים. משבטים רק קול שלך, או קול שקיבלת רשות להשתמש בו.' }), name, clone, mine));
    load(false);
  }
  const node = el('div', { class: 'panel', dataset: { panel: 'voice' } }, head('VOICE', 'קריינות'), body);
  draw();
  const again = () => draw();
  document.addEventListener('studio:settings', again);
  return { node, update: () => {}, destroy: () => document.removeEventListener('studio:settings', again) };
}

// ------------------------------------------------------------------ sound

function soundPanel() {
  const player = new Audio();
  const groups = {};
  for (const s of App.state.sfx) (groups[s.group] = groups[s.group] || []).push(s);
  const body = el('div', { class: 'panel-body' });
  for (const [g, list] of Object.entries(groups)) {
    body.append(sec(g, el('div', { class: 'sfxgrid' }, ...list.map((s) => el('div', { class: 'sfx' },
      el('button', { class: 'ib sm', 'aria-label': 'השמעה', title: 'השמעה', onclick: () => { player.src = `/api/sfx/${s.id}.wav`; player.play().catch(() => {}); } }, icon('play')),
      el('span', { text: s.name }),
      el('button', { class: 'ib sm', 'aria-label': 'הוספה בסמן', title: 'הוספה בסמן', onclick: async () => { const r = await op('add_sound_effect', { name: s.id, at: S.time }); if (r && r.item) select(r.item); } }, icon('plus')))))));
  }
  const q = el('input', { type: 'search', placeholder: 'מוזיקה: upbeat, calm piano, lofi…', dir: 'ltr' });
  const results = el('div', { class: 'stockgrid' });
  const search = async () => {
    if (!q.value.trim()) { q.focus(); return; }
    results.replaceChildren(el('span', { class: 'spin dark' }));
    try {
      const r = await api(`/api/projects/${S.pid}/ops`, { method: 'POST', body: { op: 'search_stock', args: { kind: 'music', query: q.value.trim() } } });
      results.replaceChildren();
      if (!r.result.results.length) results.append(el('p', { class: 'muted small', text: 'לא נמצאו תוצאות.' }));
      for (const x of r.result.results) {
        const add = el('button', { class: 'ib sm', title: 'הוספה בסמן', 'aria-label': 'הוספה לטיימליין', onclick: () => runJob(add, op('add_stock', { token: x.token, at: S.time }), null, 'המוזיקה נוספה.') }, icon('plus'));
        results.append(el('div', { class: 'scard wide' }, el('div', { class: 'sthumb' }, el('audio', { src: x.preview, controls: true, preload: 'none' })),
          el('div', { class: 'smeta' }, el('b', { text: x.title || 'ללא שם', title: x.title }), el('small', { text: [x.author, x.license, x.duration ? fmt(x.duration) : ''].filter(Boolean).join(' · ') })), add));
      }
    } catch (e) { results.replaceChildren(el('p', { class: 'muted small', text: e.message })); }
  };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') search(); });
  body.append(sec('מוזיקה חופשית', el('div', { class: 'row gap nowrap' }, q, el('button', { class: 'ib', 'aria-label': 'חיפוש', onclick: search }, icon('search'))),
    el('small', { class: 'muted', text: 'מ-Openverse, ברישיונות Creative Commons. הקרדיטים נאספים לקובץ בלשונית הייצוא.' }), results));
  return { node: el('div', { class: 'panel', dataset: { panel: 'sound' } }, head('SOUND', 'סאונד'), body), update: () => {} };
}

// --------------------------------------------------------------------- AI

const QUICK = [
  { label: 'להדק', text: 'להוריד חזרות, התחלות שנקטעו ומשפטים שלא מוסיפים, בלי לשנות את המסר.' },
  { label: 'גרסת 30 שניות', text: 'לקצר לגרסה של עד 30 שניות עם פתיחה חזקה.' },
  { label: 'פתיחה חזקה', text: 'לחתוך את ההקדמה כך שהסרטון ייפתח במשפט הכי חזק, ולהוסיף זום פאנץ׳ על המשפט הראשון.' },
  { label: 'הכל אוטומטי', text: 'להסיר שתיקות, לחתוך מילות מילוי וחזרות, ולהפעיל כתוביות בסגנון פופ.' },
];

function aiPanel(openMcp) {
  const body = el('div', { class: 'panel-body' });
  const draw = () => {
    const ai = App.state.ai;
    body.replaceChildren();
    const agents = el('div', { class: 'card soft' },
      el('h4', { text: 'סוכן חיצוני עורך איתך' }),
      el('p', { class: 'muted', text: `Claude Code, Claude Desktop, Cursor ואחרים מתחברים לסטודיו דרך ${App.state.tools} כלי MCP, ורואים את הטיימליין משתנה בזמן אמת.` }),
      el('button', { class: 'btn btn-ghost btn-sm plain', text: 'איך מחברים', onclick: openMcp }));
    if (!ai.ready) {
      body.append(el('div', { class: 'card soft' },
        el('h4', { text: 'מבקשים במילים, והסטודיו עורך' }),
        el('p', { class: 'muted', text: 'למשל ״לקצר ל-30 שניות״ או ״לפתוח במשפט הכי חזק״. מחברים מודל מקומי וחינמי דרך Ollama, או Claude ו-GPT עם מפתח API.' }),
        el('button', { class: 'btn btn-dark btn-sm', onclick: () => openSettings('ai') }, 'חיבור מודל', el('i', { class: 'ar' }, icon('spark')))), agents);
      return;
    }
    const input = el('textarea', { rows: 3, placeholder: 'מה לעשות עם הסרטון?', dir: 'auto' });
    const result = el('div', { class: 'ai-result' });
    const go = el('button', { class: 'btn btn-cta btn-sm', onclick: () => {
      if (!input.value.trim()) { input.focus(); return; }
      runJob(go, op('assistant', { instruction: input.value }), (r) => {
        const list = el('ul', { class: 'cuts' }, ...r.steps.map((s) => el('li', {}, el('div', { class: 'step' }, el('b', { dir: 'ltr', text: s.op }), el('small', { dir: 'ltr', text: JSON.stringify(s.args) })))));
        result.replaceChildren(el('div', { class: 'card soft' },
          el('b', { text: r.steps.length ? `בוצעו ${r.steps.length} פעולות` : 'לא בוצעו שינויים' }),
          r.summary ? el('p', { class: 'muted', text: r.summary }) : null,
          r.failed ? el('p', { class: 'note', text: 'נעצר באמצע: ' + r.failed }) : null, list,
          r.steps.length ? el('button', { class: 'btn btn-ghost btn-sm plain', text: 'ביטול השינוי', onclick: () => { op('undo'); result.replaceChildren(); } }) : null));
      });
    } }, 'לערוך', el('i', { class: 'ar' }, icon('spark')));
    const textOut = el('textarea', { rows: 8, readonly: true, hidden: true, dir: 'auto' });
    const copy = el('button', { class: 'btn btn-ghost btn-sm plain', hidden: true, text: 'העתקה', onclick: async () => { try { await navigator.clipboard.writeText(textOut.value); toast('הועתק.'); } catch { textOut.select(); } } });
    const kinds = el('div', { class: 'chips' });
    for (const k of App.state.text_kinds) {
      const b = el('button', { type: 'button', class: 'chip', text: k.label, onclick: () => runJob(b, op('write_copy', { kind: k.id }), (r) => { textOut.value = r.text; textOut.hidden = false; copy.hidden = false; }) });
      kinds.append(b);
    }
    body.append(
      el('p', { class: 'ai-model muted small' }, 'מחובר: ', el('b', { text: `${ai.label} · ${ai.model}` }), ' ', el('button', { class: 'tlink', text: 'החלפה', onclick: () => openSettings('ai') })),
      sec('עריכה לפי הנחיה', el('div', { class: 'chips' }, ...QUICK.map((x) => el('button', { type: 'button', class: 'chip', text: x.label, onclick: () => { input.value = x.text; input.focus(); } }))), input, go, result),
      sec('טקסטים לפוסט', kinds, textOut, copy), agents);
  };
  draw();
  document.addEventListener('studio:settings', draw);
  return { node: el('div', { class: 'panel', dataset: { panel: 'ai' } }, head('AI EDITOR', 'עריכה עם AI'), body), update: () => {},
    destroy: () => document.removeEventListener('studio:settings', draw) };
}

// ----------------------------------------------------------------- export

function exportPanel() {
  const chosen = new Set();
  let quality = '1080';
  const ratios = el('div', { class: 'chips' });
  const qual = segmented([{ value: '720', label: '720p' }, { value: '1080', label: '1080p' }, { value: 'source', label: 'מקורי' }], quality, (v) => { quality = v; }, 'איכות');
  const caps = toggle(true, () => {}, 'עם כתוביות');
  const summary = el('p', { class: 'muted small' });
  const list = el('div', { class: 'exports' });
  const prog = el('div', { class: 'export-prog', hidden: true });
  let running = null;

  const drawRatios = () => {
    if (!chosen.size) chosen.add(S.doc.canvas.ratio);
    ratios.replaceChildren(...App.state.ratios.map((r) => el('button', { class: 'chip' + (chosen.has(r) ? ' on' : ''), type: 'button', text: RATIO_LABELS[r] || r,
      onclick: () => { if (chosen.has(r) && chosen.size > 1) chosen.delete(r); else chosen.add(r); drawRatios(); } })));
  };
  const drawList = () => {
    const items = S.doc.exports || [];
    list.replaceChildren();
    if (!items.length) { list.append(el('p', { class: 'muted small', text: 'סרטונים שמייצאים מופיעים כאן, מוכנים להורדה.' })); return; }
    for (const x of items) {
      const url = `/api/projects/${S.pid}/exports/${encodeURIComponent(x.file)}`;
      list.append(el('div', { class: 'export-row' },
        el('div', { class: 'ex-meta' }, el('b', { text: `${fmt(x.duration)} · ${dims(x.width, x.height)}` }),
          el('small', { text: `${fmtSize(x.size)}${x.captions ? ' · עם כתוביות' : ''} · ${new Date(x.created * 1000).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}` })),
        el('div', { class: 'ex-actions' },
          el('a', { class: 'btn btn-dark btn-sm', href: url + '?dl=1', download: x.file }, 'הורדה', el('i', { class: 'ar' }, icon('download'))),
          el('a', { class: 'ib sm', href: url, target: '_blank', rel: 'noopener', title: 'צפייה', 'aria-label': 'צפייה' }, icon('eye')),
          el('button', { class: 'ib sm', title: 'מחיקה', 'aria-label': 'מחיקת הייצוא', onclick: async () => {
            if (!(await confirmBox('למחוק את הקובץ?', 'הסרטון המיוצא יימחק מהמחשב. הפרויקט עצמו נשאר.', 'מחיקה'))) return;
            try { await api(url, { method: 'DELETE' }); refresh(); } catch (e) { toast(e.message, { error: true }); }
          } }, icon('trash')))));
    }
  };

  const follow = (jobId) => {
    running = jobId;
    const bar = progressBar();
    const note = el('span', { class: 'muted small', text: 'מתחיל…' });
    prog.replaceChildren(el('div', { class: 'row between' }, note, el('button', { class: 'tlink', text: 'ביטול', onclick: () => api(`/api/jobs/${jobId}/cancel`, { method: 'POST' }).catch(() => {}) })), bar);
    prog.hidden = false;
    go.disabled = true;
    track(jobId, (j) => { bar.set(j.progress); note.textContent = `${j.message || 'מייצא…'} ${Math.round(j.progress * 100)}%`; }).then((j) => {
      running = null;
      prog.hidden = true;
      go.disabled = false;
      if (j && j.status === 'done') toast(j.result.exports.length > 1 ? `${j.result.exports.length} סרטונים מוכנים.` : 'הסרטון מוכן.', { action: { label: 'הורדה', run: () => { const a = list.querySelector('a.btn'); if (a) a.click(); } } });
    });
  };
  const go = el('button', { class: 'btn btn-cta', onclick: async () => {
    const r = await op('export', { ratios: [...chosen], quality, captions: caps.input.checked });
    if (r && r.job) follow(r.job);
  } }, 'ייצוא', el('i', { class: 'ar' }, icon('arrow')));
  const link = (kind, label) => el('a', { class: 'chip', href: `/api/projects/${S.pid}/text.${kind}`, download: '' }, icon('download'), label);

  const node = el('div', { class: 'panel', dataset: { panel: 'export' } }, head('EXPORT', 'ייצוא'),
    el('div', { class: 'panel-body' },
      sec('פורמטים, אפשר כמה בבת אחת', ratios, el('small', { class: 'muted', text: 'פורמט שונה מהמקור חותך את התמונה סביב המרכז.' })),
      sec('איכות', qual),
      sec(null, caps, summary, go, prog),
      sec('קבצים מוכנים', list),
      sec('טקסט', el('div', { class: 'chips' }, link('srt', 'כתוביות SRT'), link('vtt', 'כתוביות VTT'), link('txt', 'תמלול נקי'), link('credits', 'קרדיטים')))));
  const update = () => {
    const d = S.derived;
    drawRatios();
    drawList();
    const fpsNow = Math.round((d.fps[0] / d.fps[1]) * 100) / 100;
    summary.textContent = `אורך: ${fmt(d.duration)} · ${fpsNow} פריימים לשנייה${chosen.size > 1 ? ` · ${chosen.size} קבצים` : ''}`;
    go.disabled = d.duration <= 0 || !!running;
    caps.input.disabled = !S.doc.captions.enabled;
    if (!S.doc.captions.enabled) caps.input.checked = false;
    const job = S.jobs.find((j) => j.kind === 'export');
    if (job && !running) follow(job.id);
  };
  return { node, update };
}

// ----------------------------------------------------------------- shell

export function buildLibrary(host, openMcp) {
  const panels = { media: mediaPanel(), transcript: transcriptPanel(), captions: captionsPanel(), text: textPanel(),
    voice: voicePanel(), sound: soundPanel(), ai: aiPanel(openMcp), export: exportPanel() };
  const tabs = el('nav', { class: 'ltabs', 'aria-label': 'ספריות וכלים' });
  let current = 'media';
  const show = (id) => {
    current = id;
    host.dataset.tab = id;
    for (const b of tabs.children) b.classList.toggle('on', b.dataset.tab === id);
    for (const [k, p] of Object.entries(panels)) p.node.hidden = k !== id;
    if (S.doc) panels[id].update();
  };
  for (const t of TABS) tabs.append(el('button', { type: 'button', dataset: { tab: t.id }, title: t.label, onclick: () => show(t.id) }, icon(t.ic), el('span', { text: t.label })));
  host.append(tabs, ...Object.values(panels).map((p) => p.node));
  on('state', () => panels[current].update());
  show('media');
  return { show, destroy: () => { for (const p of Object.values(panels)) p.destroy && p.destroy(); } };
}
