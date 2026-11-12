from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATABASE_FILE = OUTPUT_DIR / "automation_center.db"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database, commit on success, and always close the file.

    The path is read on every call, so tests can point DATABASE_FILE elsewhere.
    """
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            yield conn


def create_tables() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                records_processed INTEGER NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clean_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def save_run_log(task_name: str, status: str, records_processed: int, details: str = "") -> None:
    create_tables()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO run_logs (task_name, status, records_processed, details, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_name, status, int(records_processed), details, now()),
        )


def save_clean_records(df: pd.DataFrame, source: str) -> None:
    """Store every row as a JSON document (valid JSON, unlike a Python repr)."""
    if df.empty:
        return

    create_tables()
    created_at = now()
    rows = [
        (source, json.dumps(record, ensure_ascii=False, default=str), created_at)
        for record in df.to_dict(orient="records")
    ]
    with connect() as conn:
        conn.executemany(
            "INSERT INTO clean_records (source, record_json, created_at) VALUES (?, ?, ?)",
            rows,
        )


def get_recent_runs(limit: int = 20) -> list[dict[str, object]]:
    create_tables()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT task_name, status, records_processed, details, created_at
            FROM run_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_run_summary() -> dict[str, int]:
    create_tables()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_runs,
                COALESCE(SUM(status = 'Success'), 0) AS successful,
                COALESCE(SUM(status != 'Success'), 0) AS failed,
                COALESCE(SUM(CASE WHEN status = 'Success'
                                  THEN records_processed ELSE 0 END), 0) AS records
            FROM run_logs
            """
        ).fetchone()

    return dict(row)
