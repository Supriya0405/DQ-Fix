"""
CSV Reader Module
=================
Reads CSV files into Pandas DataFrames with error handling.

Usage:
    from src.readers.csv_reader import CSVReader

    reader = CSVReader()
    df, info = reader.read("data.csv")
"""

import pandas as pd
import os


class CSVReader:
    """Reads and validates CSV files into Pandas DataFrames."""

    # Common encodings to try in order
    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

    def read(self, file_path: str = None, file_buffer=None) -> tuple:
        """
        Read a CSV file and return a DataFrame + metadata dict.

        Parameters
        ----------
        file_path : str, optional
            Path to a CSV file on disk.
        file_buffer : file-like, optional
            Uploaded file buffer (from Streamlit's file_uploader).

        Returns
        -------
        tuple (pd.DataFrame, dict)
            DataFrame and a metadata dictionary with:
            - rows, columns, column_names, dtypes, null_count, file_size, encoding
        """
        # ── Validate Input ────────────────────────────────────────────────
        if file_path is None and file_buffer is None:
            raise ValueError("Provide either file_path or file_buffer.")

        if file_path is not None and not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # ── Try Reading with Multiple Encodings ───────────────────────────
        df = None
        used_encoding = None
        last_error = None

        for encoding in self.ENCODINGS:
            try:
                if file_buffer is not None:
                    # Streamlit uploads give us a BytesIO buffer
                    file_buffer.seek(0)
                    df = pd.read_csv(file_buffer, encoding=encoding)
                else:
                    df = pd.read_csv(file_path, encoding=encoding)
                used_encoding = encoding
                break  # Success — stop trying encodings
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue  # Try next encoding
            except pd.errors.EmptyDataError:
                raise ValueError("The CSV file is empty.")
            except pd.errors.ParserError as e:
                raise ValueError(f"CSV parsing error: {e}")

        if df is None:
            raise ValueError(
                f"Could not decode CSV with any supported encoding. "
                f"Last error: {last_error}"
            )

        # ── Build Metadata ────────────────────────────────────────────────
        info = self._build_metadata(df, file_path, used_encoding)

        return df, info

    def _build_metadata(
        self, df: pd.DataFrame, file_path: str, encoding: str
    ) -> dict:
        """Build a metadata dictionary summarizing the DataFrame."""
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0

        return {
            "file_name": os.path.basename(file_path) if file_path else "uploaded_file.csv",
            "file_size_bytes": file_size,
            "encoding": encoding,
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


# ── Quick Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config.settings import SAMPLE_DATA_DIR

    reader = CSVReader()

    print("=" * 60)
    print("Testing with valid_customers.csv")
    print("=" * 60)
    df, info = reader.read(os.path.join(SAMPLE_DATA_DIR, "valid_customers.csv"))
    print(f"Shape: {df.shape}")
    print(f"Info: {info}")
    print(df.head())

    print("\n" + "=" * 60)
    print("Testing with invalid_customers.csv")
    print("=" * 60)
    df, info = reader.read(os.path.join(SAMPLE_DATA_DIR, "invalid_customers.csv"))
    print(f"Shape: {df.shape}")
    print(f"Info: {info}")
    print(df.head())
