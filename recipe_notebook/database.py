"""
database.py - everything that touches the SQLite file.

SQLite is a database that lives in a single file, built into Python
(the `sqlite3` module) - nothing to install. Nothing else in the app
writes SQL; the pages just call the functions below. If you ever move to
a different database (needed for free hosting - see README), this is the
only file you'd rewrite.
"""
import json
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config


@contextmanager
def get_conn():
    """Open the database, hand it out, then always commit and close.

    `@contextmanager` + `yield` lets us write `with get_conn() as conn:`
    elsewhere. Code after `yield` runs when the `with` block finishes.
    """
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the tables if they don't exist yet (safe to run every start)."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS folders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                icon_file  TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recipes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id        INTEGER NOT NULL
                                 REFERENCES folders(id) ON DELETE CASCADE,
                name             TEXT NOT NULL,
                ingredients_json TEXT NOT NULL,
                steps_json       TEXT NOT NULL,
                transcript       TEXT NOT NULL DEFAULT '',
                summary          TEXT NOT NULL DEFAULT '',
                created_at       TEXT NOT NULL
            );
            """
        )
        # Older database files may lack newer columns - add any that are missing.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(recipes)")]
        for column in ("transcript", "summary"):
            if column not in cols:
                conn.execute(f"ALTER TABLE recipes ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------- Folders --------------------------------------------------------
def create_folder(name: str) -> int:
    """Create a folder and permanently assign it a random colour image."""
    icons = config.list_folder_icons()          # however many exist right now
    icon = random.choice(icons) if icons else ""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO folders (name, icon_file, created_at) VALUES (?, ?, ?)",
            (name.strip(), icon, _now()),
        )
        return cur.lastrowid


def list_folders() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT f.*, COUNT(r.id) AS recipe_count
               FROM folders f LEFT JOIN recipes r ON r.folder_id = f.id
               GROUP BY f.id ORDER BY f.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_folder(folder_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
    return dict(row) if row else None


# ---------- Recipes --------------------------------------------------------
def save_recipe(folder_id: int, name: str, ingredients: list[str], steps: list[str],
                transcript: str = "", summary: str = "") -> int:
    # Lists can't be stored in a database column directly, so we turn them
    # into JSON text ("serialising") and turn them back on the way out.
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO recipes
               (folder_id, name, ingredients_json, steps_json, transcript, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (folder_id, name, json.dumps(ingredients), json.dumps(steps),
             transcript, summary, _now()),
        )
        return cur.lastrowid


def _recipe_from_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["ingredients"] = json.loads(d.pop("ingredients_json"))
    d["steps"] = json.loads(d.pop("steps_json"))
    return d


def list_recipes(folder_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE folder_id = ? ORDER BY created_at DESC",
            (folder_id,),
        ).fetchall()
    return [_recipe_from_row(r) for r in rows]


def get_recipe(recipe_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    return _recipe_from_row(row) if row else None


def delete_recipe(recipe_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
