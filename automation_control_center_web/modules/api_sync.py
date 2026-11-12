from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd
import requests

API_URL = "https://jsonplaceholder.typicode.com/users"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def fetch_api_records(api_url: str = API_URL, timeout_seconds: float = 20) -> list[dict[str, Any]]:
    response = requests.get(api_url, timeout=timeout_seconds)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError("API response must be a list.")

    return data


def text(value: Any) -> str:
    """str(None) would give the word 'None', so missing values become ''."""
    return "" if value is None else str(value).strip()


def nested(item: dict[str, Any], field: str, key: str) -> str:
    value = item.get(field)
    return text(value.get(key)) if isinstance(value, dict) else ""


def normalize_api_records(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split API records into (clean, invalid) frames.

    Invalid rows keep an ``error`` column that lists every problem found.
    """
    clean_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    seen_ids: set[str] = set()
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in records:
        if not isinstance(item, dict):
            invalid_rows.append({"source_id": "", "error": "Record is not an object"})
            continue

        row = {
            "source_id": text(item.get("id")),
            "name": text(item.get("name")).title(),
            "username": text(item.get("username")),
            "email": text(item.get("email")).lower(),
            "phone": text(item.get("phone")),
            "website": text(item.get("website")),
            "city": nested(item, "address", "city"),
            "company": nested(item, "company", "name"),
            "synced_at": synced_at,
        }

        errors = []
        if not row["source_id"]:
            errors.append("Missing source id")
        elif row["source_id"] in seen_ids:
            errors.append("Duplicate source id")
        if not row["name"]:
            errors.append("Missing name")
        if not EMAIL_RE.match(row["email"]):
            errors.append("Invalid email")
        elif row["email"] in seen_emails:
            errors.append("Duplicate email")

        if errors:
            row["error"] = "; ".join(errors)
            invalid_rows.append(row)
            continue

        seen_ids.add(row["source_id"])
        seen_emails.add(row["email"])
        clean_rows.append(row)

    return pd.DataFrame(clean_rows), pd.DataFrame(invalid_rows)
