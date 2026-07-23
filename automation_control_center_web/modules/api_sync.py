from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd
import requests


API_URL = "https://jsonplaceholder.typicode.com/users"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def fetch_api_records() -> list[dict[str, Any]]:
    response = requests.get(API_URL, timeout=20)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError("API response must be a list.")

    return data


def normalize_api_records(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean_rows = []
    invalid_rows = []
    seen_emails = set()

    for item in records:
        address = item.get("address", {})
        company = item.get("company", {})

        row = {
            "source_id": str(item.get("id", "")).strip(),
            "name": str(item.get("name", "")).strip().title(),
            "username": str(item.get("username", "")).strip(),
            "email": str(item.get("email", "")).strip().lower(),
            "phone": str(item.get("phone", "")).strip(),
            "website": str(item.get("website", "")).strip(),
            "city": str(address.get("city", "")).strip() if isinstance(address, dict) else "",
            "company": str(company.get("name", "")).strip() if isinstance(company, dict) else "",
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        errors = []

        if not row["source_id"]:
            errors.append("Missing source id")
        if not row["name"]:
            errors.append("Missing name")
        if not EMAIL_RE.match(row["email"]):
            errors.append("Invalid email")
        if row["email"] in seen_emails:
            errors.append("Duplicate email")

        if errors:
            row["error"] = "; ".join(errors)
            invalid_rows.append(row)
            continue

        seen_emails.add(row["email"])
        clean_rows.append(row)

    return pd.DataFrame(clean_rows), pd.DataFrame(invalid_rows)
