"""
DQ-FIX — Streamlit Application Entry Point
==========================================
Run this file to launch the dashboard:
    streamlit run app.py

Phase 3: CSV/Parquet upload + dataset preview + YAML rules viewer.
"""

import streamlit as st
import pandas as pd
import os
import sys

# Add project root to path so src/ imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import APP_TITLE, APP_ICON, SAMPLE_DATA_DIR, MAX_ROWS_PREVIEW, DEFAULT_RULES_PATH
from src.readers.csv_reader import CSVReader
from src.readers.parquet_reader import ParquetReader
from src.rules.rule_engine import RuleEngine
from src.utils.helpers import (
    get_dataset_summary,
    format_file_size,
    get_column_profile,
    calculate_health_score,
)


def main():
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown("---")

    # ── Initialize Session State ──────────────────────────────────────────
    if "df" not in st.session_state:
        st.session_state.df = None
    if "dataset_info" not in st.session_state:
        st.session_state.dataset_info = None
    if "rule_engine" not in st.session_state:
        st.session_state.rule_engine = None

    # ── Sidebar: Dataset Upload ───────────────────────────────────────────
    with st.sidebar:
        st.header("📂 Dataset Upload")

        uploaded_file = st.file_uploader(
            "Upload CSV or Parquet file",
            type=["csv", "parquet"],
            help="Supported formats: .csv, .parquet",
        )

        st.markdown("---")
        st.markdown("**📦 Sample Datasets**")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            load_valid = st.button("✅ Valid Data", use_container_width=True)
        with col_s2:
            load_invalid = st.button("❌ Invalid Data", use_container_width=True)

        if load_valid:
            _load_sample_file("valid_customers.csv")
        if load_invalid:
            _load_sample_file("invalid_customers.csv")

        # ── Sidebar: Validation Rules ────────────────────────────────────
        st.markdown("---")
        st.header("📜 Validation Rules")

        rules_file = st.file_uploader(
            "Upload YAML rules file",
            type=["yaml", "yml"],
            help="Upload a YAML file with validation rules",
            key="rules_upload",
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            load_default_rules = st.button("📄 Default Rules", use_container_width=True)
        with col_r2:
            clear_rules = st.button("🗑️ Clear Rules", use_container_width=True)

        if load_default_rules:
            _load_rules(DEFAULT_RULES_PATH)
        if clear_rules:
            st.session_state.rule_engine = None
            st.rerun()

        if rules_file is not None:
            _load_rules_from_buffer(rules_file)

        st.markdown("---")
        st.header("📋 Navigation")
        st.markdown(
            """
            - **Dataset Upload** ✓ _(Phase 2)_
            - **Validation Rules** ✓ _(Phase 3)_
            - **Validation Results** _(Phase 4)_
            - **AI Insights** _(Phase 5-6)_
            - **Agent Loop** _(Phase 7)_
            - **Apply Fix** _(Phase 10)_
            - **Download CSV** _(Phase 10)_
            """
        )
        st.markdown("---")
        st.caption("DQ-FIX v1.0.0 — Data Quality Agent")

    # ── Process Uploaded File ─────────────────────────────────────────────
    if uploaded_file is not None:
        _process_uploaded_file(uploaded_file)

    # ── Main Content Area ─────────────────────────────────────────────────
    if st.session_state.df is not None:
        _render_dashboard()
    else:
        _render_welcome()

    # ── Rules Viewer (shown below main content) ──────────────────────────
    if st.session_state.rule_engine is not None:
        _render_rules_viewer()


def _load_sample_file(filename: str):
    """Load a sample CSV from the SAMPLE_DATA directory."""
    file_path = os.path.join(SAMPLE_DATA_DIR, filename)
    try:
        reader = CSVReader()
        df, info = reader.read(file_path)
        st.session_state.df = df
        st.session_state.dataset_info = info
        st.rerun()
    except Exception as e:
        st.error(f"Error loading sample file: {e}")


def _load_rules(yaml_path: str):
    """Load rules from a YAML file path."""
    try:
        engine = RuleEngine(yaml_path=yaml_path)
        st.session_state.rule_engine = engine
        st.rerun()
    except Exception as e:
        st.error(f"Error loading rules: {e}")


def _load_rules_from_buffer(uploaded_file):
    """Load rules from a Streamlit uploaded file buffer."""
    try:
        content = uploaded_file.read().decode("utf-8")
        engine = RuleEngine(yaml_content=content)
        st.session_state.rule_engine = engine
        st.rerun()
    except Exception as e:
        st.error(f"Error parsing rules file: {e}")


def _process_uploaded_file(uploaded_file):
    """Process an uploaded CSV or Parquet file."""
    file_name = uploaded_file.name.lower()
    try:
        if file_name.endswith(".csv"):
            reader = CSVReader()
            df, info = reader.read(file_buffer=uploaded_file)
        elif file_name.endswith(".parquet"):
            reader = ParquetReader()
            df, info = reader.read(file_buffer=uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV or Parquet.")
            return

        st.session_state.df = df
        st.session_state.dataset_info = info
    except Exception as e:
        st.error(f"Error reading file: {e}")


def _render_rules_viewer():
    """Render the validation rules viewer section."""
    engine = st.session_state.rule_engine
    rules_summary = engine.summary()

    st.markdown("---")
    st.header("📜 Validation Rules Viewer")

    # Summary metrics
    rs1, rs2, rs3, rs4 = st.columns(4)
    with rs1:
        st.metric("Total Rules", rules_summary["total_rules"])
    with rs2:
        st.metric("Columns Covered", len(rules_summary["columns_covered"]))
    with rs3:
        st.metric("High Severity", len(engine.get_rules_by_severity("high")))
    with rs4:
        st.metric("Parse Errors", rules_summary["parse_errors"])

    # Rules by type
    st.markdown("**Rules by Type:**")
    type_cols = st.columns(len(rules_summary["by_type"]) or 1)
    for i, (rtype, count) in enumerate(rules_summary["by_type"].items()):
        with type_cols[i]:
            st.metric(rtype.replace("_", " ").title(), count)

    # Rules table
    st.markdown("---")
    st.subheader("📋 All Rules")
    rules_df = engine.to_dataframe()
    # Reorder columns for display
    display_cols = ["id", "column", "type", "severity", "description"]
    st.dataframe(rules_df[display_cols], use_container_width=True, hide_index=True)

    # Errors
    errors = engine.get_errors()
    if errors:
        st.warning(f"**{len(errors)} parsing error(s):**")
        for err in errors:
            st.error(err)

    # Dataset metadata
    st.markdown(f"**Dataset:** {engine.get_dataset_name()} | **Description:** {engine.get_dataset_description()}")


def _render_welcome():
    """Render the welcome screen when no dataset is loaded."""
    st.info(
        "👈 **Upload a dataset** from the sidebar to get started, or click "
        "a sample dataset button to try it out."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Supported Formats", "CSV, Parquet")
    with col2:
        st.metric("Validation Types", "7 Types")
    with col3:
        st.metric("AI Analysis", "Ollama + Llama3")


def _render_dashboard():
    """Render the main dashboard with dataset preview and stats."""
    df = st.session_state.df
    info = st.session_state.dataset_info
    summary = get_dataset_summary(df)

    # ── Top Metrics Bar ───────────────────────────────────────────────────
    st.subheader("📊 Dataset Overview")

    health_score = calculate_health_score(
        total_rows=summary["total_rows"],
        null_count=summary["null_count"],
        duplicated_rows=summary["duplicated_rows"],
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Records", f"{summary['total_rows']:,}")
    with m2:
        st.metric("Columns", summary["total_columns"])
    with m3:
        st.metric("Null Values", summary["null_count"])
    with m4:
        st.metric("Duplicates", summary["duplicated_rows"])
    with m5:
        st.metric(
            "Health Score",
            f"{health_score}/100",
            delta="Good" if health_score >= 70 else "Needs Attention",
            delta_color="normal" if health_score >= 70 else "inverse",
        )

    st.markdown("---")

    # ── Two-Column Layout ─────────────────────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        # Dataset Preview
        st.subheader("🔍 Dataset Preview")
        st.dataframe(df.head(MAX_ROWS_PREVIEW), use_container_width=True)

        # File Info
        st.markdown("---")
        st.subheader("📁 File Information")
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"**File Name:** {info['file_name']}")
            st.markdown(f"**File Size:** {format_file_size(info['file_size_bytes'])}")
            if "encoding" in info:
                st.markdown(f"**Encoding:** {info['encoding']}")
        with info_col2:
            st.markdown(f"**Rows:** {info['rows']}")
            st.markdown(f"**Columns:** {info['columns']}")
            st.markdown(f"**Duplicated Rows:** {info['duplicated_rows']}")

    with right_col:
        # Column Types
        st.subheader("🏷️ Column Types")
        dtype_df = pd.DataFrame(
            [{"Column": col, "Type": dtype} for col, dtype in info["dtypes"].items()]
        )
        st.dataframe(dtype_df, use_container_width=True, hide_index=True)

        # Null Distribution
        st.markdown("---")
        st.subheader("⚠️ Null Distribution")
        null_data = info.get("null_per_column", {})
        if null_data and any(v > 0 for v in null_data.values()):
            null_df = pd.DataFrame(
                [{"Column": col, "Nulls": count} for col, count in null_data.items()]
            )
            st.bar_chart(null_df.set_index("Column"))
        else:
            st.success("✅ No null values found!")

        # Column Profiler
        st.markdown("---")
        st.subheader("📈 Column Profiler")
        selected_col = st.selectbox("Select column to profile", list(df.columns))
        if selected_col:
            profile = get_column_profile(df, selected_col)
            for key, value in profile.items():
                if key not in ("top_values",):
                    st.markdown(f"**{key}:** `{value}`")
            if "top_values" in profile:
                st.markdown("**Top Values:**")
                st.json(profile["top_values"])


if __name__ == "__main__":
    main()
