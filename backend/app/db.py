"""
Document metadata in SQLite (stdlib — no extra dependency, works offline).

Replaces the old documents_metadata.json, whose read-modify-write cycle
could lose records when two uploads finished at the same time.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Model the pre-SQLite versions of the app indexed every document with (CPU path).
LEGACY_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

COLUMNS = (
    "id", "owner_id", "filename", "page_count", "chunk_count", "size_bytes",
    "uploaded_at", "status", "stage", "progress", "error", "file_path",
    "store_path", "embed_model",
)


def db_path() -> Path:
    return Path(settings.vector_store_dir) / "docchat.db"


@contextmanager
def connect():
    Path(settings.vector_store_dir).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables, import legacy JSON metadata, fail interrupted jobs."""
    with connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id           TEXT PRIMARY KEY,
                owner_id     TEXT NOT NULL,
                filename     TEXT NOT NULL,
                page_count   INTEGER NOT NULL DEFAULT 0,
                chunk_count  INTEGER NOT NULL DEFAULT 0,
                size_bytes   INTEGER NOT NULL DEFAULT 0,
                uploaded_at  TEXT NOT NULL,
                status       TEXT NOT NULL,
                stage        TEXT,
                progress     INTEGER NOT NULL DEFAULT 0,
                error        TEXT,
                file_path    TEXT,
                store_path   TEXT NOT NULL,
                embed_model  TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_id)")
        # A restart while a PDF was being processed leaves it stuck forever.
        conn.execute(
            "UPDATE documents SET status='error', stage=NULL, "
            "error='Processing was interrupted. Please upload the file again.' "
            "WHERE status='processing'"
        )
    _migrate_legacy_json()


def _migrate_legacy_json() -> None:
    legacy = Path(settings.vector_store_dir) / "documents_metadata.json"
    if not legacy.exists():
        return
    try:
        records = json.loads(legacy.read_text())
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read legacy metadata file %s", legacy)
        return

    with connect() as conn:
        for rec in records.values():
            conn.execute(
                "INSERT OR IGNORE INTO documents (id, owner_id, filename, page_count, "
                "chunk_count, size_bytes, uploaded_at, status, progress, file_path, "
                "store_path, embed_model) VALUES (?, 'local', ?, ?, ?, ?, ?, 'ready', 100, ?, ?, ?)",
                (
                    rec["id"], rec["filename"], rec.get("page_count", 0),
                    rec.get("chunk_count", 0), rec.get("size_bytes", 0),
                    rec["uploaded_at"], rec.get("file_path"), rec["store_path"],
                    LEGACY_EMBED_MODEL,
                ),
            )
    legacy.rename(legacy.with_suffix(".json.migrated"))
    logger.info("Imported %d documents from %s", len(records), legacy.name)


def insert(record: dict) -> None:
    cols = ", ".join(record)
    marks = ", ".join("?" for _ in record)
    with connect() as conn:
        conn.execute(f"INSERT INTO documents ({cols}) VALUES ({marks})", tuple(record.values()))


def update(doc_id: str, **fields) -> None:
    unknown = set(fields) - set(COLUMNS)
    if unknown:
        raise ValueError(f"Unknown columns: {unknown}")
    assignments = ", ".join(f"{k}=?" for k in fields)
    with connect() as conn:
        conn.execute(f"UPDATE documents SET {assignments} WHERE id=?", (*fields.values(), doc_id))


def get(doc_id: str, owner_id: str | None = None) -> dict | None:
    sql, args = "SELECT * FROM documents WHERE id=?", [doc_id]
    if owner_id is not None:
        sql += " AND owner_id=?"
        args.append(owner_id)
    with connect() as conn:
        row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def list_for(owner_id: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM documents", []
    if owner_id is not None:
        sql += " WHERE owner_id=?"
        args.append(owner_id)
    sql += " ORDER BY uploaded_at DESC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def count_for(owner_id: str) -> int:
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM documents WHERE owner_id=?", (owner_id,)
        ).fetchone()[0]


def delete(doc_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))


def expired(ttl_hours: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE uploaded_at < ? AND status != 'processing'", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]
