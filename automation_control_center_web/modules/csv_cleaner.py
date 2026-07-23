from __future__ import annotations

import re
from typing import Any

import pandas as pd


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    total_rows = len(df)
    df = normalize_column_names(df)

    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].fillna("").astype(str).str.strip()

    for column in ["name", "first_name", "last_name", "company", "city"]:
        if column in df.columns:
            df[column] = df[column].astype(str).str.title()

    if "email" in df.columns:
        df["email"] = df["email"].astype(str).str.lower()

    invalid_mask = pd.Series(False, index=df.index)
    errors = pd.Series("", index=df.index, dtype="object")

    if "email" in df.columns:
        invalid_email = ~df["email"].apply(lambda value: bool(EMAIL_RE.match(str(value))))
        invalid_mask = invalid_mask | invalid_email
        errors.loc[invalid_email] += "Invalid email; "

    before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before - len(df)

    invalid_df = df[invalid_mask.loc[df.index]].copy()
    clean_df = df[~invalid_mask.loc[df.index]].copy()

    if not invalid_df.empty:
        invalid_df["error"] = errors.loc[invalid_df.index].str.strip()

    stats = {
        "total_rows": total_rows,
        "clean_rows": len(clean_df),
        "invalid_rows": len(invalid_df),
        "duplicates_removed": duplicates_removed,
    }

    return clean_df.reset_index(drop=True), invalid_df.reset_index(drop=True), stats
