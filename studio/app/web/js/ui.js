// Small DOM helpers, icons, toasts and modals shared by every screen.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (v === true) node.setAttribute(k, '');
    else node.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

const P = (d, extra = '') =>
  `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${d}</svg>`;

export const icons = {
  play: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5z"/></svg>`,
  pause: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4.5" height="14" rx="1.2"/><rect x="13.5" y="5" width="4.5" height="14" rx="1.2"/></svg>`,
  back: P('<path d="M9 6l6 6-6 6"/>'),
  arrow: P('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
  undo: P('<path d="M15 14l5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>'),
  redo: P('<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>'),
  gear: P('<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.6V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.6 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
  phone: P('<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>'),
  trash: P('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>'),
  download: P('<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>'),
  upload: P('<path d="M12 16V5M7 9l5-5 5 5M5 20h14"/>', 'width="28" height="28"'),
  spark: P('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>'),
  cut: P('<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M20 4L8.1 15.9M14.5 14.5L20 20M8.1 8.1L12 12"/>'),
  cc: P('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 10.5a2 2 0 1 0 0 3M17 10.5a2 2 0 1 0 0 3"/>'),
  text: P('<path d="M5 6h14M5 12h14M5 18h9"/>'),
  x: P('<path d="M6 6l12 12M18 6L6 18"/>'),
  check: P('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
  restore: P('<path d="M4 12a8 8 0 1 0 2.6-5.9"/><path d="M4 4v5h5"/>'),
  edit: P('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>'),
  copy: P('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>'),
  eye: P('<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  start: P('<path d="M19 5v14L8 12z" fill="currentColor"/><path d="M5 5v14"/>'),
  mic: P('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>'),
  film: P('<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M8 4v16M16 4v16M3 9h5M3 15h5M16 9h5M16 15h5"/>'),
};

export function icon(name, cls = '') {
  return el('span', { class: 'ic ' + cls, html: icons[name] || '' });
}

export function fmt(t, withTenths = false) {
  if (!isFinite(t) || t < 0) t = 0;
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  if (withTenths) return `${m}:${s.toFixed(1).padStart(4, '0')}`;
  return `${m}:${String(Math.floor(s)).padStart(2, '0')}`;
}

export function fmtSize(bytes) {
  if (bytes > 1e9) return (bytes / 1e9).toFixed(1) + ' GB';
  if (bytes > 1e6) return (bytes / 1e6).toFixed(1) + ' MB';
  return Math.max(1, Math.round(bytes / 1e3)) + ' KB';
}

export function toast(message, opts = {}) {
  const root = document.getElementById('toasts');
  const node = el('div', { class: 'toast' + (opts.error ? ' err' : '') }, el('span', { text: message }));
  if (opts.action) {
    node.append(el('button', {
      class: 'toast-act', text: opts.action.label,
      onclick: () => { opts.action.run(); node.remove(); },
    }));
  }
  root.append(node);
  const ttl = opts.ttl || (opts.error ? 6500 : 3800);
  setTimeout(() => { node.classList.add('out'); setTimeout(() => node.remove(), 300); }, ttl);
  return node;
}

export function modal({ title, body, wide = false, onClose }) {
  const root = document.getElementById('modal-root');
  const close = () => { wrap.remove(); document.removeEventListener('keydown', onKey); onClose && onClose(); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  const wrap = el('div', { class: 'modal-wrap', onclick: (e) => { if (e.target === wrap) close(); } },
    el('div', { class: 'modal' + (wide ? ' wide' : ''), role: 'dialog', 'aria-modal': 'true', 'aria-label': title },
      el('div', { class: 'modal-head' },
        el('h2', { text: title }),
        el('button', { class: 'ib', 'aria-label': 'סגירה', onclick: close }, icon('x'))),
      el('div', { class: 'modal-body' }, body)));
  root.append(wrap);
  document.addEventListener('keydown', onKey);
  const first = wrap.querySelector('input, select, textarea, button.btn');
  if (first && !('ontouchstart' in window)) first.focus();
  return { close, node: wrap };
}

export function confirmBox(title, text, okLabel = 'אישור') {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v); m.close(); } };
    const m = modal({
      title,
      body: el('div', {},
        el('p', { class: 'muted', text }),
        el('div', { class: 'row end gap' },
          el('button', { class: 'btn btn-ghost btn-sm plain', text: 'ביטול', onclick: () => finish(false) }),
          el('button', { class: 'btn btn-dark btn-sm plain', text: okLabel, onclick: () => finish(true) }))),
      onClose: () => { if (!done) { done = true; resolve(false); } },
    });
  });
}

export function segmented(options, value, onChange, label) {
  const wrap = el('div', { class: 'seg', role: 'radiogroup', 'aria-label': label || '' });
  const set = (v) => {
    for (const b of wrap.children) {
      const on = b.dataset.v === String(v);
      b.classList.toggle('on', on);
      b.setAttribute('aria-checked', on ? 'true' : 'false');
    }
  };
  for (const o of options) {
    wrap.append(el('button', {
      type: 'button', role: 'radio', dataset: { v: String(o.value) }, text: o.label,
      onclick: () => { set(o.value); onChange(o.value); },
    }));
  }
  set(value);
  wrap.setValue = set;
  return wrap;
}

export function toggle(checked, onChange, label) {
  const input = el('input', { type: 'checkbox', onchange: () => onChange(input.checked) });
  input.checked = !!checked;
  const wrap = el('label', { class: 'switch' }, input, el('i'), label ? el('span', { text: label }) : null);
  wrap.input = input;
  return wrap;
}

export function slider({ min, max, step, value, onInput, label, format }) {
  const out = el('output', { text: format ? format(value) : value });
  const input = el('input', {
    type: 'range', min, max, step, value, 'aria-label': label,
    oninput: () => { out.textContent = format ? format(+input.value) : input.value; onInput(+input.value); },
  });
  const wrap = el('label', { class: 'field slider' }, el('span', { class: 'lbl' }, label, out), input);
  wrap.setValue = (v) => { input.value = v; out.textContent = format ? format(+v) : v; };
  return wrap;
}

export function progressBar() {
  const bar = el('i');
  const wrap = el('div', { class: 'bar' }, bar);
  wrap.set = (f) => { bar.style.width = Math.round(Math.max(0, Math.min(1, f)) * 100) + '%'; };
  return wrap;
}

export function debounce(fn, ms) {
  let t;
  const wrapped = (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  wrapped.flush = (...a) => { clearTimeout(t); fn(...a); };
  wrapped.cancel = () => clearTimeout(t);
  return wrapped;
}
