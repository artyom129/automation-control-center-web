from __future__ import annotations

import re

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TITLE_COLUMNS = ["name", "first_name", "last_name", "company", "city"]


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Return (clean rows, invalid rows, stats).

    Text is trimmed, names are title-cased, emails are lower-cased, duplicate
    rows are removed (first one wins, an ``id`` column is ignored), and rows with a malformed email
    go to the invalid frame with an ``error`` column.
    """
    total_rows = len(df)
    df = normalize_column_names(df)

    # pandas 3 stores text as the dedicated "str" dtype. Checking both dtypes
    # explicitly avoids the deprecated select_dtypes(include="object") shortcut.
    for column in df.columns:
        if is_object_dtype(df[column]) or is_string_dtype(df[column]):
            df[column] = df[column].fillna("").astype(str).str.strip()

    for column in TITLE_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype(str).str.title()

    if "email" in df.columns:
        df["email"] = df["email"].astype(str).str.lower()

    # A row repeated under a new "id" is still a duplicate, so the id column
    # is left out of the comparison.
    compare_columns = [c for c in df.columns if c != "id"] or list(df.columns)
    before = len(df)
    df = df.drop_duplicates(subset=compare_columns)
    duplicates_removed = before - len(df)

    if "email" in df.columns:
        invalid_mask = ~df["email"].map(lambda value: bool(EMAIL_RE.match(value)))
    else:
        invalid_mask = pd.Series(False, index=df.index)

    invalid_df = df[invalid_mask].copy()
    clean_df = df[~invalid_mask].copy()

    if not invalid_df.empty:
        invalid_df["error"] = "Invalid email"

    stats = {
        "total_rows": total_rows,
        "clean_rows": len(clean_df),
        "invalid_rows": len(invalid_df),
        "duplicates_removed": duplicates_removed,
    }

    return clean_df.reset_index(drop=True), invalid_df.reset_index(drop=True), stats
