"""Background jobs with progress the browser can poll."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from .media import Cancelled


class UserError(Exception):
    """An error whose message is safe and useful to show to the person editing."""


class Job:
    def __init__(self, kind: str, project: str | None):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.project = project
        self.status = "queued"
        self.progress = 0.0
        self.message = ""
        self.error: str | None = None
        self.result = None
        self.created = time.time()
        self.cancel = threading.Event()

    def update(self, progress: float | None = None, message: str | None = None) -> None:
        if self.cancel.is_set():
            raise Cancelled()
        if progress is not None:
            self.progress = max(0.0, min(1.0, float(progress)))
        if message is not None:
            self.message = message

    def public(self) -> dict:
        return {"id": self.id, "kind": self.kind, "project": self.project, "status": self.status,
                "progress": round(self.progress, 4), "message": self.message, "error": self.error,
                "result": self.result if self.status == "done" else None}


class JobManager:
    def __init__(self, workers: int = 2):
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, kind: str, project: str | None, fn, *args) -> Job:
        job = Job(kind, project)
        with self._lock:
            self._jobs[job.id] = job
            self._trim()
        self._pool.submit(self._run, job, fn, args)
        return job

    def _run(self, job: Job, fn, args) -> None:
        if job.cancel.is_set():
            job.status = "cancelled"
            return
        job.status = "running"
        try:
            job.result = fn(job, *args)
            job.progress = 1.0
            job.status = "done"
        except Cancelled:
            job.status = "cancelled"
        except UserError as e:
            job.error = str(e)
            job.status = "error"
        except Exception as e:  # noqa: BLE001 - surfaced to the UI
            traceback.print_exc()
            job.error = f"{type(e).__name__}: {e}"[:600]
            job.status = "error"

    def _trim(self) -> None:
        if len(self._jobs) > 200:
            done = sorted((j for j in self._jobs.values() if j.status not in ("queued", "running")),
                          key=lambda j: j.created)
            for j in done[: len(self._jobs) - 150]:
                self._jobs.pop(j.id, None)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self, project: str, kind: str | None = None) -> list[Job]:
        return [j for j in self._jobs.values()
                if j.project == project and j.status in ("queued", "running")
                and (kind is None or j.kind == kind)]

    def cancel_project(self, project: str) -> None:
        for j in self.active(project):
            j.cancel.set()


jobs = JobManager()
