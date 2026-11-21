// The timeline: tracks, clips, the playhead and everything you do with the mouse.
import { api } from './api.js';
import { el, icon, fmt, toast, confirmBox, segmented } from './ui.js';
import { S, on, emit, op, select, findItem, info, media, mainTrack, fps, clampTime } from './store.js';

const HEAD = 138;
const LANE = { captions: 26, text: 34, video: 60, audio: 46 };
const SNAP = 7;
const peaksCache = new Map();

export const actions = {
  split() {
    const sel = S.sel && findItem(S.sel);
    const inf = sel && info(S.sel);
    const inside = inf && S.time > inf.start + 0.02 && S.time < inf.start + inf.dur - 0.02;
    return op('split_item', inside ? { at: S.time, item: S.sel } : { at: S.time });
  },
  remove() { if (S.sel) return op('remove_item', { item: S.sel }); toast('בוחרים קליפ ואז מוחקים.'); return null; },
  duplicate() { if (S.sel) return op('duplicate_item', { item: S.sel }); return null; },
  rangeIn() { S.range.a = S.time; if (S.range.b != null && S.range.b <= S.time) S.range.b = null; emit('range'); },
  rangeOut() { S.range.b = S.time; if (S.range.a != null && S.range.a >= S.time) S.range.a = null; emit('range'); },
  clearRange() { S.range = { a: null, b: null }; emit('range'); },
  async cutRange() {
    const { a, b } = S.range;
    if (a == null || b == null) { toast('מסמנים תחילת טווח (I) וסוף טווח (O), ואז חותכים.'); return; }
    const r = await op('cut_range', { from: a, to: b });
    if (r) { S.player.seek(a); actions.clearRange(); }
  },
  async keepRange() {
    const { a, b } = S.range;
    if (a == null || b == null) { toast('מסמנים תחילת טווח (I) וסוף טווח (O).'); return; }
    const r = await op('keep_range', { from: a, to: b });
    if (r) { S.player.seek(0); actions.clearRange(); }
  },
  step(dir) { S.player.pause(); S.player.seek(clampTime(S.time + dir / fps())); },
};

function loadPeaks(mid) {
  if (!peaksCache.has(S.pid + mid)) {
    peaksCache.set(S.pid + mid, api(`/api/projects/${S.pid}/media/${mid}/peaks`).then((r) => r.peaks || []).catch(() => []));
  }
  return peaksCache.get(S.pid + mid);
}

export function buildTimeline(host) {
  let pps = 60;
  let fitted = false;
  const scroll = el('div', { class: 'tl-scroll' });
  const inner = el('div', { class: 'tl-inner' });
  const ruler = el('div', { class: 'tl-ruler' });
  const rows = el('div', { class: 'tl-rows' });
  const playhead = el('div', { class: 'tl-playhead' }, el('i'));
  const rangeEl = el('div', { class: 'tl-range', hidden: true });
  const insert = el('div', { class: 'tl-insert', hidden: true });
  inner.append(ruler, rows, rangeEl, insert, playhead);
  scroll.append(inner);

  // ----- toolbar
  const btn = (ic, label, fn, key) => el('button', { class: 'tb', type: 'button', title: key ? `${label} (${key})` : label, 'aria-label': label, onclick: fn }, icon(ic), el('span', { text: label }));
  const undoB = el('button', { class: 'ib sm', title: 'ביטול (Ctrl+Z)', 'aria-label': 'ביטול', onclick: () => op('undo') }, icon('undo'));
  const redoB = el('button', { class: 'ib sm', title: 'ביצוע מחדש (Ctrl+Shift+Z)', 'aria-label': 'ביצוע מחדש', onclick: () => op('redo') }, icon('redo'));
  const tighten = segmented(
    [{ value: 0, label: 'כבוי' }, { value: 0.6, label: 'עדין' }, { value: 0.35, label: 'רגיל' }, { value: 0.2, label: 'הדוק' }],
    0, (v) => op('remove_silences', { level: v || 'off' }), 'הסרת שתיקות');
  const zoom = el('input', { type: 'range', min: 0, max: 100, value: 30, class: 'tl-zoom', 'aria-label': 'זום של הטיימליין',
    oninput: () => { setScale(8 * Math.pow(60, zoom.value / 100)); fitted = true; } });
  const tools = el('div', { class: 'tl-tools' },
    el('div', { class: 'tg' }, undoB, redoB),
    el('div', { class: 'tg' },
      btn('cut', 'פיצול', actions.split, 'S'), btn('trash', 'מחיקה', actions.remove, 'Del'), btn('copy', 'שכפול', actions.duplicate, 'Ctrl+D')),
    el('div', { class: 'tg' },
      btn('rin', 'תחילת טווח', actions.rangeIn, 'I'), btn('rout', 'סוף טווח', actions.rangeOut, 'O'), btn('cutx', 'חיתוך הטווח', actions.cutRange, 'X')),
    el('div', { class: 'tg grow' }, el('span', { class: 'tg-lbl', text: 'הסרת שתיקות' }), tighten),
    el('div', { class: 'tg' },
      el('button', { class: 'chip', type: 'button', onclick: () => op('add_track', { kind: 'video' }) }, icon('plus'), 'וידאו'),
      el('button', { class: 'chip', type: 'button', onclick: () => op('add_track', { kind: 'audio' }) }, icon('plus'), 'אודיו'),
      el('button', { class: 'chip', type: 'button', onclick: () => op('add_track', { kind: 'text' }) }, icon('plus'), 'טקסט')),
    el('div', { class: 'tg' },
      el('button', { class: 'ib sm', title: 'התאמה לרוחב', 'aria-label': 'התאמת הטיימליין לרוחב', onclick: () => { fitted = false; fit(); } }, icon('fit')), zoom));
  host.append(tools, scroll);

  const x2t = (clientX) => {
    const r = inner.getBoundingClientRect();
    return Math.max(0, (clientX - r.left - HEAD) / pps);
  };

  function setScale(v) {
    const mid = (scroll.scrollLeft + scroll.clientWidth / 2 - HEAD) / pps;
    pps = Math.max(4, Math.min(600, v));
    render();
    scroll.scrollLeft = Math.max(0, mid * pps + HEAD - scroll.clientWidth / 2);
  }

  function fit() {
    const dur = Math.max(S.derived.duration, 4);
    const room = scroll.clientWidth - HEAD - 40;
    if (room <= 0) return;
    pps = Math.max(4, Math.min(600, room / dur));
    zoom.value = String(Math.round(Math.max(0, Math.min(1, Math.log(pps / 8) / Math.log(60))) * 100));
    render();
  }

  // ----- drawing

  function drawRuler(width) {
    ruler.replaceChildren(el('div', { class: 'tl-corner', style: { width: HEAD + 'px' } }));
    const steps = [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
    const step = steps.find((s) => s * pps >= 64) || 600;
    const strip = el('div', { class: 'tl-ticks', style: { width: width + 'px' } });
    for (let t = 0; t * pps <= width; t += step) {
      const label = step < 1 ? fmt(t, true) : fmt(t);
      strip.append(el('span', { style: { left: (t * pps) + 'px' }, text: label }));
    }
    ruler.append(strip);
  }

  function waveform(canvas, it, m, w, h) {
    loadPeaks(m.id).then((peaks) => {
      if (!canvas.isConnected || !peaks.length) return;
      const cw = Math.min(3000, Math.max(1, Math.round(w)));
      canvas.width = cw;
      canvas.height = h;
      const g = canvas.getContext('2d');
      g.fillStyle = getComputedStyle(canvas).color;
      const span = Math.max(0.01, it.out - it.in);
      for (let x = 0; x < cw; x += 2) {
        const src = it.in + (x / cw) * span;
        const i = Math.min(peaks.length - 1, Math.floor((src / Math.max(m.duration, 0.01)) * peaks.length));
        const bh = Math.max(1, (peaks[i] / 100) * (h - 4));
        g.fillRect(x, (h - bh) / 2, 1, bh);
      }
    });
  }

  function clipEl(track, it) {
    const inf = info(it.id);
    if (!inf) return null;
    const w = Math.max(inf.dur * pps, 4);
    const c = el('div', { class: `clip k-${track.kind}${S.sel === it.id ? ' sel' : ''}${it.mute ? ' muted' : ''}${inf.dur <= 0 ? ' empty' : ''}`,
      dataset: { id: it.id }, style: { left: (inf.start * pps) + 'px', width: w + 'px' } });
    if (track.kind === 'text') {
      c.append(el('span', { class: 'clip-label', text: it.text || 'טקסט' }));
    } else {
      const m = media(it.media);
      const speed = it.speed || 1;
      if (track.kind === 'video') {
        if (m.kind === 'video' && m.meta && m.meta.strip) {
          c.style.backgroundImage = `url(/api/projects/${S.pid}/media/${m.id}/strip.jpg)`;
          c.style.backgroundSize = `${(m.duration / speed) * pps}px 100%`;
          c.style.backgroundPositionX = `${-(it.in / speed) * pps}px`;
        } else if (m.kind === 'image') {
          c.style.backgroundImage = `url(/api/projects/${S.pid}/media/${m.id}/thumb.jpg)`;
          c.style.backgroundSize = 'auto 100%';
        }
        // marks where words were cut out of the clip
        let acc = 0;
        for (let i = 0; i < inf.segs.length - 1; i++) {
          acc += inf.segs[i][1] - inf.segs[i][0];
          c.append(el('i', { class: 'cutmark', style: { left: ((acc / speed) * pps) + 'px' } }));
        }
        for (const k of it.zoom || []) c.append(el('i', { class: 'kf', style: { left: (k.t * pps) + 'px' }, title: `זום ×${k.s}` }));
        if (inf.trans > 0) c.append(el('i', { class: 'trans', style: { width: Math.max(8, inf.trans * pps) + 'px' }, title: 'מעבר' }));
        if (it.blend === 'screen') c.classList.add('blend');
      } else {
        const cv = el('canvas', { class: 'wave' });
        c.append(cv);
        waveform(cv, it, m, w, LANE.audio - 8);
      }
      const tags = [];
      if (Math.abs(speed - 1) > 0.01) tags.push(`${+speed.toFixed(2)}×`);
      if (it.look) tags.push('לוק');
      if (it.mute) tags.push('מושתק');
      // a clip that fades in from the previous one starts under it, so its name moves past the overlap
      const lead = inf.trans > 0 ? Math.min(Math.max(0, w - 40), inf.trans * pps) : 0;
      c.append(el('span', { class: 'clip-label', style: lead ? { left: (lead + 9) + 'px' } : {} },
        el('b', { text: it.label || m.name }), tags.length ? el('em', { text: tags.join(' · ') }) : null));
      if (!it.mute && (m.has_audio || m.kind === 'audio')) {
        c.append(el('i', { class: 'fade in', style: { left: Math.min(w - 10, (it.fade_in || 0) * pps) + 'px' }, title: 'פייד פנימה' }),
          el('i', { class: 'fade out', style: { right: Math.min(w - 10, (it.fade_out || 0) * pps) + 'px' }, title: 'פייד החוצה' }));
        if (it.fade_in > 0) c.append(el('i', { class: 'fadeshade in', style: { width: (it.fade_in * pps) + 'px' } }));
        if (it.fade_out > 0) c.append(el('i', { class: 'fadeshade out', style: { width: (it.fade_out * pps) + 'px' } }));
      }
    }
    c.append(el('i', { class: 'h l' }), el('i', { class: 'h r' }));
    return c;
  }

  function headEl(track) {
    const tb = (ic, label, active, fn) => el('button', { class: 'th' + (active ? ' on' : ''), type: 'button', title: label, 'aria-label': label, onclick: fn }, icon(ic));
    const kids = [el('b', { text: track.name })];
    if (track.kind !== 'text') kids.push(tb(track.muted ? 'volx' : 'vol', track.muted ? 'ביטול השתקה' : 'השתקת הערוץ', track.muted, () => op('set_track', { track: track.id, muted: !track.muted })));
    if (track.kind !== 'audio') kids.push(tb(track.hidden ? 'eyex' : 'eye', track.hidden ? 'הצגה' : 'הסתרת הערוץ', track.hidden, () => op('set_track', { track: track.id, hidden: !track.hidden })));
    if (!track.main) kids.push(tb('x', 'מחיקת הערוץ', false, async () => {
      if (track.items.length && !(await confirmBox('למחוק את הערוץ?', 'כל מה שנמצא בערוץ הזה יוסר מהטיימליין.', 'מחיקה'))) return;
      op('remove_track', { track: track.id });
    }));
    return el('div', { class: 'tl-head', style: { width: HEAD + 'px' } }, ...kids);
  }

  function render() {
    if (!S.derived) return;
    const d = S.derived;
    const width = Math.max(scroll.clientWidth - HEAD - 2, (d.duration + 3) * pps);
    inner.style.width = (HEAD + width) + 'px';
    drawRuler(width);
    rows.replaceChildren();
    // captions are derived from the transcript, so their lane is read-only
    const capLane = el('div', { class: 'tl-lane', style: { width: width + 'px', height: LANE.captions + 'px' } });
    if (S.doc.captions.enabled) {
      for (const cp of d.caps) {
        capLane.append(el('div', { class: 'clip k-cap', style: { left: (cp.s * pps) + 'px', width: Math.max(3, (cp.e - cp.s) * pps - 1) + 'px' }, title: cp.t,
          onclick: () => S.player.seek(cp.s + 0.01) }, el('span', { class: 'clip-label', text: cp.t })));
      }
    }
    rows.append(el('div', { class: 'tl-row k-captions' },
      el('div', { class: 'tl-head', style: { width: HEAD + 'px' } }, el('b', { text: 'כתוביות' })), capLane));
    for (const track of S.doc.tracks) {
      const lane = el('div', { class: 'tl-lane', dataset: { track: track.id, kind: track.kind, main: track.main ? '1' : '' },
        style: { width: width + 'px', height: LANE[track.kind] + 'px' } });
      for (const it of track.items) { const c = clipEl(track, it); if (c) lane.append(c); }
      rows.append(el('div', { class: `tl-row k-${track.kind}${track.main ? ' main' : ''}${track.muted ? ' muted' : ''}${track.hidden ? ' hidden' : ''}` }, headEl(track), lane));
    }
    undoB.disabled = !S.history.undo;
    redoB.disabled = !S.history.redo;
    const t = S.doc.tighten || 0;
    tighten.setValue(t ? [0.6, 0.35, 0.2].reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a)) : 0);
    movePlayhead();
    drawRange();
  }

  function movePlayhead() {
    playhead.style.transform = `translateX(${HEAD + S.time * pps}px)`;
    if (S.playing) {
      const x = HEAD + S.time * pps;
      if (x > scroll.scrollLeft + scroll.clientWidth - 60 || x < scroll.scrollLeft + HEAD) scroll.scrollLeft = Math.max(0, x - HEAD - 80);
    }
  }

  function drawRange() {
    const { a, b } = S.range;
    if (a == null && b == null) { rangeEl.hidden = true; return; }
    const lo = a == null ? b : a, hi = b == null ? a : b;
    rangeEl.hidden = false;
    rangeEl.style.left = (HEAD + Math.min(lo, hi) * pps) + 'px';
    rangeEl.style.width = Math.max(2, Math.abs(hi - lo) * pps) + 'px';
    rangeEl.classList.toggle('open', a == null || b == null);
  }

  // ----- pointer work

  const snapTime = (t, ignoreId) => {
    const marks = [0, S.time];
    for (const [id, inf] of Object.entries(S.derived.items)) {
      if (id === ignoreId) continue;
      marks.push(inf.start, inf.start + inf.dur);
    }
    let best = t, gap = SNAP / pps;
    for (const m of marks) if (Math.abs(m - t) < gap) { best = m; gap = Math.abs(m - t); }
    return best;
  };

  const laneAt = (clientY) => {
    for (const lane of rows.querySelectorAll('.tl-lane[data-track]')) {
      const r = lane.getBoundingClientRect();
      if (clientY >= r.top && clientY <= r.bottom) return lane;
    }
    return null;
  };

  const mainIndexAt = (t, ignoreId) => {
    let n = 0;
    for (const it of mainTrack().items) {
      if (it.id === ignoreId) continue;
      const inf = info(it.id);
      if (inf.start + inf.dur / 2 < t) n++;
    }
    return n;
  };

  const insertX = (index, ignoreId) => {
    const items = mainTrack().items.filter((it) => it.id !== ignoreId);
    if (!items.length) return 0;
    if (index >= items.length) { const inf = info(items[items.length - 1].id); return inf.start + inf.dur; }
    return info(items[index].id).start;
  };

  function drag(ev, onMove, onEnd) {
    const move = (e) => onMove(e);
    const up = (e) => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
      onEnd(e);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', up);
    ev.preventDefault();
  }

  rows.addEventListener('pointerdown', (ev) => {
    if (ev.button !== 0) return;
    const clip = ev.target.closest('.clip[data-id]');
    if (!clip) {
      if (ev.target.closest('.tl-head') || ev.target.closest('.k-cap')) return;
      select(null);
      S.player.seek(x2t(ev.clientX));
      drag(ev, (e) => S.player.seek(x2t(e.clientX)), () => {});
      return;
    }
    const id = clip.dataset.id;
    const found = findItem(id);
    if (!found) return;
    const { track, item: it } = found;
    const inf = info(id);
    select(id);
    for (const c of rows.querySelectorAll('.clip.sel')) c.classList.remove('sel');
    clip.classList.add('sel');
    const x0 = ev.clientX;
    const speed = it.speed || 1;
    const m = it.media ? media(it.media) : null;
    const minLen = 2 / fps();

    if (ev.target.classList.contains('fade')) {
      const isIn = ev.target.classList.contains('in');
      const start = isIn ? it.fade_in || 0 : it.fade_out || 0;
      let val = start;
      drag(ev, (e) => {
        const dx = (e.clientX - x0) / pps;
        val = Math.max(0, Math.min(inf.dur / 2, start + (isIn ? dx : -dx)));
        ev.target.style[isIn ? 'left' : 'right'] = (val * pps) + 'px';
      }, () => { if (Math.abs(val - start) > 0.01) op('set_item', { item: id, [isIn ? 'fade_in' : 'fade_out']: +val.toFixed(2) }); });
      return;
    }

    if (ev.target.classList.contains('h')) {
      const left = ev.target.classList.contains('l');
      let dt = 0;
      drag(ev, (e) => {
        dt = (e.clientX - x0) / pps;
        if (track.kind === 'text') {
          dt = left ? Math.max(-it.start, Math.min(it.dur - minLen, dt)) : Math.max(minLen - it.dur, dt);
        } else {
          const lim = m.kind === 'image' ? 3600 : m.duration;
          dt = left ? Math.max(-it.in / speed, Math.min((it.out - it.in) / speed - minLen, dt))
            : Math.max(minLen - (it.out - it.in) / speed, Math.min((lim - it.out) / speed, dt));
          if (left && !track.main) dt = Math.max(-it.start, dt);
        }
        if (left) { clip.style.left = ((inf.start + dt) * pps) + 'px'; clip.style.width = Math.max(4, (inf.dur - dt) * pps) + 'px'; }
        else clip.style.width = Math.max(4, (inf.dur + dt) * pps) + 'px';
      }, () => {
        if (Math.abs(dt) < 0.5 / fps()) { render(); return; }
        if (track.kind === 'text') {
          op('trim_item', left ? { item: id, start: +(it.start + dt).toFixed(3), duration: +(it.dur - dt).toFixed(3) } : { item: id, duration: +(it.dur + dt).toFixed(3) });
        } else if (left) {
          const args = { item: id, source_in: +(it.in + dt * speed).toFixed(3) };
          if (!track.main) args.start = +(it.start + dt).toFixed(3);
          op('trim_item', args);
        } else {
          op('trim_item', { item: id, source_out: +(it.out + dt * speed).toFixed(3) });
        }
      });
      return;
    }

    let moved = false;
    let target = null;
    drag(ev, (e) => {
      const dx = e.clientX - x0;
      if (!moved && Math.abs(dx) < 4 && Math.abs(e.clientY - ev.clientY) < 6) return;
      moved = true;
      clip.classList.add('dragging');
      const lane = laneAt(e.clientY);
      const sameKind = lane && lane.dataset.kind === track.kind ? lane : null;
      const toMain = sameKind ? sameKind.dataset.main === '1' : track.main;
      insert.hidden = true;
      if (toMain) {
        const index = mainIndexAt(x2t(e.clientX), id);
        const row = rows.querySelector('.tl-row.main .tl-lane').getBoundingClientRect();
        const base = inner.getBoundingClientRect();
        insert.hidden = false;
        insert.style.left = (HEAD + insertX(index, id) * pps - 1) + 'px';
        insert.style.top = (row.top - base.top) + 'px';
        insert.style.height = row.height + 'px';
        clip.style.transform = `translate(${dx}px, ${track.main ? 0 : e.clientY - ev.clientY}px)`;
        target = { index, track: sameKind && sameKind.dataset.track !== track.id ? sameKind.dataset.track : null };
      } else {
        const start = Math.max(0, snapTime(inf.start + dx / pps, id));
        const endSnap = snapTime(inf.start + dx / pps + inf.dur, id) - inf.dur;
        const best = Math.abs(start - (inf.start + dx / pps)) <= Math.abs(endSnap - (inf.start + dx / pps)) ? start : Math.max(0, endSnap);
        clip.style.transform = `translate(${(best - inf.start) * pps}px, ${sameKind && sameKind.dataset.track !== track.id ? e.clientY - ev.clientY : 0}px)`;
        target = { start: best, track: sameKind && sameKind.dataset.track !== track.id ? sameKind.dataset.track : null };
      }
    }, () => {
      insert.hidden = true;
      clip.classList.remove('dragging');
      if (!moved || !target) return;
      const args = { item: id };
      if (target.track) args.track = target.track;
      if (target.index != null) {
        const current = track.main ? mainTrack().items.findIndex((x) => x.id === id) : -1;
        if (!target.track && target.index === current) { render(); return; }
        args.index = target.index;
      } else {
        if (!target.track && Math.abs(target.start - inf.start) < 0.5 / fps()) { render(); return; }
        args.start = +target.start.toFixed(3);
      }
      op('move_item', args).then((r) => { if (!r) render(); });
    });
  });

  ruler.addEventListener('pointerdown', (ev) => {
    if (ev.button !== 0) return;
    S.player.seek(x2t(ev.clientX));
    drag(ev, (e) => S.player.seek(x2t(e.clientX)), () => {});
  });

  // media dragged in from the library
  rows.addEventListener('dragover', (ev) => {
    if (![...ev.dataTransfer.types].includes('text/studio-media')) return;
    const lane = laneAt(ev.clientY);
    if (lane && lane.dataset.kind !== 'text') { ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; }
  });
  rows.addEventListener('drop', (ev) => {
    const mid = ev.dataTransfer.getData('text/studio-media');
    const lane = laneAt(ev.clientY);
    if (!mid || !lane) return;
    ev.preventDefault();
    const t = x2t(ev.clientX);
    const args = { media: mid, track: lane.dataset.track };
    if (lane.dataset.main === '1') args.index = mainIndexAt(t, null); else args.at = +snapTime(t, null).toFixed(3);
    op('add_clip', args).then((r) => { if (r && r.item) select(r.item); });
  });

  scroll.addEventListener('wheel', (ev) => {
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    fitted = true;
    setScale(pps * (ev.deltaY < 0 ? 1.15 : 1 / 1.15));
    zoom.value = String(Math.round(Math.max(0, Math.min(1, Math.log(pps / 8) / Math.log(60))) * 100));
  }, { passive: false });

  on('state', () => { if (!fitted && S.derived.duration > 0) fit(); else render(); });
  on('time', movePlayhead);
  on('range', drawRange);
  on('select', () => {
    for (const c of rows.querySelectorAll('.clip[data-id]')) c.classList.toggle('sel', c.dataset.id === S.sel);
  });
  const ro = new ResizeObserver(() => { if (!fitted && S.derived) fit(); else render(); });
  ro.observe(scroll);
  return { destroy: () => ro.disconnect(), fit: () => { fitted = false; fit(); } };
}
