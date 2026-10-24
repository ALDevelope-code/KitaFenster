import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4


def uid():
    return uuid4().hex


class Database:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS entities(kind TEXT, id TEXT, data TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS auth(key TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, csrf TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS pairing(code TEXT PRIMARY KEY, device_id TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS device_tokens(token TEXT PRIMARY KEY, device_id TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, device_id TEXT, kind TEXT,
                    created REAL, acked INTEGER DEFAULT 0);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def all(self, kind):
        with self.connect() as db:
            return [
                json.loads(r[0])
                for r in db.execute("SELECT data FROM entities WHERE kind=? ORDER BY id", (kind,))
            ]

    def get(self, kind, id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM entities WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def get_many(self, kind, ids):
        ids = list(set(ids))
        result = {}
        with self.connect() as db:
            for offset in range(0, len(ids), 400):
                chunk = ids[offset : offset + 400]
                query = (
                    "SELECT id,data FROM entities WHERE kind=? AND id IN ("
                    + ",".join("?" for _ in chunk)
                    + ")"
                )
                for row in db.execute(query, [kind, *chunk]):
                    result[row["id"]] = json.loads(row["data"])
        return result

    @staticmethod
    def write(db, kind, obj):
        db.execute(
            "INSERT INTO entities VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (kind, obj["id"], json.dumps(obj, ensure_ascii=False)),
        )

    def put(self, kind, obj):
        with self.connect() as db:
            self.write(db, kind, obj)
        return obj

    def mutate(self, kind, id, changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM entities WHERE kind=? AND id=?", (kind, id)).fetchone()
            if row is None:
                return None
            obj = json.loads(row[0])
            obj.update(changes)
            self.write(db, kind, obj)
        return obj

    def delete(self, kind, id):
        with self.connect() as db:
            db.execute("DELETE FROM entities WHERE kind=? AND id=?", (kind, id))
