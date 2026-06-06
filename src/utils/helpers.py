"""
Helper Utilities
================
Shared functions used across readers, validators, and the Streamlit UI.

Usage:
    from src.utils.helpers import (
        get_dataset_summary,
        format_file_size,
        get_column_profile,
        calculate_health_score,
    )
"""

import pandas as pd
from typing import Optional


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string (KB, MB, GB)."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def get_dataset_summary(df: pd.DataFrame) -> dict:
    """
    Generate a comprehensive summary of a DataFrame.

    Returns
    -------
    dict with keys:
        - total_rows, total_columns, total_cells
        - null_count, null_percentage
        - duplicated_rows
        - numeric_columns, text_columns, date_columns
        - memory_usage_mb
    """
    total_cells = df.shape[0] * df.shape[1]
    null_count = int(df.isnull().sum().sum())

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "total_cells": total_cells,
        "null_count": null_count,
        "null_percentage": round((null_count / total_cells * 100), 2) if total_cells > 0 else 0,
        "duplicated_rows": int(df.duplicated().sum()),
        "numeric_columns": numeric_cols,
        "text_columns": text_cols,
        "date_columns": date_cols,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
    }


def get_column_profile(df: pd.DataFrame, column: str) -> dict:
    """
    Profile a single column with statistics.

    Returns
    -------
    dict with:
        - dtype, null_count, unique_count
        - For numeric: min, max, mean, median, std
        - For text: top_values, max_length, min_length
    """
    col = df[column]
    profile = {
        "column": column,
        "dtype": str(col.dtype),
        "null_count": int(col.isnull().sum()),
        "null_percentage": round(col.isnull().sum() / len(df) * 100, 2),
        "unique_count": int(col.nunique()),
    }

    if pd.api.types.is_numeric_dtype(col):
        profile.update({
            "min": col.min(),
            "max": col.max(),
            "mean": round(col.mean(), 2),
            "median": col.median(),
            "std": round(col.std(), 2),
        })
    elif pd.api.types.is_object_dtype(col) or pd.api.types.is_string_dtype(col):
        non_null = col.dropna()
        profile.update({
            "top_values": col.value_counts().head(5).to_dict(),
            "max_length": int(non_null.str.len().max()) if len(non_null) > 0 else 0,
            "min_length": int(non_null.str.len().min()) if len(non_null) > 0 else 0,
        })

    return profile


def calculate_health_score(
    total_rows: int,
    null_count: int,
    duplicated_rows: int,
    failed_validations: int = 0,
) -> int:
    """
    Calculate a data health score from 0 to 100.

    Formula:
        - Start at 100
        - Deduct for null percentage
        - Deduct for duplicate percentage
        - Deduct for validation failure percentage
    """
    if total_rows == 0:
        return 0

    score = 100

    # Deduct for nulls (max -40 points)
    null_pct = (null_count / (total_rows * 10)) * 100  # rough estimate
    score -= min(40, null_pct * 2)

    # Deduct for duplicates (max -20 points)
    dup_pct = (duplicated_rows / total_rows) * 100
    score -= min(20, dup_pct * 2)

    # Deduct for validation failures (max -40 points)
    if failed_validations > 0:
        fail_pct = (failed_validations / total_rows) * 100
        score -= min(40, fail_pct * 2)

    return max(0, int(score))


def safe_sample(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Return up to n rows, handling small DataFrames gracefully."""
    return df.head(min(n, len(df)))
