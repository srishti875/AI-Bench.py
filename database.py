"""SQLite database for users, profiles and interview results."""

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "data" / "aibench.db"

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
MAX_NAME_LENGTH = 80


def get_connection():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def _check_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
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
                """
                INSERT INTO users
                    (username, password_hash, name, level, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    _hash_password(password),
                    name,
                    level,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        return True, "Account created. You can log in now."
    except sqlite3.IntegrityError:
        return False, "That username is already registered."


def authenticate_user(username, password):
    username = username.strip()
    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()

    if user and _check_password(password, user["password_hash"]):
        return dict(user)
    return None


def get_user(user_id):
    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(user) if user else None


def update_user(user_id, name, level):
    name = " ".join(name.strip().split())
    if not name:
        return False, "Name cannot be empty."
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name must be {MAX_NAME_LENGTH} characters or fewer."

    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET name = ?, level = ? WHERE id = ?",
            (name, level, user_id),
        )
    return True, "Profile updated."


def save_result(user_id, subject, difficulty, score, question_count):
    score = max(0.0, min(10.0, float(score)))
    question_count = max(0, int(question_count))

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO results
                (user_id, date, subject, difficulty, score, questions)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                subject,
                difficulty,
                round(score, 1),
                question_count,
            ),
        )


def load_results(user_id):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT date, subject, difficulty, score, questions
            FROM results
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


init_database()
