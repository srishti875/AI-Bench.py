"""SQLite database for accounts, interview results and personal notes."""

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "data" / "aibench.db"
ATTACHMENTS_DIR = BASE_DIR / "data" / "note_attachments"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
MAX_NAME_LENGTH = 80


def get_connection():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
    """Create the database schema first, then safely migrate older databases."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'Student / Fresher',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                subject TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                score REAL NOT NULL,
                questions INTEGER NOT NULL,
                transcript TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                attachment_name TEXT DEFAULT '',
                attachment_path TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        note_columns = {row[1] for row in connection.execute("PRAGMA table_info(notes)").fetchall()}
        if "attachment_name" not in note_columns:
            connection.execute("ALTER TABLE notes ADD COLUMN attachment_name TEXT DEFAULT ''")
        if "attachment_path" not in note_columns:
            connection.execute("ALTER TABLE notes ADD COLUMN attachment_path TEXT DEFAULT ''")

        result_columns = {row[1] for row in connection.execute("PRAGMA table_info(results)").fetchall()}
        if "transcript" not in result_columns:
            connection.execute("ALTER TABLE results ADD COLUMN transcript TEXT NOT NULL DEFAULT '[]'")


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def _check_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_user(username, password, name, level):
    username = username.strip()
    name = " ".join(name.strip().split())
    if not username or not password or not name:
        return False, "Please fill in all required fields."
    if not USERNAME_RE.fullmatch(username):
        return False, "Username must be 3–30 characters using letters, numbers, dots, underscores or hyphens."
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name must be {MAX_NAME_LENGTH} characters or fewer."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, name, level, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, _hash_password(password), name, level, datetime.now().isoformat(timespec="seconds")),
            )
        return True, "Account created. You can log in now."
    except sqlite3.IntegrityError:
        return False, "That username is already registered."


def authenticate_user(username, password):
    with get_connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),)).fetchone()
    return dict(user) if user and _check_password(password, user["password_hash"]) else None


def get_user(user_id):
    with get_connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(user) if user else None


def update_user(user_id, name, level):
    name = " ".join(name.strip().split())
    if not name:
        return False, "Name cannot be empty."
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name must be {MAX_NAME_LENGTH} characters or fewer."
    with get_connection() as connection:
        connection.execute("UPDATE users SET name = ?, level = ? WHERE id = ?", (name, level, user_id))
    return True, "Profile updated."


def save_result(user_id, subject, difficulty, score, question_count, transcript=None):
    payload = json.dumps(transcript or [], ensure_ascii=False)
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO results (user_id, date, subject, difficulty, score, questions, transcript) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), subject, difficulty, max(0, min(10, float(score))), max(0, int(question_count)), payload),
        )


def load_results(user_id):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, date, subject, difficulty, score, questions, transcript FROM results WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        try:
            item["transcript"] = json.loads(item.get("transcript") or "[]")
        except json.JSONDecodeError:
            item["transcript"] = []
        output.append(item)
    return output


def create_note(user_id, title, content, attachment=None):
    title = title.strip()
    content = content.strip()

    if not title or not content:
        return False, "Add a title and some note content."

    attachment_name = ""
    attachment_path = ""

    if attachment is not None:
        attachment_name = attachment.name
        safe_name = Path(attachment_name).name
        attachment_path = str(ATTACHMENTS_DIR / safe_name)

        with open(attachment_path, "wb") as file:
            file.write(attachment.getvalue())

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO notes
            (user_id, title, content, updated_at, attachment_name, attachment_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title,
                content,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                attachment_name,
                attachment_path,
            ),
        )

    return True, "Note saved."

 
def load_notes(user_id):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, content, updated_at, attachment_name, attachment_path FROM notes WHERE user_id = ? ORDER BY id DESC",
            (user_id,)
            ).fetchall()
    return [dict(row) for row in rows]


def update_note(user_id, note_id, title, content):
    title = title.strip()
    content = content.strip()
    if not title or not content:
        return False, "Add a title and some note content."
    with get_connection() as connection:
        connection.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (title, content, datetime.now().strftime("%Y-%m-%d %H:%M"), note_id, user_id),
        )
    return True, "Note updated."


def delete_note(user_id, note_id):
    with get_connection() as connection:
        connection.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
    return True


init_database()
