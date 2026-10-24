"""Coordinate prepared files across server threads and backup processes."""

import errno
import os
import threading
import time
from functools import lru_cache
from pathlib import Path

from player.cache import ASSET_ID


class AssetLock:
    def __init__(self, path):
        self.path = path
        self.thread_lock = threading.RLock()
        self.depth = 0
        self.stream = None

    def __enter__(self):
        self.thread_lock.acquire()
        try:
            if self.depth == 0:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.stream = self.path.open("a+b")
                try:
                    if os.name == "nt":
                        import msvcrt

                        if self.stream.seek(0, os.SEEK_END) == 0:
                            self.stream.write(b"\0")
                            self.stream.flush()
                        self.stream.seek(0)
                        while True:
                            try:
                                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                                break
                            except OSError as error:
                                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                                    raise
                                time.sleep(0.05)
                    else:
                        import fcntl

                        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX)
                except BaseException:
                    self.stream.close()
                    self.stream = None
                    raise
            self.depth += 1
            return self
        except BaseException:
            self.thread_lock.release()
            raise

    def __exit__(self, *exc):
        try:
            self.depth -= 1
            if self.depth == 0:
                # Closing the descriptor also releases the OS lock after an exception
                # or process exit. Never unlink this shared lock file.
                self.stream.close()
                self.stream = None
        finally:
            self.thread_lock.release()


@lru_cache(maxsize=None)
def _asset_lock(directory):
    return AssetLock(directory / ".assets.lock")


def asset_lock(directory):
    return _asset_lock(Path(directory).resolve())


def referenced_assets(db):
    ids = set()
    for snapshot in db.all("snapshot"):
        ids.update(snapshot.get("photos", []))
        ids.update(snapshot.get("plan", []))
    for document in db.all("document"):
        ids.update(document.get("assets", []))
    return ids


def required_asset_files(db, directory):
    """Reject incomplete backups/restores instead of publishing missing references."""
    paths = []
    for id in sorted(referenced_assets(db)):
        if not ASSET_ID.fullmatch(id):
            raise ValueError("Sicherung enthält eine ungültige Bildreferenz")
        path = directory / (id + ".jpg")
        descriptor = db.get("asset", id)
        if not descriptor or not path.is_file() or path.stat().st_size != descriptor.get("bytes"):
            raise ValueError("Sicherung unvollständig: Eine verwendete Bilddatei fehlt oder ist beschädigt")
        paths.append(path)
    return paths
