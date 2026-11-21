// Boot, header, home screen and settings.
import { api, uploadVideo, followJob } from './api.js';
import { el, icon, fmt, toast, modal, confirmBox, toggle, progressBar } from './ui.js';
import { openEditor, closeEditor } from './editor.js';

export const App = { state: null, view: null };
const view = document.getElementById('view');
const top = document.getElementById('top');
let homeAlive = false;
const uploads = new Map(); // temp id -> {name, progress}

export async function refreshState() {
  App.state = await api('/api/state');
  return App.state;
}

// ---------------------------------------------------------------- header

export function renderTop(editorBits = null) {
  top.replaceChildren();
  const logo = el('a', { class: 'logo', href: '#/', 'aria-label': 'הסטודיו שלי, למסך הבית' },
    el('strong', {}, 'הסטודיו שלי', el('span', { text: '.' })),
    el('small', { text: 'LOCAL CONTENT STUDIO' }));
  const actions = el('div', { class: 'top-actions' });
  if (App.state && App.state.local) {
    actions.append(el('button', { class: 'ib', title: 'גישה מהנייד', 'aria-label': 'גישה מהנייד', onclick: openMobile }, icon('phone')));
  }
  actions.append(el('button', { class: 'ib', title: 'הגדרות', 'aria-label': 'הגדרות', onclick: () => openSettings() }, icon('gear')));
  if (editorBits) {
    top.classList.add('in-editor');
    top.append(editorBits.start, editorBits.middle, el('div', { class: 'top-end' }, editorBits.end, actions));
  } else {
    top.classList.remove('in-editor');
    top.append(logo, actions);
  }
}

// ------------------------------------------------------------------ home

function statusPill(p) {
  if (p.status === 'error') return el('span', { class: 'pill-s err', text: 'שגיאה' });
  if (p.job) {
    const pct = Math.round(p.job.progress * 100);
    const label = p.status !== 'ready' ? 'מכין' : 'מתמלל';
    return el('span', { class: 'pill-s live' }, el('i', { class: 'live' }), `${label} ${pct}%`);
  }
  if (p.transcript === 'done') return el('span', { class: 'pill-s ok', text: p.exports ? `יוצא ${p.exports}×` : 'מוכן לעריכה' });
  if (p.status === 'ready') return el('span', { class: 'pill-s', text: 'בלי תמלול' });
  return el('span', { class: 'pill-s', text: 'בהכנה' });
}

function projectCard(p) {
  const thumb = el('div', { class: 'thumb' });
  const img = el('img', { src: `/api/projects/${p.id}/thumb.jpg`, alt: '', loading: 'lazy' });
  img.onerror = () => img.remove();
  thumb.append(img, el('span', { class: 'dur', text: fmt(p.duration) }));
  const del = el('button', {
    class: 'ib sm del', 'aria-label': 'מחיקת הפרויקט', title: 'מחיקה',
    onclick: async (e) => {
      e.preventDefault(); e.stopPropagation();
      if (await confirmBox('למחוק את הפרויקט?', `״${p.name}״ יימחק מהמחשב, כולל הסרטונים שיוצאו ממנו.`, 'מחיקה')) {
        await api('/api/projects/' + p.id, { method: 'DELETE' });
        loadHome();
      }
    },
  }, icon('trash'));
  return el('a', { class: 'card proj', href: '#/p/' + p.id },
    thumb,
    el('div', { class: 'proj-meta' }, el('b', { text: p.name }), statusPill(p)),
    del);
}

function uploadCard(u) {
  const bar = progressBar();
  bar.set(u.progress);
  return el('div', { class: 'card proj uploading' },
    el('div', { class: 'thumb' }, el('span', { class: 'spin' })),
    el('div', { class: 'proj-meta' }, el('b', { text: u.name }),
      el('span', { class: 'pill-s live' }, el('i', { class: 'live' }), `מעלה ${Math.round(u.progress * 100)}%`)),
    bar);
}

async function loadHome() {
  if (!homeAlive) return;
  let data;
  try { data = await api('/api/projects'); } catch (e) { toast(e.message, { error: true }); return; }
  if (!homeAlive) return;
  const grid = document.getElementById('grid');
  if (!grid) return;
  grid.replaceChildren();
  for (const u of uploads.values()) grid.append(uploadCard(u));
  for (const p of data.projects) grid.append(projectCard(p));
  const empty = document.getElementById('empty');
  if (empty) empty.hidden = data.projects.length > 0 || uploads.size > 0;
  const busy = data.projects.some((p) => p.job) || uploads.size > 0;
  clearTimeout(loadHome.timer);
  if (busy) loadHome.timer = setTimeout(loadHome, 1500);
}

async function startUpload(file) {
  if (!file) return;
  if (!file.type.startsWith('video/') && !/\.(mp4|mov|m4v|webm|mkv|avi|3gp)$/i.test(file.name)) {
    toast('זה לא נראה כמו קובץ וידאו. נתמכים MP4, MOV, WEBM ועוד.', { error: true });
    return;
  }
  const id = Math.random().toString(36).slice(2);
  uploads.set(id, { name: file.name.replace(/\.[^.]+$/, ''), progress: 0 });
  loadHome();
  let last = 0;
  try {
    const res = await uploadVideo(file, (f) => {
      uploads.get(id).progress = f;
      if (Date.now() - last > 400) { last = Date.now(); loadHome(); }
    });
    uploads.delete(id);
    location.hash = '#/p/' + res.project.id;
  } catch (e) {
    uploads.delete(id);
    toast(e.message, { error: true });
    loadHome();
  }
}

function renderHome() {
  homeAlive = true;
  renderTop();
  const input = el('input', { type: 'file', accept: 'video/*', hidden: true, onchange: () => { startUpload(input.files[0]); input.value = ''; } });
  const drop = el('label', { class: 'drop card', tabindex: '0' },
    input,
    el('span', { class: 'drop-ic' }, icon('upload')),
    el('b', { text: 'גוררים לכאן סרטון' }),
    el('span', { class: 'btn btn-cta' }, 'בחירת קובץ', el('i', { class: 'ar' }, icon('arrow'))),
    el('small', { text: 'MP4, MOV ועוד. הקובץ נשאר אצלך במחשב.' }));
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
  for (const ev of ['dragenter', 'dragover']) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); });
  for (const ev of ['dragleave', 'drop']) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); });
  drop.addEventListener('drop', (e) => startUpload(e.dataTransfer.files[0]));

  view.replaceChildren(el('section', { class: 'home' },
    el('div', { class: 'hero' },
      el('div', { class: 'hero-copy' },
        el('span', { class: 'eyebrow', text: 'TRANSCRIBE · CUT · CAPTION' }),
        el('h1', {}, 'וידאו נכנס.', el('br'), el('span', { class: 'mag', text: 'תוכן יוצא.' })),
        el('p', { class: 'lead', text: 'תמלול בעברית, עריכה ישר מהטקסט, כתוביות ו-AI. הכל רץ אצלך על המחשב, בלי מנוי ובלי ענן.' }),
        el('div', { class: 'facts' },
          ...['תמלול מקומי', 'חיתוך דרך הטקסט', 'כתוביות צרובות', 'גם מהנייד'].map((t) => el('span', { text: t })))),
      drop),
    el('div', { class: 'projects' },
      el('div', { class: 'sec-head' }, el('span', { class: 'eyebrow', text: 'PROJECTS' }), el('h2', { text: 'הפרויקטים שלי' })),
      el('div', { class: 'grid', id: 'grid' }),
      el('p', { class: 'empty muted', id: 'empty', hidden: true, text: 'עדיין אין כאן פרויקטים. הסרטון הראשון שמעלים מופיע כאן.' }))));
  loadHome();
}

// -------------------------------------------------------------- settings

function field(label, control, hint) {
  return el('label', { class: 'field' }, el('span', { class: 'lbl', text: label }), control, hint ? el('small', { class: 'muted', text: hint }) : null);
}

export async function openSettings(section = 'transcribe') {
  await refreshState();
  const st = App.state;
  const s = st.settings;
  const readonly = !st.local;
  const body = el('div', { class: 'settings' });
  const save = async (patch) => {
    try {
      const r = await api('/api/settings', { method: 'PUT', body: patch });
      App.state.settings = r.settings;
      App.state.ai = r.ai;
      document.dispatchEvent(new CustomEvent('studio:settings'));
      return r;
    } catch (e) { toast(e.message, { error: true }); return null; }
  };

  // --- transcription
  const models = el('div', { class: 'choices' });
  for (const m of st.models) {
    const input = el('input', { type: 'radio', name: 'tmodel', value: m.id, disabled: readonly, onchange: () => save({ transcribe: { model: m.id } }) });
    input.checked = s.transcribe.model === m.id;
    models.append(el('label', { class: 'choice' }, input,
      el('span', {}, el('b', { text: m.label }),
        el('small', { text: m.downloaded ? 'כבר במחשב' : `הורדה חד-פעמית של ${m.gb} GB בשימוש הראשון` }))));
  }
  const lang = el('select', { disabled: readonly, onchange: () => save({ transcribe: { language: lang.value } }) },
    ...st.languages.map((l) => el('option', { value: l.id, text: l.label, selected: l.id === s.transcribe.language })));

  // --- AI
  const ai = s.ai;
  const provBox = el('div', { class: 'prov-fields' });
  const providers = [
    { id: 'none', label: 'בלי AI', hint: 'ניקוי חכם עובד גם בלי מודל' },
    { id: 'ollama', label: 'Ollama', hint: 'מודל מקומי, חינם, בלי אינטרנט' },
    { id: 'claude', label: 'Claude', hint: 'התוצאות הטובות ביותר, עם מפתח API' },
    { id: 'openai', label: 'OpenAI / תואם', hint: 'GPT או כל שירות בפורמט של OpenAI' },
  ];
  const drawProvider = (prov) => {
    provBox.replaceChildren();
    if (prov === 'ollama') {
      const url = el('input', { type: 'url', dir: 'ltr', value: ai.ollama.base_url, disabled: readonly });
      const model = el('select', { disabled: readonly, onchange: () => save({ ai: { ollama: { model: model.value } } }) },
        el('option', { value: ai.ollama.model || '', text: ai.ollama.model || 'טוען רשימה…' }));
      const load = async () => {
        await save({ ai: { ollama: { base_url: url.value.trim() } } });
        try {
          const r = await api('/api/ai/models?provider=ollama');
          model.replaceChildren(...(r.models.length ? r.models : ['']).map((m) =>
            el('option', { value: m, text: m || 'אין מודלים מותקנים', selected: m === ai.ollama.model })));
          if (r.models.length && !r.models.includes(ai.ollama.model)) { ai.ollama.model = r.models[0]; save({ ai: { ollama: { model: r.models[0] } } }); }
        } catch (e) {
          model.replaceChildren(el('option', { value: '', text: 'Ollama לא רץ כרגע' }));
        }
      };
      url.onchange = load;
      provBox.append(
        field('מודל', model, 'מתקינים את Ollama מ-ollama.com, מורידים מודל שמבין עברית, והוא יופיע כאן.'),
        field('כתובת', url));
      if (!readonly) load();
    } else if (prov === 'claude') {
      const key = el('input', { type: 'password', dir: 'ltr', autocomplete: 'off', placeholder: ai.claude.has_key ? `מפתח שמור ${ai.claude.key_hint}` : 'sk-ant-…', disabled: readonly,
        onchange: async () => { if (key.value.trim() && await save({ ai: { claude: { api_key: key.value.trim() } } })) { key.value = ''; key.placeholder = 'המפתח נשמר'; toast('המפתח נשמר במחשב הזה בלבד.'); } } });
      const model = el('select', { disabled: readonly, onchange: () => save({ ai: { claude: { model: model.value } } }) },
        ...st.claude_models.map((m) => el('option', { value: m.id, text: m.label, selected: m.id === ai.claude.model })));
      provBox.append(
        field('מפתח API', key, 'יוצרים מפתח ב-platform.claude.com. הוא נשמר רק בקובץ ההגדרות שבמחשב.'),
        field('מודל', model));
    } else if (prov === 'openai') {
      const url = el('input', { type: 'url', dir: 'ltr', value: ai.openai.base_url, disabled: readonly, onchange: () => save({ ai: { openai: { base_url: url.value.trim() } } }) });
      const key = el('input', { type: 'password', dir: 'ltr', autocomplete: 'off', placeholder: ai.openai.has_key ? `מפתח שמור ${ai.openai.key_hint}` : 'sk-…', disabled: readonly,
        onchange: async () => { if (key.value.trim() && await save({ ai: { openai: { api_key: key.value.trim() } } })) { key.value = ''; key.placeholder = 'המפתח נשמר'; } } });
      const list = el('datalist', { id: 'oai-models' });
      const model = el('input', { type: 'text', dir: 'ltr', list: 'oai-models', value: ai.openai.model, placeholder: 'שם המודל', disabled: readonly, onchange: () => save({ ai: { openai: { model: model.value.trim() } } }) });
      const fetchBtn = el('button', { class: 'btn btn-ghost btn-sm plain', type: 'button', text: 'טעינת רשימת מודלים', disabled: readonly,
        onclick: async () => {
          try {
            const r = await api('/api/ai/models?provider=openai');
            list.replaceChildren(...r.models.map((m) => el('option', { value: m })));
            toast(`נטענו ${r.models.length} מודלים. מתחילים להקליד בשדה כדי לבחור.`);
          } catch (e) { toast(e.message, { error: true }); }
        } });
      provBox.append(field('כתובת השירות', url), field('מפתח API', key), field('מודל', el('div', {}, model, list)), fetchBtn);
    } else {
      provBox.append(el('p', { class: 'muted', text: 'הסרת שתיקות, מילות מילוי וחזרות עובדות בלי שום מודל. מודל AI מוסיף עריכה לפי הנחיה חופשית וכתיבת טקסטים לפוסט.' }));
    }
  };
  const provs = el('div', { class: 'choices two' });
  for (const p of providers) {
    const input = el('input', { type: 'radio', name: 'prov', value: p.id, disabled: readonly,
      onchange: async () => { ai.provider = p.id; await save({ ai: { provider: p.id } }); drawProvider(p.id); } });
    input.checked = ai.provider === p.id;
    provs.append(el('label', { class: 'choice' }, input, el('span', {}, el('b', { text: p.label }), el('small', { text: p.hint }))));
  }
  drawProvider(ai.provider);

  // --- phone
  const phone = el('div', {});
  if (st.local) {
    phone.append(
      toggle(s.mobile_access, (v) => save({ mobile_access: v }), 'לאפשר כניסה ממכשירים אחרים ברשת הביתית'),
      el('p', { class: 'muted', text: 'כשהאפשרות פעילה, רק מי שסרק את קוד ה-QR האישי יכול להיכנס. מומלץ להשתמש ברשת Wi-Fi שסומכים עליה.' }),
      el('button', { class: 'btn btn-dark btn-sm', type: 'button', onclick: openMobile }, 'הצגת קוד QR', el('i', { class: 'ar' }, icon('phone'))));
  } else {
    phone.append(el('p', { class: 'muted', text: 'נכנסת מהנייד. את ההגדרות אפשר לשנות רק מהמחשב שהסטודיו רץ עליו.' }));
  }

  const sections = [
    { id: 'transcribe', label: 'תמלול', node: el('div', {}, el('h3', { text: 'מודל תמלול' }), models, field('שפת הדיבור בסרטונים', lang)) },
    { id: 'ai', label: 'AI', node: el('div', {}, el('h3', { text: 'מודל לעריכה חכמה' }), provs, provBox) },
    { id: 'phone', label: 'נייד', node: el('div', {}, el('h3', { text: 'גישה מהנייד' }), phone) },
  ];
  const nav = el('div', { class: 'seg wide' });
  const pane = el('div', { class: 'settings-pane' });
  const show = (id) => {
    for (const b of nav.children) b.classList.toggle('on', b.dataset.v === id);
    pane.replaceChildren(sections.find((x) => x.id === id).node);
  };
  for (const sec of sections) nav.append(el('button', { type: 'button', dataset: { v: sec.id }, text: sec.label, onclick: () => show(sec.id) }));
  body.append(nav, pane);
  if (readonly) body.append(el('p', { class: 'note', text: 'מצב צפייה: שינויי הגדרות נעשים מהמחשב.' }));
  show(sections.some((x) => x.id === section) ? section : 'transcribe');
  modal({ title: 'הגדרות', body, wide: true });
}

async function openMobile() {
  await refreshState();
  const st = App.state;
  const body = el('div', { class: 'mobile-box' });
  if (!st.settings.mobile_access) {
    body.append(el('p', { class: 'muted', text: 'הגישה מהנייד כבויה כרגע. מפעילים אותה בהגדרות, תחת ״נייד״.' }));
  } else if (!st.mobile_url) {
    body.append(el('p', { class: 'muted', text: 'המחשב לא מחובר לרשת כרגע, אז אין כתובת לשתף.' }));
  } else {
    body.append(
      el('img', { class: 'qr', src: '/api/qr.svg?' + Date.now(), alt: 'קוד QR לכניסה מהנייד', width: 232, height: 232 }),
      el('ol', { class: 'steps' },
        el('li', { text: 'מחברים את הנייד לאותה רשת Wi-Fi של המחשב.' }),
        el('li', { text: 'סורקים את הקוד עם המצלמה.' }),
        el('li', { text: 'מעלים סרטון מהגלריה. המחשב מתמלל ועורך, והנייד רק מציג.' })),
      el('button', { class: 'btn btn-ghost btn-sm plain', type: 'button', text: 'העתקת הקישור',
        onclick: async () => { try { await navigator.clipboard.writeText(st.mobile_url); toast('הקישור הועתק.'); } catch { toast(st.mobile_url, { ttl: 9000 }); } } }),
      el('p', { class: 'muted small', text: 'המחשב צריך להישאר דלוק, והסטודיו פתוח. מחוץ לבית אפשר להתחבר דרך Tailscale.' }));
  }
  modal({ title: 'עורכים מהנייד', body });
}

// ---------------------------------------------------------------- router

async function route() {
  const hash = location.hash || '#/';
  const m = hash.match(/^#\/p\/([a-f0-9]{12})$/);
  clearTimeout(loadHome.timer);
  if (m) {
    homeAlive = false;
    document.body.classList.add('editing');
    await openEditor(m[1], view);
  } else {
    closeEditor();
    document.body.classList.remove('editing');
    renderHome();
  }
}

window.addEventListener('hashchange', route);
window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => e.preventDefault());

(async function boot() {
  try {
    await refreshState();
  } catch (e) {
    view.replaceChildren(el('div', { class: 'fatal card' }, el('h2', { text: 'הסטודיו לא זמין' }), el('p', { text: e.message })));
    return;
  }
  route();
})();
