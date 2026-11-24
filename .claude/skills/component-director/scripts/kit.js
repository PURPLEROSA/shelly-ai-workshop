/* kit:start — helpers a self-contained piece inlines. No dependencies. Source: component-director/scripts/kit.js */
const K = (() => {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  // Remap x from a..b to c..d, clamped. map(p, .2, .6) is "the part of p between 20% and 60%, as 0..1".
  const map = (x, a, b, c = 0, d = 1) => c + (d - c) * clamp((x - a) / (b - a || 1e-9));
  const smooth = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const gauss = (d, sigma) => Math.exp(-(d * d) / (2 * sigma * sigma));
  // Seeded random: the same piece looks the same on every load and in every screenshot.
  const rand = (seed = 1) => () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);

  // A damped spring stepped at a fixed 1/120 s, so it feels the same at 60, 120 or 30 fps.
  // z is the damping ratio: 1 arrives without overshoot, 0.7 overshoots a hair, below 0.4 rings.
  function spring(x = 0, { k = 180, z = 1, eps = 5e-4 } = {}) {
    const s = {
      x, v: 0, to: x, k, z,
      step(dt) {
        const c = 2 * s.z * Math.sqrt(s.k);
        for (let t = Math.min(dt, 0.1); t > 1e-6; t -= 1 / 120) {
          const h = Math.min(t, 1 / 120);
          s.v += (-s.k * (s.x - s.to) - c * s.v) * h;
          s.x += s.v * h;
        }
        if (Math.abs(s.x - s.to) < eps && Math.abs(s.v) < eps * 20) { s.x = s.to; s.v = 0; return false; }
        return true;
      },
      snap(v = s.to) { s.x = s.to = v; s.v = 0; },
    };
    return s;
  }

  // One requestAnimationFrame loop per piece. tick(dt, t) returns false when nothing is moving and the
  // loop goes to sleep; call wake() from any input. It also sleeps while the piece is off screen or the
  // tab is hidden, and picks up where it left off.
  function loop(root, tick) {
    let raf = 0, last = 0, want = false, seen = true;
    const frame = (now) => {
      raf = 0;
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 1 / 60;
      last = now;
      want = tick(dt, now / 1000) !== false;
      if (want && seen && !document.hidden) raf = requestAnimationFrame(frame); else last = 0;
    };
    const wake = () => { want = true; if (!raf && seen && !document.hidden) raf = requestAnimationFrame(frame); };
    const io = new IntersectionObserver(([e]) => { seen = e.isIntersecting; if (seen && want) wake(); }, { rootMargin: '64px' });
    io.observe(root);
    const vis = () => { if (!document.hidden && want) wake(); };
    document.addEventListener('visibilitychange', vis);
    return { wake, stop() { cancelAnimationFrame(raf); raf = 0; want = false; io.disconnect(); document.removeEventListener('visibilitychange', vis); } };
  }

  // Mouse, touch and pen through one path, with pointer capture and a release velocity in px/s measured
  // over the last 90 ms. Coordinates are local to el. Set touch-action in CSS on el (pan-y for a
  // horizontal drag) or the browser will scroll instead. Returns an unsubscribe function.
  function drag(el, on) {
    let id = null, hist = [], x0 = 0, y0 = 0;
    const pt = (e) => { const r = el.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, h: r.height }; };
    const down = (e) => {
      if (id !== null || (e.pointerType === 'mouse' && e.button !== 0)) return;
      id = e.pointerId; el.setPointerCapture(id);
      const p = pt(e); x0 = p.x; y0 = p.y; hist = [{ ...p, t: e.timeStamp }];
      on.start?.({ ...p, e });
    };
    const move = (e) => {
      if (e.pointerId !== id) return;
      const p = pt(e); hist.push({ ...p, t: e.timeStamp });
      while (hist.length > 2 && e.timeStamp - hist[0].t > 90) hist.shift();
      on.move?.({ ...p, dx: p.x - x0, dy: p.y - y0, e });
    };
    const up = (e) => {
      if (e.pointerId !== id) return;
      id = null;
      const p = pt(e), a = hist[0], b = hist[hist.length - 1], dt = (b.t - a.t) / 1000;
      const stale = e.timeStamp - b.t > 60;                  // held still before letting go: no throw
      const vx = dt > 0.005 && !stale ? (b.x - a.x) / dt : 0, vy = dt > 0.005 && !stale ? (b.y - a.y) / dt : 0;
      on.end?.({ ...p, dx: p.x - x0, dy: p.y - y0, vx, vy, e });
    };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    return () => { el.removeEventListener('pointerdown', down); el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); };
  }

  // Keep a canvas sharp: size its backing store to its CSS box times the device pixel ratio (capped at 2).
  function fit(canvas, onSize) {
    const ro = new ResizeObserver(() => {
      const r = canvas.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(r.width * d)); canvas.height = Math.max(1, Math.round(r.height * d));
      onSize?.(r.width, r.height, d);
    });
    ro.observe(canvas);
    return () => ro.disconnect();
  }

  const rm = window.matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = () => rm.matches;

  // Split text so each letter (or each word) can move alone, without breaking right-to-left text, line
  // wrapping or screen readers. A word and its punctuation stay on one line; every word keeps its own
  // direction, so a Latin word or "16:30" inside a Hebrew sentence is not reversed. The readable text
  // stays in the page for assistive tech. Never split Arabic or other joined scripts by letter: pass 'word'.
  function split(el, by = 'grapheme') {
    const text = el.textContent, lang = el.closest('[lang]')?.lang || undefined, S = 'Segmenter' in Intl;
    const letters = (s) => (S ? [...new Intl.Segmenter(lang, { granularity: 'grapheme' }).segment(s)].map((x) => x.segment) : [...s]);
    const words = (s) => (S ? [...new Intl.Segmenter(lang, { granularity: 'word' }).segment(s)].map((x) => ({ s: x.segment, word: !!x.isWordLike })) : [{ s, word: true }]);
    const rtl = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/;
    const mk = (css, txt) => { const n = document.createElement('span'); if (css) n.style.cssText = css; if (txt) n.textContent = txt; return n; };
    const sr = mk('position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap', text);
    const box = mk();
    box.setAttribute('aria-hidden', 'true');
    const out = [];
    for (const chunk of text.split(/(\s+)/)) {
      if (!chunk) continue;
      if (/^\s+$/.test(chunk)) { box.append(document.createTextNode(chunk)); continue; }
      if (by === 'word') { const w = mk('display:inline-block;white-space:nowrap', chunk); out.push(w); box.append(w); continue; }
      // group: no line break inside. core: first word to last word, in its own direction. Punctuation before
      // and after the core follows the sentence, so the full stop after a Latin word lands on the correct side.
      const group = mk('white-space:nowrap'), parts = words(chunk);
      const first = parts.findIndex((x) => x.word), last = parts.length - 1 - [...parts].reverse().findIndex((x) => x.word);
      let core = null;
      parts.forEach(({ s, word }, k) => {
        const inCore = first >= 0 && k >= first && k <= last;
        if (inCore && !core) { core = mk(); core.dir = rtl.test(parts.slice(first, last + 1).map((x) => x.s).join('')) ? 'rtl' : 'ltr'; group.append(core); }
        let into = inCore ? core : group;
        if (word) { const w = mk('display:inline-block;white-space:nowrap'); w.dir = rtl.test(s) ? 'rtl' : 'ltr'; into.append(w); into = w; }
        for (const g of letters(s)) { const n = mk('display:inline-block', g); into.append(n); out.push(n); }
      });
      box.append(group);
    }
    el.textContent = '';
    el.append(sr, box);
    return out;
  }

  return { clamp, lerp, map, smooth, gauss, rand, spring, loop, drag, fit, reduced, onReduced: (f) => rm.addEventListener('change', f), split };
})();
/* kit:end */
