"""
DQ-FIX — Streamlit Application Entry Point
==========================================
Run this file to launch the dashboard:
    streamlit run app.py

Phase 1: Placeholder — UI will be built in Phase 12.
"""

import streamlit as st
from config.settings import APP_TITLE, APP_ICON


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
    st.info(
        "**Phase 1 Complete** — Project structure is ready.  \n"
        "The dashboard will be built in Phase 12.  \n"
        "For now, use this space to verify your environment is working."
    )

    # ── Environment Check ──────────────────────────────────────────────────
    st.subheader("Environment Check")
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            import pandas as pd
            st.success(f"Pandas {pd.__version__} ✓")
        except ImportError:
            st.error("Pandas not installed")

    with col2:
        try:
            import yaml
            st.success("PyYAML ✓")
        except ImportError:
            st.error("PyYAML not installed")

    with col3:
        try:
            import requests
            st.success("Requests ✓")
        except ImportError:
            st.error("Requests not installed")

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Navigation")
        st.markdown(
            """
            - **Dataset Upload** _(Phase 2)_
            - **Validation Rules** _(Phase 3)_
            - **Validation Results** _(Phase 4)_
            - **AI Insights** _(Phase 5-6)_
            - **Agent Loop** _(Phase 7)_
            - **Apply Fix** _(Phase 10)_
            - **Download CSV** _(Phase 10)_
            """
        )
        st.markdown("---")
        st.caption("DQ-FIX v1.0.0 — Data Quality Agent")


if __name__ == "__main__":
    main()
