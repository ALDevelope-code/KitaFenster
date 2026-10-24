import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from threading import Lock


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def secure_equals(left, right):
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return hmac.compare_digest(left.encode("utf-8", "surrogatepass"), right.encode("utf-8", "surrogatepass"))


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
    return salt + ":" + value


def password_matches(password, encoded):
    try:
        return hmac.compare_digest(password_hash(password, encoded.split(":")[0]), encoded)
    except (UnicodeEncodeError, ValueError):
        return False


def set_admin(db, username, password, *, only_if_changed=False):
    if not username or len(username) > 80:
        raise ValueError("Benutzername erforderlich; maximal 80 Zeichen")
    with db.connect() as connection:
        row = connection.execute("SELECT data FROM auth WHERE key='admin'").fetchone()
        if only_if_changed and row:
            account = json.loads(row[0])
            if account["username"] == username and password_matches(password, account["password"]):
                return False
        connection.execute(
            "INSERT INTO auth VALUES ('admin',?) ON CONFLICT(key) DO UPDATE SET data=excluded.data",
            (json.dumps({"username": username, "password": password_hash(password)}),),
        )
        connection.execute("DELETE FROM sessions")
    return True


class Limiter:
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = Lock()

    def blocked(self, key, count=10, seconds=300):
        with self.lock:
            now = time.monotonic()
            queue = self.entries[key]
            while queue and queue[0] <= now - seconds:
                queue.popleft()
            return len(queue) >= count

    def record_failure(self, key, seconds=300):
        with self.lock:
            now = time.monotonic()
            queue = self.entries[key]
            while queue and queue[0] <= now - seconds:
                queue.popleft()
            queue.append(now)
            if len(self.entries) > 5000:
                self.entries = defaultdict(
                    deque, {k: v for k, v in self.entries.items() if v and v[-1] > now - seconds}
                )

    def reset(self, key):
        with self.lock:
            self.entries.pop(key, None)
