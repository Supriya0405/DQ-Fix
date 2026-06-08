"""
Parquet Reader Module
=====================
Reads Parquet files into Pandas DataFrames using PyArrow engine.

Usage:
    from src.readers.parquet_reader import ParquetReader

    reader = ParquetReader()
    df, info = reader.read("data.parquet")
"""

import pandas as pd
import os


class ParquetReader:
    """Reads and validates Parquet files into Pandas DataFrames."""

    def read(self, file_path: str = None, file_buffer=None) -> tuple:
        """
        Read a Parquet file and return a DataFrame + metadata dict.

        Parameters
        ----------
        file_path : str, optional
            Path to a Parquet file on disk.
        file_buffer : file-like, optional
            Uploaded file buffer (from Streamlit's file_uploader).

        Returns
        -------
        tuple (pd.DataFrame, dict)
            DataFrame and a metadata dictionary with:
            - rows, columns, column_names, dtypes, null_count, file_size
        """
        # ── Validate Input ────────────────────────────────────────────────
        if file_path is None and file_buffer is None:
            raise ValueError("Provide either file_path or file_buffer.")

        if file_path is not None and not os.path.exists(file_path):
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        # ── Read Parquet ─────────────────────────────────────────────────
        try:
            if file_buffer is not None:
                file_buffer.seek(0)
                df = pd.read_parquet(file_buffer, engine="pyarrow")
            else:
                df = pd.read_parquet(file_path, engine="pyarrow")
        except Exception as e:
            error_msg = str(e).lower()
            if "not a parquet file" in error_msg or "magic" in error_msg:
                raise ValueError(
                    "The file does not appear to be a valid Parquet file. "
                    "Please upload a .parquet file."
                )
            raise ValueError(f"Error reading Parquet file: {e}")

        if df.empty:
            raise ValueError("The Parquet file contains no data rows.")

        # ── Build Metadata ────────────────────────────────────────────────
        info = self._build_metadata(df, file_path)

        return df, info

    def _build_metadata(self, df: pd.DataFrame, file_path: str) -> dict:
        """Build a metadata dictionary summarizing the DataFrame."""
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0

        return {
            "file_name": os.path.basename(file_path) if file_path else "uploaded_file.parquet",
            "file_size_bytes": file_size,
            "format": "parquet",
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_count": int(df.isnull().sum().sum()),
            "null_per_column": {
                col: int(df[col].isnull().sum()) for col in df.columns
            },
            "duplicated_rows": int(df.duplicated().sum()),
        }

    def to_csv(self, df: pd.DataFrame, output_path: str) -> str:
        """Convert a Parquet DataFrame to CSV for preview/download."""
        df.to_csv(output_path, index=False)
        return output_path


# ── Quick Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config.settings import SAMPLE_DATA_DIR

    # Convert our sample CSV to Parquet for testing
    sample_csv = os.path.join(SAMPLE_DATA_DIR, "valid_customers.csv")
    sample_parquet = os.path.join(SAMPLE_DATA_DIR, "test_valid.parquet")

    print("Creating test Parquet file from valid_customers.csv...")
    df_csv = pd.read_csv(sample_csv)
    df_csv.to_parquet(sample_parquet, engine="pyarrow", index=False)

    reader = ParquetReader()

    print("=" * 60)
    print("Testing Parquet Reader")
    print("=" * 60)
    df, info = reader.read(sample_parquet)
    print(f"Shape: {df.shape}")
    print(f"Info: {info}")
    print(df.head())

    # Cleanup test file
    os.remove(sample_parquet)
    print("\nTest parquet file cleaned up.")
