// The editor's shared state: the project document, what is derived from it,
// the selection and the playhead. Every edit goes through `op`, which is the
// same server operation that MCP tools call.
import { api, followJob } from './api.js';
import { toast } from './ui.js';

export const S = {
  pid: null, alive: false, doc: null, derived: null, words: {}, history: { undo: 0, redo: 0 },
  jobs: [], sel: null, time: 0, playing: false, range: { a: null, b: null }, pending: 0,
  player: null, listeners: {}, zoomDraft: null,
};

export function on(evt, fn) { (S.listeners[evt] = S.listeners[evt] || []).push(fn); }
export function emit(evt, data) { for (const fn of S.listeners[evt] || []) { try { fn(data); } catch (e) { console.error(e); } } }

export function reset(pid) {
  Object.assign(S, { pid, alive: true, doc: null, derived: null, words: {}, history: { undo: 0, redo: 0 }, jobs: [],
    sel: null, time: 0, playing: false, range: { a: null, b: null }, pending: 0, player: null, listeners: {}, zoomDraft: null });
}

export function applyState(st) {
  for (const [mid, m] of Object.entries(st.doc.media)) {
    if (m.words) S.words[mid] = m.words;
    else if (!S.words[mid] || S.words[mid].length !== m.word_count) delete S.words[mid];
  }
  for (const mid of Object.keys(S.words)) if (!st.doc.media[mid]) delete S.words[mid];
  S.doc = st.doc;
  S.derived = st.derived;
  S.history = st.history || S.history;
  if (st.jobs) S.jobs = st.jobs;
  if (S.sel && !findItem(S.sel)) S.sel = null;
  emit('state');
}

export async function refresh() {
  if (!S.alive) return;
  const pid = S.pid;
  const st = await api('/api/projects/' + pid);
  if (S.alive && S.pid === pid) applyState(st);
}

// Run one operation on the server. Returns its result, or null if it failed (a toast explains why).
export async function op(name, args = {}, { coalesce, silent } = {}) {
  if (!S.alive) return null;
  S.pending++;
  try {
    const r = await api(`/api/projects/${S.pid}/ops`, { method: 'POST', body: { op: name, args, coalesce } });
    if (r.doc && S.alive) applyState(r);
    return r.result || {};
  } catch (e) {
    if (!silent) toast(e.message, { error: true });
    return null;
  } finally {
    S.pending--;
  }
}

// Follow a background job, then reload the project. `onDone` gets the job's result.
export async function track(jobId, onTick, onDone) {
  const job = await followJob(jobId, (j) => { onTick && onTick(j); }, () => S.alive);
  if (!job || !S.alive) return null;
  if (job.status === 'error') toast(job.error || 'הפעולה נכשלה.', { error: true });
  await refresh().catch(() => {});
  if (job.status === 'done' && onDone) onDone(job.result);
  return job;
}

export function findItem(id) {
  if (!S.doc) return null;
  for (const track of S.doc.tracks) {
    const index = track.items.findIndex((it) => it.id === id);
    if (index >= 0) return { track, index, item: track.items[index] };
  }
  return null;
}

export const mainTrack = () => S.doc.tracks.find((t) => t.main);
export const media = (mid) => S.doc.media[mid];
export const info = (id) => S.derived.items[id];
export const fps = () => S.derived.fps[0] / S.derived.fps[1];
export const playUrl = (mid) => `/api/projects/${S.pid}/media/${mid}/play`;

export function select(id) {
  if (S.sel === id) return;
  S.sel = id;
  S.zoomDraft = null;
  emit('select');
}

// ----- time mapping for one item (mirrors compose.ItemMap on the server)

export function srcAt(id, t) {
  const inf = info(id);
  const it = findItem(id).item;
  if (!inf || !inf.segs.length) return 0;
  const speed = it.speed || 1;
  let pos = Math.max(0, (t - inf.start) * speed);
  for (const [a, b] of inf.segs) {
    if (pos <= b - a) return a + pos;
    pos -= b - a;
  }
  return inf.segs[inf.segs.length - 1][1];
}

export function tlAt(id, src) {
  const inf = info(id);
  const it = findItem(id).item;
  if (!inf || !inf.segs.length) return inf ? inf.start : 0;
  const speed = it.speed || 1;
  let acc = 0;
  for (const [a, b] of inf.segs) {
    if (src < a) break;
    if (src <= b) { acc += src - a; return Math.min(inf.start + inf.dur, inf.start + acc / speed); }
    acc += b - a;
  }
  return Math.min(inf.start + inf.dur, inf.start + acc / speed);
}

export function covers(id, src) {
  const inf = info(id);
  return !!inf && inf.segs.some(([a, b]) => src >= a && src < b);
}

// The main-track item playing at time t (the later one during a transition).
export function mainAt(t) {
  let found = null;
  for (const id of S.derived.order) {
    const inf = info(id);
    if (inf.dur > 0 && inf.start <= t + 1e-6) found = id;
  }
  return found;
}

export function clampTime(t) { return Math.max(0, Math.min(S.derived ? S.derived.duration : 0, t)); }
