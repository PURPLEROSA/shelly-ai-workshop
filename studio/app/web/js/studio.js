// The editor screen: header, preview stage, and the panels around it.
import { api } from './api.js';
import { el, icon, icons, fmt, toast, modal, progressBar } from './ui.js';
import { App, renderTop, setTheme } from './app.js';
import { S, on, emit, reset, applyState, refresh, op, select, findItem, clampTime, fps, mainTrack } from './store.js';
import { Player } from './player.js';
import { buildTimeline, actions } from './timeline.js';
import { buildInspector } from './inspector.js';
import { buildLibrary, uploadMedia } from './library.js';

let cleanup = [];
const isNarrow = () => window.matchMedia('(max-width: 899px)').matches;

export function closeEditor() {
  if (!S.alive) return;
  S.alive = false;
  if (S.player) S.player.destroy();
  for (const fn of cleanup) { try { fn(); } catch { /* ignore */ } }
  cleanup = [];
}

function looksSvg() {
  if (document.getElementById('looks-svg')) return;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.id = 'looks-svg';
  svg.setAttribute('width', '0');
  svg.setAttribute('height', '0');
  svg.style.position = 'absolute';
  for (const lk of App.state.looks) {
    const f = document.createElementNS(ns, 'filter');
    f.id = 'look-' + lk.id;
    f.setAttribute('color-interpolation-filters', 'sRGB');
    const ct = document.createElementNS(ns, 'feComponentTransfer');
    ['R', 'G', 'B'].forEach((ch, i) => {
      const fn = document.createElementNS(ns, 'feFunc' + ch);
      fn.setAttribute('type', 'table');
      fn.setAttribute('tableValues', lk.curves[i].join(' '));
      ct.append(fn);
    });
    const m = lk.matrix;
    const cm = document.createElementNS(ns, 'feColorMatrix');
    cm.setAttribute('type', 'matrix');
    cm.setAttribute('values', `${m[0].join(' ')} 0 0 ${m[1].join(' ')} 0 0 ${m[2].join(' ')} 0 0 0 0 0 1 0`);
    f.append(ct, cm);
    svg.append(f);
  }
  document.body.append(svg);
}

export function openMcpDialog() {
  const st = App.state;
  const cmd = `claude mcp add --transport http studio ${st.mcp_url}`;
  const json = JSON.stringify({ mcpServers: { studio: { type: 'http', url: st.mcp_url } } }, null, 2);
  const curl = `curl -X POST ${st.mcp_url.replace('/mcp', '')}/api/projects/${S.pid || '<project>'}/ops \\\n  -H 'Content-Type: application/json' \\\n  -d '{"op": "remove_silences", "args": {"level": "normal"}}'`;
  const block = (text) => {
    const pre = el('pre', { class: 'code', dir: 'ltr', text });
    return el('div', { class: 'codebox' }, pre, el('button', { class: 'ib sm', 'aria-label': 'העתקה', title: 'העתקה',
      onclick: async () => { try { await navigator.clipboard.writeText(text); toast('הועתק.'); } catch { /* ignore */ } } }, icon('copy')));
  };
  modal({ title: 'API · MCP', wide: true, body: el('div', { class: 'mcp' },
    el('p', { class: 'muted', text: `כל פעולת עריכה בסטודיו היא גם כלי MCP וגם קריאת REST: ${st.tools} כלים. מחברים סוכן, מבקשים ממנו במילים, ורואים את הטיימליין משתנה כאן בזמן אמת. כל שינוי שלו נכנס להיסטוריה, ואפשר לבטל אותו.` }),
    el('h3', { text: 'Claude Code' }), block(cmd),
    el('h3', { text: 'Claude Desktop, Cursor, VS Code ואחרים' }), block(json),
    el('h3', { text: 'REST' }), block(curl),
    el('p', { class: 'muted small' }, 'הרשימה המלאה של הפעולות והפרמטרים: ',
      el('a', { class: 'tlink', href: '/api/ops', target: '_blank', rel: 'noopener', dir: 'ltr', text: '/api/ops' }),
      '. החיבור פתוח רק מהמחשב הזה.')) });
}

export async function openEditor(pid, view) {
  closeEditor();
  reset(pid);
  view.replaceChildren(el('div', { class: 'center-msg' }, el('span', { class: 'spin dark' })));
  renderTop();
  let st;
  try {
    st = await api('/api/projects/' + pid);
  } catch (err) {
    if (S.pid !== pid) return;
    view.replaceChildren(el('div', { class: 'center-msg' }, el('div', { class: 'card fatal' },
      el('h2', { text: 'הפרויקט לא נמצא' }), el('p', { class: 'muted', text: err.message }),
      el('a', { class: 'btn btn-dark btn-sm plain', href: '#/', text: 'חזרה לפרויקטים' }))));
    return;
  }
  if (S.pid !== pid || !S.alive) return;
  looksSvg();

  // ----- stage
  const screen = el('div', { class: 'screen' });
  const screenWrap = el('div', { class: 'screen-wrap' }, screen);
  const bigPlay = el('button', { class: 'bigplay', 'aria-label': 'ניגון', html: icons.play });
  const empty = el('div', { class: 'stage-empty', hidden: true }, icon('film'), el('b', { text: 'הטיימליין ריק' }),
    el('span', { text: 'מעלים קובץ בלשונית המדיה, או גוררים אותו לכאן.' }));
  screen.append(bigPlay);
  const player = new Player(screen);
  S.player = player;
  screen.addEventListener('click', () => player.toggle());
  const tb = (ic, label, fn) => el('button', { class: 'ib sm', type: 'button', title: label, 'aria-label': label, onclick: fn }, icon(ic));
  const playBtn = el('button', { class: 'ib play', 'aria-label': 'ניגון או השהיה', html: icons.play, onclick: () => player.toggle() });
  const clock = el('span', { class: 'time', dir: 'ltr', text: '0:00.0' });
  const meta = el('span', { class: 'time meta', dir: 'ltr' });
  const transport = el('div', { class: 'transport' },
    clock,
    el('div', { class: 'tr-mid' },
      tb('prev', 'לתחילה', () => player.seek(0)), tb('stepb', 'פריים אחורה', () => actions.step(-1)),
      playBtn,
      tb('stepf', 'פריים קדימה', () => actions.step(1)), tb('next', 'לסוף', () => player.seek(S.derived.duration))),
    meta);
  const stage = el('div', { class: 'stage' }, screenWrap, empty, transport);

  // ----- panels
  const insp = el('aside', { class: 'insp' });
  const lib = el('aside', { class: 'lib' });
  const tl = el('section', { class: 'tl' });
  const root = el('section', { class: 'studio' }, lib, stage, insp, tl);
  view.replaceChildren(root);

  // ----- header
  const title = el('span', { class: 'title', contenteditable: 'plaintext-only', spellcheck: 'false', text: st.doc.name, 'aria-label': 'שם הפרויקט' });
  title.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); title.blur(); } });
  title.addEventListener('blur', () => {
    const name = title.textContent.trim();
    if (!name) { title.textContent = S.doc.name; return; }
    if (name !== S.doc.name) op('rename_project', { name });
  });
  const activity = el('div', { class: 'activity' });
  const themeBtn = el('button', { class: 'ib', title: 'רקע בהיר או כהה', 'aria-label': 'החלפת ערכת צבעים',
    onclick: () => { setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'); themeBtn.replaceChildren(icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon')); } },
  icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon'));
  renderTop({
    start: el('div', { class: 'top-start' }, el('a', { class: 'ib', href: '#/', 'aria-label': 'חזרה לפרויקטים', title: 'חזרה' }, icon('back')), title),
    middle: el('div', { class: 'top-mid' }, activity),
    end: el('div', { class: 'top-tools' },
      el('button', { class: 'chip mcpbtn', type: 'button', onclick: openMcpDialog }, icon('plug'), el('span', { dir: 'ltr', text: 'API · MCP' })),
      themeBtn,
      el('button', { class: 'btn btn-cta btn-sm', onclick: () => library.show('export') }, 'ייצוא', el('i', { class: 'ar' }, icon('arrow')))),
  });

  const timeline = buildTimeline(tl);
  const inspector = buildInspector(insp);
  const library = buildLibrary(lib, openMcpDialog);
  cleanup.push(() => timeline.destroy(), () => library.destroy());

  // ----- reactions
  function sizeScreen() {
    const f = S.derived.frame;
    const cs = getComputedStyle(screenWrap);
    const w0 = screenWrap.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const h0 = screenWrap.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    if (w0 <= 0 || h0 <= 0) return;
    const ratio = f.w / f.h;
    let w = w0, h = w / ratio;
    if (h > h0) { h = h0; w = h * ratio; }
    screen.style.width = Math.floor(w) + 'px';
    screen.style.height = Math.floor(h) + 'px';
  }
  const ro = new ResizeObserver(sizeScreen);
  ro.observe(screenWrap);
  cleanup.push(() => ro.disconnect());

  let hadClips = null;
  on('state', () => {
    const d = S.derived;
    // the first clip just landed (a fresh upload finished preparing): move on to its transcript
    const clips = mainTrack().items.length > 0;
    if (hadClips === false && clips) library.show('transcript');
    hadClips = clips;
    sizeScreen();
    player.refresh();
    const has = d.duration > 0;
    empty.hidden = has;
    screenWrap.hidden = !has;
    meta.textContent = `${fmt(d.duration, true)}  /  ${d.frame.w}x${d.frame.h}  /  ${Math.round((d.fps[0] / d.fps[1]) * 100) / 100} fps`;
    if (document.activeElement !== title) title.textContent = S.doc.name;
    document.title = `${S.doc.name} · הסטודיו שלי`;
    drawActivity();
  });
  on('time', () => { clock.textContent = fmt(S.time, true); });
  on('play', () => { playBtn.innerHTML = S.playing ? icons.pause : icons.play; bigPlay.classList.toggle('hide', S.playing); });

  function drawActivity() {
    const busy = [];
    for (const m of Object.values(S.doc.media)) {
      if (m.status === 'preparing') busy.push(`מכין את ${m.name}`);
      else if (m.transcript.status === 'running') busy.push(`מתמלל את ${m.name}`);
    }
    for (const j of S.jobs) if (['export', 'voice', 'stock', 'ai', 'detach'].includes(j.kind)) busy.push(`${j.message || 'עובד…'} ${Math.round(j.progress * 100)}%`);
    activity.replaceChildren(...busy.slice(0, 2).map((t) => el('span', { class: 'pill-s live' }, el('i', { class: 'live' }), t)));
  }
  on('jobs', drawActivity);

  // ----- live sync: edits by an AI agent (or another window) show up here
  let polling = true;
  let hadJobs = false;
  (async function poll() {
    while (polling && S.alive && S.pid === pid) {
      await new Promise((r) => setTimeout(r, 1300));
      if (!polling || !S.alive || S.pid !== pid || document.hidden) continue;
      try {
        const r = await api(`/api/projects/${pid}/rev`);
        const jobsChanged = JSON.stringify(r.jobs.map((j) => [j.id, j.progress, j.message])) !== JSON.stringify(S.jobs.map((j) => [j.id, j.progress, j.message]));
        S.jobs = r.jobs;
        if (jobsChanged) emit('jobs');
        const finished = hadJobs && !r.jobs.length;
        hadJobs = r.jobs.length > 0;
        if ((r.rev !== S.doc.rev || finished) && !S.pending) await refresh();
      } catch { /* the server may be restarting */ }
    }
  })();
  cleanup.push(() => { polling = false; });

  // ----- keyboard
  const onKey = (e) => {
    if (!S.alive) return;
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) return;
    if (document.querySelector('.modal-wrap')) return;
    const mod = e.ctrlKey || e.metaKey;
    const k = e.key.toLowerCase();
    const sel = window.getSelection();
    const textSel = sel && !sel.isCollapsed && lib.contains(sel.anchorNode);
    if (e.code === 'Space' && !mod) { e.preventDefault(); player.toggle(); }
    else if (mod && k === 'z') { e.preventDefault(); op(e.shiftKey ? 'redo' : 'undo'); }
    else if (mod && k === 'y') { e.preventDefault(); op('redo'); }
    else if (mod && k === 'd') { e.preventDefault(); actions.duplicate(); }
    else if (mod) return;
    else if (e.code === 'KeyS') { e.preventDefault(); actions.split(); }
    else if (e.code === 'KeyI') { e.preventDefault(); actions.rangeIn(); }
    else if (e.code === 'KeyO') { e.preventDefault(); actions.rangeOut(); }
    else if (e.code === 'KeyX') { e.preventDefault(); actions.cutRange(); }
    else if (e.code === 'KeyK') { e.preventDefault(); inspector.addKeyframe(); }
    else if (e.key === 'Escape') { actions.clearRange(); select(null); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); actions.step(e.shiftKey ? -10 : -1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); actions.step(e.shiftKey ? 10 : 1); }
    else if (e.key === 'Home') { e.preventDefault(); player.seek(0); }
    else if (e.key === 'End') { e.preventDefault(); player.seek(S.derived.duration); }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && !textSel && S.sel) { e.preventDefault(); actions.remove(); }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && textSel) {
      const btn = lib.querySelector('.selbar:not([hidden]) .btn');
      if (btn) { e.preventDefault(); btn.click(); }
    }
  };
  document.addEventListener('keydown', onKey);
  cleanup.push(() => document.removeEventListener('keydown', onKey));

  // ----- files dropped anywhere on the editor go to the library, and onto the timeline if it is empty
  const onDrop = (e) => {
    if (!e.dataTransfer || !e.dataTransfer.files.length) return;
    e.preventDefault();
    const emptyNow = !mainTrack().items.length;
    for (const f of e.dataTransfer.files) uploadMedia(f, emptyNow || !!e.target.closest('.tl, .stage'), undefined);
  };
  root.addEventListener('drop', onDrop);
  cleanup.push(() => root.removeEventListener('drop', onDrop));

  applyState(st);
  library.show(isNarrow() ? 'transcript' : (mainTrack().items.length ? 'transcript' : 'media'));
  // a fresh upload is still being prepared: keep the screen informed until it lands on the timeline
  if (!mainTrack().items.length && st.jobs.length) toast('הסרטון בהכנה. הוא יופיע בטיימליין בעוד רגע.', { ttl: 5000 });
}
