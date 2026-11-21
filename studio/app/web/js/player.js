// The preview engine. It plays the timeline with ordinary <video>, <audio> and
// <img> elements: the main track, B-roll and overlays above it, audio items,
// captions and titles, all kept in step with one clock.
import { S, emit, findItem, info, media, srcAt, tlAt, playUrl } from './store.js';

const LEAD = 0.02;      // jump this early at a cut so the removed sound is never heard
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export function zoomAt(keys, t) {
  if (!keys || !keys.length) return { s: 1, x: 0.5, y: 0.5 };
  if (t <= keys[0].t) return keys[0];
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (t < b.t) {
      const u = (t - a.t) / Math.max(b.t - a.t, 1e-4);
      const e = u * u * (3 - 2 * u);
      return { s: a.s + (b.s - a.s) * e, x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e };
    }
  }
  return keys[keys.length - 1];
}

function seekTo(node, t) {
  try { node.currentTime = Math.max(0, t); } catch { /* not ready yet */ }
}

export class Player {
  constructor(frame) {
    this.frame = frame;
    const layer = (cls) => { const d = document.createElement('div'); d.className = cls; frame.append(d); return d; };
    this.layerMain = layer('pl-layer');
    this.layerOver = layer('pl-layer');
    this.capBands = [layer('pl-cap'), layer('pl-cap')];
    this.layerTitles = layer('pl-layer pl-titles');
    this.audioHost = layer('pl-audio');
    this.slots = new Map();
    this.bind = {};            // main item id -> slot key
    this.images = new Map();
    this.shown = [null, null];
    this.titleEls = new Map();
    this.ctx = null;
    this.t = 0;
    this.playing = false;
    this.stall = 0;
    this.capW = 540;
    this.last = performance.now();
    this.alive = true;
    const loop = (now) => { if (!this.alive) return; this.tick(now); this.raf = requestAnimationFrame(loop); };
    this.raf = requestAnimationFrame(loop);
  }

  destroy() {
    this.alive = false;
    cancelAnimationFrame(this.raf);
    for (const key of [...this.slots.keys()]) this.drop(key);
    if (this.ctx) this.ctx.close().catch(() => {});
  }

  // ----- transport

  play() {
    if (this.playing || !S.derived || S.derived.duration <= 0) return;
    if (this.t >= S.derived.duration - 0.05) this.t = 0;
    if (!this.ctx) {
      try {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        for (const s of this.slots.values()) this.wire(s);
      } catch { this.ctx = null; }
    }
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
    this.playing = true;
    this.stall = 0;
    S.playing = true;
    emit('play');
  }

  pause() {
    if (!this.playing) return;
    this.playing = false;
    S.playing = false;
    for (const s of this.slots.values()) if (s.kind !== 'image' && !s.el.paused) s.el.pause();
    emit('play');
  }

  toggle() { if (this.playing) this.pause(); else this.play(); }

  seek(t) {
    this.t = clamp(t, 0, S.derived ? S.derived.duration : 0);
    this.stall = 0;
    this.sync();
    this.publish();
  }

  publish() {
    if (S.time !== this.t) { S.time = this.t; emit('time'); }
  }

  // ----- elements

  slot(key, mid, layer) {
    let s = this.slots.get(key);
    const m = media(mid);
    const kind = m.kind === 'image' ? 'image' : (layer === 'audio' ? 'audio' : 'video');
    if (s && (s.mid !== mid || s.kind !== kind)) { this.drop(key); s = null; }
    if (!s) {
      const node = kind === 'image' ? new Image() : document.createElement(kind);
      if (kind === 'image') {
        node.src = `/api/projects/${S.pid}/media/${mid}/thumb.jpg`;
        node.draggable = false;
      } else {
        node.preload = 'auto';
        node.playsInline = true;
        node.src = playUrl(mid);
      }
      const wrap = document.createElement('div');
      wrap.className = 'pl-slot';
      wrap.append(node);
      (layer === 'main' ? this.layerMain : layer === 'over' ? this.layerOver : this.audioHost).append(wrap);
      s = { key, wrap, el: node, mid, kind, gain: null, vol: -1 };
      this.slots.set(key, s);
      this.wire(s);
    }
    return s;
  }

  wire(s) {
    if (!this.ctx || s.kind === 'image' || s.gain) return;
    try {
      const src = this.ctx.createMediaElementSource(s.el);
      s.gain = this.ctx.createGain();
      src.connect(s.gain).connect(this.ctx.destination);
      s.vol = -1;
    } catch { s.gain = null; }
  }

  drop(key) {
    const s = this.slots.get(key);
    if (!s) return;
    if (s.kind !== 'image') { try { s.el.pause(); s.el.removeAttribute('src'); s.el.load(); } catch { /* ignore */ } }
    s.wrap.remove();
    this.slots.delete(key);
  }

  volume(s, v) {
    if (s.kind === 'image' || Math.abs(v - s.vol) < 0.004) return;
    s.vol = v;
    if (s.gain) s.gain.gain.value = v; else s.el.volume = clamp(v, 0, 1);
  }

  // Keep a slave element (anything but the clock's master) on its target time.
  follow(s, want, speed, active) {
    const node = s.el;
    if (s.kind === 'image') return;
    if (this.playing && active) {
      if (node.paused) { seekTo(node, want); node.playbackRate = speed; node.play().catch(() => {}); return; }
      if (node.seeking) return;
      const drift = node.currentTime - want;
      if (Math.abs(drift) > 0.3) seekTo(node, want + 0.05 * speed);
      else node.playbackRate = clamp(speed * (1 - clamp(drift, -0.08, 0.08)), 0.1, 8);
    } else {
      if (!node.paused) node.pause();
      if (!node.seeking && Math.abs(node.currentTime - want) > 0.03) seekTo(node, want);
    }
  }

  visual(s, it, local) {
    const m = media(s.mid);
    const { w: W, h: H } = S.derived.frame;
    const mw = m.width || W, mh = m.height || H;
    const k = Math.max(W / mw, H / mh);
    const cw = mw * k, ch = mh * k;
    const draft = S.zoomDraft && S.zoomDraft.item === it.id ? S.zoomDraft : null;
    const z = draft || zoomAt(it.zoom, local);
    const x0 = clamp(W / 2 - z.x * cw * z.s, W - cw * z.s, 0);
    const y0 = clamp(H / 2 - z.y * ch * z.s, H - ch * z.s, 0);
    const st = s.el.style;
    st.width = (cw / W * 100) + '%';
    st.height = (ch / H * 100) + '%';
    st.transform = `translate(${(x0 / cw * 100).toFixed(3)}%, ${(y0 / ch * 100).toFixed(3)}%) scale(${z.s.toFixed(4)})`;
    const look = it.look ? `url(#look-${it.look})` : '';
    if (st.filter !== look) st.filter = look;
  }

  // ----- the clock

  tick(now) {
    const dt = Math.min(0.25, (now - this.last) / 1000);
    this.last = now;
    if (!S.derived || !S.doc) return;
    const cw = this.capWidth();
    if (cw !== this.capW) { this.capW = cw; this.shown = [null, null]; }
    if (this.playing) this.advance(dt);
    this.sync();
    this.publish();
  }

  activeMain(t) {
    const out = [];
    for (const id of S.derived.order) {
      const inf = info(id);
      if (inf.dur > 0 && t >= inf.start - 1e-6 && t < inf.start + inf.dur - 1e-6) out.push(id);
    }
    return out;
  }

  advance(dt) {
    const d = S.derived;
    const active = this.activeMain(this.t);
    const id = active[0];
    const s = id ? this.slots.get(this.bind[id]) : null;
    if (s && s.kind === 'video') {
      const node = s.el;
      const inf = info(id);
      const it = findItem(id).item;
      if (!node.paused && !node.seeking && node.readyState >= 2) {
        this.stall = 0;
        const src = node.currentTime;
        let k = -1;
        for (let i = 0; i < inf.segs.length; i++) if (inf.segs[i][0] <= src + 1e-3) k = i;
        if (k < 0) {
          seekTo(node, inf.segs[0][0]);
        } else if (src >= inf.segs[k][1] - LEAD * it.speed) {
          if (k + 1 < inf.segs.length) {
            seekTo(node, inf.segs[k + 1][0]);
            this.t = Math.max(this.t, tlAt(id, inf.segs[k + 1][0]));
          } else {
            this.t = inf.start + inf.dur;   // this clip is done; the next tick moves on
          }
        } else {
          const mapped = tlAt(id, src);
          this.t = Math.abs(mapped - this.t) < 0.5 ? Math.max(this.t, mapped) : mapped;
        }
      } else if (node.paused) {
        this.t += dt * 0;   // about to start: sync() will play it
        this.stall += dt;
        if (this.stall > 0.5) this.t += dt;
      } else {
        this.stall += dt;   // waiting for the picture, but never hang
        if (this.stall > 0.8) this.t += dt;
      }
    } else {
      this.t += dt;         // images, or audio running past the end of the main track
    }
    if (this.t >= d.duration - 1e-3) {
      this.t = d.duration;
      this.pause();
    }
  }

  sync() {
    const d = S.derived;
    // at the very end keep showing the last frame instead of going black
    const t = Math.min(this.t, Math.max(0, d.duration - 0.02));
    const order = d.order;
    const active = this.activeMain(t);
    const master = active[0];

    // --- main track: bind up to two slots
    const wanted = [...active];
    const lastIdx = active.length ? order.indexOf(active[active.length - 1]) : -1;
    for (let i = lastIdx + 1; i < order.length; i++) {
      const inf = info(order[i]);
      if (inf.dur <= 0) continue;
      if (inf.start - t < 1.5 && wanted.length < 2) wanted.push(order[i]);
      break;
    }
    const used = new Set();
    const next = {};
    for (const id of wanted) if (this.bind[id] && !used.has(this.bind[id])) { next[id] = this.bind[id]; used.add(this.bind[id]); }
    for (const id of wanted) {
      if (next[id]) continue;
      const mid = findItem(id).item.media;
      const free = ['mA', 'mB'].filter((k) => !used.has(k));
      const same = free.find((k) => this.slots.get(k) && this.slots.get(k).mid === mid);
      const key = same || free[0];
      if (!key) continue;
      next[id] = key;
      used.add(key);
    }
    this.bind = next;
    for (const key of ['mA', 'mB']) {
      const s = this.slots.get(key);
      if (s && !used.has(key)) { s.wrap.style.opacity = '0'; if (s.kind !== 'image' && !s.el.paused) s.el.pause(); }
    }
    let bg = '';
    for (const id of wanted) {
      const { item: it, track } = findItem(id);
      const inf = info(id);
      const s = this.slot(next[id], it.media, 'main');
      const on = active.includes(id);
      const local = clamp(t - inf.start, 0, inf.dur);
      const want = srcAt(id, Math.max(t, inf.start));
      if (s.kind === 'video') {
        const node = s.el;
        if (this.playing && on) {
          node.playbackRate = it.speed;
          if (node.paused) { seekTo(node, want); node.play().catch(() => {}); }
          else if (id !== master) this.follow(s, want, it.speed, true);
        } else {
          this.follow(s, want, it.speed, false);
        }
      }
      this.visual(s, it, local);
      const ws = s.wrap.style;
      ws.zIndex = String(order.indexOf(id) + 1);
      let opacity = on ? 1 : 0, transform = '', clip = '';
      const k = order.indexOf(id);
      const nxt = order[k + 1] ? info(order[k + 1]) : null;
      // this clip is arriving through a transition
      if (on && inf.trans > 0 && local < inf.trans) {
        const u = local / inf.trans;
        const type = (it.transition || {}).type || 'fade';
        if (type === 'fade' || type === 'zoomin') opacity = u;
        else if (type === 'fadeblack' || type === 'fadewhite') { opacity = Math.max(0, 2 * u - 1); bg = type === 'fadewhite' ? '#fff' : '#000'; }
        else if (type === 'slideleft') transform = `translateX(${(1 - u) * 100}%)`;
        else if (type === 'slideright') transform = `translateX(${-(1 - u) * 100}%)`;
        else if (type === 'wipeleft') clip = `inset(0 0 0 ${(1 - u) * 100}%)`;
        else if (type === 'circleopen') clip = `circle(${u * 75}% at 50% 50%)`;
      }
      // this clip is leaving through the next clip's transition
      if (on && nxt && nxt.trans > 0 && t >= nxt.start) {
        const u = clamp((t - nxt.start) / nxt.trans, 0, 1);
        const type = (findItem(order[k + 1]).item.transition || {}).type || 'fade';
        if (type === 'fadeblack' || type === 'fadewhite') opacity = Math.max(0, 1 - 2 * u);
        else if (type === 'slideleft') transform = `translateX(${-u * 100}%)`;
        else if (type === 'slideright') transform = `translateX(${u * 100}%)`;
        else if (type === 'zoomin') { transform = `scale(${1 + u * 0.8})`; opacity = 1 - u; }
      }
      ws.opacity = String(opacity);
      ws.transform = transform;
      ws.clipPath = clip;
      let vol = 0;
      if (on && !it.mute && !track.muted) {
        const fi = Math.max(it.fade_in || 0, inf.trans || 0);
        const fo = Math.max(it.fade_out || 0, nxt ? nxt.trans || 0 : 0);
        vol = it.volume * (fi > 0 ? clamp(local / fi, 0, 1) : 1) * (fo > 0 ? clamp((inf.dur - local) / fo, 0, 1) : 1);
      }
      this.volume(s, vol);
    }
    this.frame.style.background = bg || '';

    // --- free tracks: B-roll, overlays, audio
    const keep = new Set(['mA', 'mB']);
    let z = 0;
    for (let ti = S.doc.tracks.length - 1; ti >= 0; ti--) {
      const track = S.doc.tracks[ti];
      if (track.main || track.kind === 'text') continue;
      z += 1;
      for (const it of track.items) {
        const inf = info(it.id);
        if (!inf || inf.dur <= 0) continue;
        const end = inf.start + inf.dur;
        if (t < inf.start - 1.2 || t > end + 0.3) continue;
        const isVideo = track.kind === 'video';
        if (isVideo && track.hidden) continue;
        const key = (isVideo ? 'o:' : 'a:') + it.id;
        keep.add(key);
        const s = this.slot(key, it.media, isVideo ? 'over' : 'audio');
        const on = t >= inf.start && t < end;
        const local = clamp(t - inf.start, 0, inf.dur);
        this.follow(s, srcAt(it.id, Math.max(t, inf.start)), it.speed || 1, on);
        if (isVideo) {
          this.visual(s, it, local);
          const ws = s.wrap.style;
          ws.zIndex = String(z);
          ws.opacity = on ? String(it.opacity == null ? 1 : it.opacity) : '0';
          ws.mixBlendMode = it.blend === 'screen' ? 'screen' : '';
        }
        let vol = 0;
        if (on && !it.mute && !track.muted) {
          vol = (it.volume == null ? 1 : it.volume)
            * (it.fade_in > 0 ? clamp(local / it.fade_in, 0, 1) : 1)
            * (it.fade_out > 0 ? clamp((inf.dur - local) / it.fade_out, 0, 1) : 1);
        }
        this.volume(s, vol);
      }
    }
    for (const key of [...this.slots.keys()]) if (!keep.has(key)) this.drop(key);

    this.captions(t);
    this.titles(t);
  }

  // ----- captions and titles

  capWidth() {
    const px = (this.frame.clientWidth || 360) * Math.min(window.devicePixelRatio || 1, 2);
    for (const w of [360, 540, 720, 1080]) if (px <= w * 1.15) return w;
    return 1080;
  }

  image(key) {
    const id = key + '@' + this.capW;
    let img = this.images.get(id);
    if (!img) {
      img = new Image();
      img.decoding = 'async';
      img.alt = '';
      img.draggable = false;
      img.src = `/api/cap/${key}.png?w=${this.capW}`;
      this.images.set(id, img);
      if (this.images.size > 3000) for (const k of [...this.images.keys()].slice(0, 800)) this.images.delete(k);
    }
    return img;
  }

  // Load the caption pictures around the playhead ahead of time.
  preload() {
    const d = S.derived;
    if (!d || !S.doc.captions.enabled) return;
    const token = (this.preloadToken = {});
    const keys = [];
    const seen = new Set();
    for (const list of [d.cues, d.cues2]) {
      let start = list.findIndex((c) => c.e > this.t);
      if (start < 0) start = 0;
      for (let n = 0; n < list.length; n++) {
        const k = list[(start + n) % list.length].k;
        if (!seen.has(k)) { seen.add(k); keys.push(k); }
      }
    }
    let i = 0;
    const pump = () => {
      if (!this.alive || this.preloadToken !== token || i >= keys.length) return;
      const img = this.image(keys[i++]);
      if (img.complete) { pump(); return; }
      img.addEventListener('load', pump, { once: true });
      img.addEventListener('error', pump, { once: true });
    };
    setTimeout(() => { for (let n = 0; n < 4; n++) pump(); }, 150);
  }

  captions(t) {
    const d = S.derived;
    const lists = [d.cues, d.cues2];
    const bands = [d.band, d.band2];
    for (let b = 0; b < 2; b++) {
      let key = '';
      if (S.doc.captions.enabled) {
        const cues = lists[b];
        let lo = 0, hi = cues.length - 1;
        while (lo <= hi) {
          const mid = (lo + hi) >> 1;
          if (cues[mid].e <= t) lo = mid + 1; else if (cues[mid].s > t) hi = mid - 1; else { key = cues[mid].k; break; }
        }
      }
      const host = this.capBands[b];
      host.style.top = (bands[b].top * 100) + '%';
      host.style.height = (bands[b].height * 100) + '%';
      if (key === this.shown[b]) continue;
      this.shown[b] = key;
      if (key) host.replaceChildren(this.image(key)); else host.replaceChildren();
    }
  }

  titles(t) {
    const live = new Set();
    for (const ti of S.derived.titles) {
      const end = ti.start + ti.dur;
      if (t < ti.start || t >= end) continue;
      live.add(ti.id);
      let node = this.titleEls.get(ti.id);
      if (!node || node.dataset.k !== ti.k + '@' + this.capW) {
        if (node) node.remove();
        node = document.createElement('div');
        node.className = 'pl-title';
        node.dataset.k = ti.k + '@' + this.capW;
        node.append(this.image(ti.k));
        this.layerTitles.append(node);
        this.titleEls.set(ti.id, node);
      }
      node.style.top = (ti.top * 100) + '%';
      node.style.height = (ti.height * 100) + '%';
      const f = Math.min(ti.fade, ti.dur / 2);
      node.style.opacity = f > 0.01 ? String(clamp(Math.min((t - ti.start) / f, (end - t) / f), 0, 1)) : '1';
    }
    for (const [id, node] of this.titleEls) if (!live.has(id)) { node.remove(); this.titleEls.delete(id); }
  }

  // Called when the project changed.
  refresh() {
    this.shown = [null, null];
    if (S.derived && this.t > S.derived.duration) this.t = S.derived.duration;
    this.preload();
  }
}
