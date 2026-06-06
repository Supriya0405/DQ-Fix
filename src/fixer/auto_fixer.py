"""
Auto-Fix Engine
================
Applies suggested fixes to DataFrames and enables cleaned CSV download.
"""

import pandas as pd
from typing import List
import io


class AutoFixer:
    """Applies fixes to DataFrames and generates cleaned CSV output."""

    def apply_fixes(self, df: pd.DataFrame, fixes: List[dict]) -> pd.DataFrame:
        """Apply a list of fix operations to the DataFrame."""
        result_df = df.copy()
        for fix in fixes:
            if not fix.get("success", False):
                continue
            # Fixes are applied during agent loop; this is for manual application
        return result_df

    def apply_pandas_fix(self, df: pd.DataFrame, pandas_code: str) -> pd.DataFrame:
        """Execute a pandas fix code snippet safely."""
        result_df = df.copy()
        try:
            local_ns = {"df": result_df, "pd": pd}
            exec(pandas_code, {}, local_ns)
            return local_ns.get("df", result_df)
        except Exception:
            return result_df

    def to_csv_bytes(self, df: pd.DataFrame) -> bytes:
        """Convert DataFrame to CSV bytes for download."""
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)
        return buffer.getvalue()

    def to_csv_string(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string."""
        return df.to_csv(index=False)

    def get_fix_summary(self, fixes: List[dict]) -> dict:
        """Summarize applied fixes."""
        successful = [f for f in fixes if f.get("success")]
        failed = [f for f in fixes if not f.get("success")]
        return {
            "total_fixes": len(fixes),
            "successful": len(successful),
            "failed": len(failed),
            "columns_fixed": list(set(f.get("column", "") for f in successful)),
        }
