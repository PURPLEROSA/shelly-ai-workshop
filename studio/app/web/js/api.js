// Talking to the local server.

export async function api(path, { method = 'GET', body, signal } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method, signal,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new Error('אין חיבור לסטודיו. בודקים שהוא עדיין רץ במחשב.');
  }
  if (!res.ok) {
    let msg = `שגיאה (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
    } catch { /* not JSON */ }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  const type = res.headers.get('content-type') || '';
  return type.includes('json') ? res.json() : res;
}

export function uploadVideo(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/projects?name=' + encodeURIComponent(file.name));
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300 && data) resolve(data);
      else reject(new Error((data && typeof data.detail === 'string' && data.detail) || `ההעלאה נכשלה (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error('ההעלאה נקטעה. בודקים את החיבור ומנסים שוב.'));
    xhr.send(file);
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Follow a background job until it ends. `alive` lets a screen stop polling when it closes.
export async function followJob(id, onTick, alive = () => true) {
  let misses = 0;
  while (alive()) {
    let job;
    try {
      job = await api('/api/jobs/' + id);
      misses = 0;
    } catch (e) {
      if (e.status === 404 || ++misses > 8) return { status: 'error', error: 'המשימה אבדה. ייתכן שהסטודיו הופעל מחדש.' };
      await sleep(1200);
      continue;
    }
    onTick && onTick(job);
    if (job.status !== 'queued' && job.status !== 'running') return job;
    await sleep(700);
  }
  return null;
}
