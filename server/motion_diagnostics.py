"""Short-lived diagnostics; no per-second database writes or permanent motion history."""

import threading
import time


class MotionDiagnostics:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.sessions = {}

    def _prune(self, now):
        self.sessions = {key: value for key, value in self.sessions.items() if value["until"] > now}

    def start(self, device_id):
        with self.lock:
            now = self.clock()
            self._prune(now)
            session = self.sessions.setdefault(device_id, {"sample": None, "received": None})
            session["until"] = now + 30

    def report(self, device_id, sample):
        with self.lock:
            now = self.clock()
            self._prune(now)
            session = self.sessions.get(device_id)
            if session and sample is not None:
                session.update(sample=sample, received=now)
            return session is not None

    def snapshot(self, device_id):
        with self.lock:
            now = self.clock()
            self._prune(now)
            session = self.sessions.get(device_id)
            if not session:
                return {"active": False, "sample": None, "age_seconds": None}
            sample = session["sample"]
            age = now - session["received"] + sample["sample_age_seconds"] if sample else None
            return {"active": True, "sample": sample, "age_seconds": age}

    def discard(self, device_id):
        with self.lock:
            self.sessions.pop(device_id, None)
