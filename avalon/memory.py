import sqlite3
import threading
from pathlib import Path

class Memory:
    """Only completed turns are stored; context never starts mid-turn."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._db:
            self._db.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
            self._db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)")
            self._db.execute("CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, user TEXT NOT NULL, assistant TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")

    def append(self, user, assistant):
        with self._lock, self._db:
            self._db.execute("INSERT INTO turns(user, assistant) VALUES (?, ?)", (user, assistant))
            self._db.execute("DELETE FROM turns WHERE id NOT IN (SELECT id FROM turns ORDER BY id DESC LIMIT 500)")

    def context(self, turns=10, char_budget=18000):
        with self._lock:
            rows = self._db.execute("SELECT user, assistant FROM turns ORDER BY id DESC LIMIT ?", (turns,)).fetchall()
        selected, used = [], 0
        for user, assistant in rows:
            size = len(user) + len(assistant)
            if used + size > char_budget:
                break
            selected.append((user, assistant))
            used += size
        return [message for user, assistant in reversed(selected) for message in (
            {"role": "user", "content": user}, {"role": "assistant", "content": assistant})]

    def clear(self):
        with self._lock, self._db:
            self._db.execute("DELETE FROM turns")

    def add_note(self, text):
        with self._lock, self._db:
            cursor = self._db.execute("INSERT INTO notes(text) VALUES (?)", (text,))
            return cursor.lastrowid

    def notes(self):
        with self._lock:
            return self._db.execute("SELECT id, text FROM notes ORDER BY id DESC LIMIT 50").fetchall()

    def add_task(self, text):
        with self._lock, self._db:
            cursor = self._db.execute("INSERT INTO tasks(text) VALUES (?)", (text,))
            return cursor.lastrowid

    def tasks(self):
        with self._lock:
            return self._db.execute("SELECT id, text FROM tasks WHERE done=0 ORDER BY id LIMIT 50").fetchall()

    def complete_task(self, task_id):
        with self._lock, self._db:
            cursor = self._db.execute("UPDATE tasks SET done=1 WHERE id=? AND done=0", (task_id,))
            return cursor.rowcount == 1

    def close(self):
        with self._lock:
            self._db.close()
