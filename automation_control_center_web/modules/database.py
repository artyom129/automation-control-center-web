from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path("output")
DATABASE_FILE = OUTPUT_DIR / "automation_center.db"


def connect() -> sqlite3.Connection:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DATABASE_FILE)


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

        conn.commit()


def save_run_log(task_name: str, status: str, records_processed: int, details: str = "") -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO run_logs (task_name, status, records_processed, details, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task_name,
                status,
                records_processed,
                details,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()


def save_clean_records(df: pd.DataFrame, source: str) -> None:
    if df.empty:
        return

    with connect() as conn:
        for record in df.to_dict(orient="records"):
            conn.execute(
                """
                INSERT INTO clean_records (source, record_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    source,
                    str(record),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
        conn.commit()


def get_recent_runs(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
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
