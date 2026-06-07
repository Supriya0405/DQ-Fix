"""
DQ-FIX — Enterprise Data Quality Dashboard
==========================================
Full 3-panel enterprise dashboard with AI-powered data quality analysis.
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    APP_TITLE, APP_ICON, SAMPLE_DATA_DIR, MAX_ROWS_PREVIEW,
    DEFAULT_RULES_PATH, DATABASE_PATH,
    SUPPORTED_PROVIDERS, DEFAULT_PROVIDER,
    GROQ_API_KEY, OPENAI_API_KEY,
)
from src.readers.csv_reader import CSVReader
from src.readers.parquet_reader import ParquetReader
from src.rules.rule_engine import RuleEngine
from src.validators.validation_engine import ValidationEngine
from src.validators.result_models import ValidationResult
from src.ai.llm_client import LLMClient
from src.ai.severity_engine import SeverityEngine
from src.agent.agent_loop import AgentLoop
from src.api.email_verifier import EmailVerifier
from src.fixer.auto_fixer import AutoFixer
from src.database.db_manager import DatabaseManager
from src.utils.helpers import (
    get_dataset_summary, format_file_size,
    get_column_profile, calculate_health_score,
)
from ui.theme import (
    inject_global_css, header_html, metric_card, insight_card,
    failures_card, remediation_card, sidebar_brand_html,
    step_indicator_html, workflow_step_header,
)


NAV_PAGES = [
    "Dataset Overview",
    "Validation Rules",
    "Failed Records",
    "AI Insights",
    "Agent Loop Status",
    "Validation History",
    "Settings",
]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title=APP_TITLE, page_icon=APP_ICON,
        layout="wide", initial_sidebar_state="expanded",
    )

    _init_session_state()
    st.markdown(inject_global_css(), unsafe_allow_html=True)

    page = _render_sidebar_nav()
    _render_app_header()

    if page == "Dataset Overview":
        _page_dataset_overview()
    elif page == "Validation Rules":
        _page_validation_rules()
    elif page == "Failed Records":
        _page_failed_records()
    elif page == "AI Insights":
        _page_ai_insights()
    elif page == "Agent Loop Status":
        _page_agent_loop()
    elif page == "Validation History":
        _page_validation_history()
    elif page == "Settings":
        _page_settings()


def _render_app_header():
    df = st.session_state.df
    agent = st.session_state.agent_result
    info = st.session_state.dataset_info

    agent_status = agent.get("status", "idle") if agent else "idle"
    iteration = agent.get("total_iterations", 0) if agent else 0
    agent_active = agent_status not in ("idle", "completed", "success")
    dataset_name = info.get("file_name") if info else None

    st.markdown(
        header_html(
            title="DQ-Fix Agent",
            agent_status=agent_status,
            iteration=iteration,
            dataset_name=dataset_name,
            agent_active=agent_active or (iteration > 0 and agent_status == "running"),
        ),
        unsafe_allow_html=True,
    )


def _render_sidebar_nav() -> str:
    vr = st.session_state.validation_result
    failed_count = vr.total_failures if vr else 0
    ai_count = len(st.session_state.ai_analyses)

    labels = {
        "Dataset Overview": "Dataset Overview",
        "Validation Rules": "Validation Rules",
        "Failed Records": f"Failed Records ({failed_count})" if failed_count else "Failed Records",
        "AI Insights": f"AI Insights ({ai_count})" if ai_count else "AI Insights",
        "Agent Loop Status": "Agent Loop Status",
        "Validation History": "Validation History",
        "Settings": "Settings",
    }

    with st.sidebar:
        st.markdown(sidebar_brand_html(), unsafe_allow_html=True)
        page = st.radio(
            "Navigation",
            options=NAV_PAGES,
            format_func=lambda p: labels.get(p, p),
            label_visibility="collapsed",
            key="nav_page",
        )
        st.markdown("---")
        if st.session_state.cleaned_df is not None:
            fixer = AutoFixer()
            csv_bytes = fixer.to_csv_bytes(st.session_state.cleaned_df)
            st.download_button(
                "Download Cleaned",
                data=csv_bytes,
                file_name="cleaned_data.csv",
                mime="text/csv",
                use_container_width=True,
            )
    return page


def _get_health_score() -> float:
    df = st.session_state.df
    vr = st.session_state.validation_result
    if df is None:
        return 0.0
    summary = get_dataset_summary(df)
    return calculate_health_score(
        summary["total_rows"], summary["null_count"],
        summary["duplicated_rows"],
        vr.total_failures if vr else 0,
    )


def _get_primary_analysis() -> dict:
    analyses = st.session_state.ai_analyses
    if analyses:
        return analyses[0]
    vr = st.session_state.validation_result
    if vr:
        failed = vr.get_failed_results()
        if failed:
            rr = failed[0]
            return {
                "root_cause": rr.description,
                "confidence": 0,
                "rule_id": rr.rule_id,
            }
    return None


def _get_remediation_fixes() -> tuple:
    analyses = st.session_state.ai_analyses
    if analyses:
        a = analyses[0]
        provider = st.session_state.get("ai_provider", "ollama")
        return a.get("sql_fix", ""), a.get("pandas_fix", ""), provider
    return "", "", "ollama"


def _build_failure_list() -> list:
    vr = st.session_state.validation_result
    if not vr:
        return []
    failures = []
    for rr in vr.get_failed_results():
        desc = rr.description
        if rr.failed_count:
            desc = f"{rr.description} — {rr.failed_count} rows affected"
        failures.append({
            "rule_id": f"{rr.rule_id}: {rr.column} → {rr.rule_type}",
            "description": desc,
            "severity": rr.severity,
        })
    return failures


def _init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "df": None, "dataset_info": None, "rule_engine": None,
        "validation_result": None, "ai_analyses": [],
        "agent_result": None, "cleaned_df": None,
        "email_results": [], "db": None,
        "_last_uploaded_file": None,
        "ai_provider": DEFAULT_PROVIDER,
        "ai_api_key": GROQ_API_KEY or OPENAI_API_KEY or "",
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
    if st.session_state.db is None:
        try:
            st.session_state.db = DatabaseManager()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# SETUP WORKFLOW — Dataset → Rules → AI Provider
# ═══════════════════════════════════════════════════════════════════════════

def _setup_status() -> dict:
    df = st.session_state.df
    re = st.session_state.rule_engine
    llm = _get_llm_client()
    return {
        "has_dataset": df is not None,
        "has_rules": re is not None,
        "has_provider": llm.is_available(),
        "ready": df is not None and re is not None,
    }


def _render_ai_provider_selector(radio_key: str = "ai_provider_radio"):
    provider_options = list(SUPPORTED_PROVIDERS.keys())
    selected_idx = (
        provider_options.index(st.session_state.ai_provider)
        if st.session_state.ai_provider in provider_options else 0
    )
    selected = st.radio(
        "Choose AI provider",
        options=provider_options,
        format_func=lambda x: SUPPORTED_PROVIDERS[x]["name"],
        index=selected_idx,
        key=radio_key,
        horizontal=True,
    )
    st.session_state.ai_provider = selected
    llm = _get_llm_client()
    if llm.is_available():
        st.success(f"Connected: {llm.get_status()}")
    else:
        st.warning(f"{llm.get_status()} — add API keys in .env for Groq/OpenAI, or start Ollama locally.")


def _render_setup_workflow() -> bool:
    """Step-by-step setup. Returns True when dataset + rules are ready."""
    status = _setup_status()

    steps = [
        {"label": "Upload Dataset", "status": "done" if status["has_dataset"] else "active"},
        {"label": "Validation Rules", "status": (
            "done" if status["has_rules"] else ("active" if status["has_dataset"] else "pending")
        )},
        {"label": "AI Provider", "status": (
            "done" if status["has_provider"] else ("active" if status["has_rules"] else "pending")
        )},
    ]
    st.markdown(step_indicator_html(steps), unsafe_allow_html=True)

    # ── Step 1: Dataset ──────────────────────────────────────────────────
    st.markdown(
        workflow_step_header(1, "Upload Dataset", done=status["has_dataset"]),
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Upload CSV or Parquet file", type=["csv", "parquet"], key="data_upload",
    )
    if uploaded:
        current_id = getattr(uploaded, "id", None) or uploaded.name
        if st.session_state.get("_last_upload_id") != current_id:
            _process_upload(uploaded)
    elif not status["has_dataset"]:
        st.info("Upload a dataset to preview your data and generate validation rules.")

    if status["has_dataset"]:
        info = st.session_state.dataset_info
        m1, m2, m3 = st.columns(3)
        m1.metric("File", info["file_name"])
        m2.metric("Rows", f"{info['rows']:,}")
        m3.metric("Columns", info["columns"])
        with st.expander("Preview Data", expanded=True):
            st.dataframe(st.session_state.df.head(MAX_ROWS_PREVIEW), use_container_width=True)
        with st.expander("Column Types"):
            dtype_df = pd.DataFrame([{"Column": c, "Type": t} for c, t in info["dtypes"].items()])
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)

    # ── Step 2: Rules ────────────────────────────────────────────────────
    st.markdown(
        workflow_step_header(2, "Validation Rules", done=status["has_rules"]),
        unsafe_allow_html=True,
    )
    if not status["has_dataset"]:
        st.caption("Complete Step 1 first — rules are generated from your uploaded dataset.")
    else:
        info = st.session_state.dataset_info
        has_rules = status["has_rules"]
        btn_label = "Regenerate Rules with AI" if has_rules else "Auto-Generate Rules (AI)"
        if st.button(btn_label, type="primary", use_container_width=True,
                     help="AI analyzes your dataset columns and creates matching YAML rules"):
            _auto_generate_rules(st.session_state.df, info.get("file_name", "dataset"))

        rules_file = st.file_uploader(
            "Or upload custom YAML rules", type=["yaml", "yml"], key="rules_upload",
        )
        if rules_file:
            _load_rules_from_buffer(rules_file)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Load Default Rules", use_container_width=True):
                _load_rules(DEFAULT_RULES_PATH)
        with c2:
            if st.button("Clear Rules", use_container_width=True):
                st.session_state.rule_engine = None
                st.session_state.validation_result = None
                st.session_state.ai_analyses = []
                st.rerun()

        if st.session_state.rule_engine:
            s = st.session_state.rule_engine.summary()
            st.success(f"{s['total_rules']} rules loaded covering {len(s['columns_covered'])} columns")

    # ── Step 3: AI Provider ──────────────────────────────────────────────
    st.markdown(
        workflow_step_header(3, "AI Provider", done=status["has_provider"]),
        unsafe_allow_html=True,
    )
    if not status["has_rules"]:
        st.caption("Complete Step 2 first — the provider powers AI rule generation and analysis.")
    else:
        _render_ai_provider_selector(radio_key="setup_provider_radio")

    return status["ready"]


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: DATASET OVERVIEW (Bento Dashboard)
# ═══════════════════════════════════════════════════════════════════════════

def _page_dataset_overview():
    setup_ready = _render_setup_workflow()

    st.markdown("---")
    st.markdown("### Analytics Dashboard")

    if not setup_ready:
        st.markdown(
            '<div class="dq-empty-state">Complete Steps 1 &amp; 2 above to unlock validation and AI analysis.</div>',
            unsafe_allow_html=True,
        )
        return

    df = st.session_state.df
    re = st.session_state.rule_engine

    health = _get_health_score()
    agent = st.session_state.agent_result
    prev_health = st.session_state.get("_prev_health")
    trend = ""
    if prev_health is not None and agent and agent.get("total_iterations", 0) > 1:
        delta = health - prev_health
        if delta != 0:
            trend = f"{'+' if delta > 0 else ''}{delta:.1f}% from previous iteration"
    st.session_state["_prev_health"] = health

    analysis = _get_primary_analysis()
    insight_text = (
        analysis.get("root_cause", "Run validation and AI analysis to generate root cause insights.")
        if analysis else "Load rules and run validation to detect data quality issues."
    )
    insight_conf = analysis.get("confidence") if analysis and analysis.get("confidence") else None

    # Top bento row: Health | Records | AI Insight
    c1, c2, c3 = st.columns([1, 1, 2.2])
    with c1:
        st.markdown(
            metric_card("Health Score", f"{health:.1f}%", trend=trend, trend_up=health >= 70),
            unsafe_allow_html=True,
        )
    with c2:
        source = "AWS S3 / Landing" if st.session_state.dataset_info else "Local Upload"
        st.markdown(
            metric_card("Total Records", f"{len(df):,}", sub=f"Source: {source}"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            insight_card("AI Root Cause Analysis", insight_text, insight_conf),
            unsafe_allow_html=True,
        )

    # Action bar
    ac1, ac2, ac3 = st.columns([1.2, 1.2, 2])
    with ac1:
        run_val = st.button("Run Validation", type="primary", use_container_width=True,
                            disabled=re is None)
    with ac2:
        vr = st.session_state.validation_result
        run_agent = st.button("Run Agent Loop", use_container_width=True,
                              disabled=not (vr and not vr.all_passed))
    with ac3:
        if re is None:
            st.caption("Load or generate validation rules to enable validation.")
        elif vr:
            if vr.all_passed:
                st.success(f"All {vr.total_rules} rules passed")
            else:
                st.warning(f"{vr.failed_rules}/{vr.total_rules} rules failed")

    if run_val and re:
        _execute_validation(df, re)
    if run_agent and re and vr and not vr.all_passed:
        _execute_agent_loop(df, re)

    # Bottom bento row: Failures | Remediation
    sql_fix, pandas_fix, provider = _get_remediation_fixes()
    failures = _build_failure_list()
    bc1, bc2 = st.columns([1.4, 1])
    with bc1:
        st.markdown(failures_card(failures), unsafe_allow_html=True)
    with bc2:
        st.markdown(remediation_card(sql_fix, pandas_fix, provider), unsafe_allow_html=True)
        if st.session_state.cleaned_df is not None:
            if st.button("Apply Fix & Re-run", type="primary", use_container_width=True):
                st.session_state.df = st.session_state.cleaned_df
                st.session_state.validation_result = None
                st.success("Fix applied. Re-run validation to verify.")
                st.rerun()


def _execute_validation(df, re):
    rule_columns = set(r.column for r in re.get_rules())
    data_columns = set(df.columns.tolist())
    matching_columns = rule_columns & data_columns
    missing_columns = rule_columns - data_columns
    if missing_columns and not matching_columns:
        st.error("No matching columns between dataset and rules.")
        return
    if missing_columns:
        st.warning(f"{len(missing_columns)} rule columns not in data ({len(matching_columns)} rules will run)")
    with st.spinner("Running validation rules..."):
        engine = ValidationEngine()
        result = engine.validate(df, re.get_rules())
        st.session_state.validation_result = result
        if st.session_state.db:
            try:
                run_id = st.session_state.db.save_validation_run(
                    st.session_state.dataset_info.get("file_name", "unknown"),
                    len(df), result, total_columns=len(df.columns),
                )
                st.session_state.current_run_id = run_id
            except Exception as e:
                import logging
                logging.getLogger("dq_database").error(f"Validation save failed: {e}")
    st.rerun()


def _execute_agent_loop(df, re):
    progress_bar = st.progress(0, text="Agent loop starting...")
    llm_for_agent = _get_llm_client()
    loop = AgentLoop(max_iterations=3, llm=llm_for_agent)
    progress_bar.progress(10, text="Analyzing failures with AI...")
    result = loop.run(df, re.get_rules())
    progress_bar.progress(90, text="Finalizing results...")
    st.session_state.agent_result = result
    st.session_state.cleaned_df = result.get("final_df")
    all_analyses = []
    for it in result.get("iterations", []):
        all_analyses.extend(it.get("ai_analyses", []))
    st.session_state.ai_analyses = all_analyses
    if st.session_state.db:
        try:
            engine = ValidationEngine()
            initial_result = engine.validate(df, re.get_rules())
            run_id = st.session_state.db.save_validation_run(
                st.session_state.dataset_info.get("file_name", "unknown"),
                len(df), initial_result, total_columns=len(df.columns),
            )
            st.session_state.current_run_id = run_id
            for it in result.get("iterations", []):
                st.session_state.db.save_agent_iteration(
                    run_id=run_id, iteration=it["iteration"],
                    status=it.get("status", "unknown"),
                    passed_rules=it.get("passed_rules", 0),
                    failed_rules=it.get("failed_rules", 0),
                    total_failures=it.get("total_failures", 0),
                    fixes_applied=len(it.get("fixes_applied", [])),
                    action_taken=f"Iteration {it['iteration']}: {len(it.get('ai_analyses', []))} analyzed",
                    details=it,
                )
            for it in result.get("iterations", []):
                for analysis in it.get("ai_analyses", []):
                    analysis["provider"] = st.session_state.get("ai_provider", "fallback")
                    st.session_state.db.save_ai_analysis(run_id, analysis)
            for email_res in st.session_state.get("email_results", []):
                st.session_state.db.save_api_validation(email_res.get("email", ""), email_res)
        except Exception as e:
            import logging
            logging.getLogger("dq_database").error(f"Agent loop DB save failed: {e}")
    progress_bar.progress(100, text=f"Done — {result['total_iterations']} iteration(s)")
    import time
    time.sleep(1)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: VALIDATION RULES
# ═══════════════════════════════════════════════════════════════════════════

def _page_validation_rules():
    st.markdown("### Validation Rules")
    st.caption("Manage rules here, or use the setup workflow on Dataset Overview.")

    if st.session_state.df is None:
        st.info("Upload a dataset on Dataset Overview first.")
    else:
        info = st.session_state.dataset_info
        st.markdown(f"**{info['file_name']}** — {info['rows']} rows × {info['columns']} columns")
        has_rules = st.session_state.rule_engine is not None
        label = "Regenerate Rules (AI)" if has_rules else "Auto-Generate Rules (AI)"
        if st.button(label, use_container_width=True):
            _auto_generate_rules(st.session_state.df, info.get("file_name", "dataset"))

    rules_file = st.file_uploader("Upload YAML rules", type=["yaml", "yml"], key="rules_upload_page")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Load Default Rules", use_container_width=True, key="default_rules_page"):
            _load_rules(DEFAULT_RULES_PATH)
    with c2:
        if st.button("Clear Rules", use_container_width=True, key="clear_rules_page"):
            st.session_state.rule_engine = None
            st.session_state.validation_result = None
            st.session_state.ai_analyses = []
            st.rerun()

    if rules_file:
        _load_rules_from_buffer(rules_file)

    if st.session_state.rule_engine:
        re = st.session_state.rule_engine
        s = re.summary()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Rules", s["total_rules"])
        m2.metric("Columns Covered", len(s["columns_covered"]))
        m3.metric("Rule Types", len(s.get("by_type", {})))

        with st.expander("Rule Details", expanded=True):
            for r in re.get_rules():
                st.markdown(f"**{r.id}** — `{r.column}` → {r.type} ({r.severity})")
                st.caption(r.description)
    else:
        st.info("No rules loaded. Upload YAML, use default rules, or auto-generate with AI.")

    if st.session_state.df is not None:
        with st.expander("Dataset Preview"):
            st.dataframe(st.session_state.df.head(MAX_ROWS_PREVIEW), use_container_width=True)
        with st.expander("Column Types"):
            info = st.session_state.dataset_info
            dtype_df = pd.DataFrame([{"Column": c, "Type": t} for c, t in info["dtypes"].items()])
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: FAILED RECORDS
# ═══════════════════════════════════════════════════════════════════════════

def _page_failed_records():
    st.markdown("### Failed Records")
    vr = st.session_state.validation_result
    if not vr:
        st.info("Run validation from Dataset Overview to see failed records.")
        return

    failed = vr.get_failed_results()
    if not failed:
        st.success("No failed records — all validation rules passed.")
        return

    st.markdown(failures_card(_build_failure_list()), unsafe_allow_html=True)

    for rr in failed:
        with st.expander(
            f"{rr.rule_id}: {rr.column} → {rr.rule_type} ({rr.failed_count} failures)",
            expanded=False,
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Failed Rows", rr.failed_count)
            c2.metric("Total Rows", rr.total_rows)
            c3.metric("Severity", rr.severity.upper())
            st.markdown(f"**Description:** {rr.description}")
            st.markdown(f"**Failed indices:** {rr.failed_row_indices[:30]}")
            for detail in rr.error_details[:8]:
                st.markdown(f"- {detail}")
            if rr.failed_samples is not None:
                st.dataframe(rr.failed_samples.head(10), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: AI INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════

def _page_ai_insights():
    st.markdown("### AI Insights")
    analyses = st.session_state.ai_analyses

    if not analyses:
        vr = st.session_state.validation_result
        if vr and not vr.all_passed:
            st.info("Generate AI insights with a quick analysis or run the agent loop.")
            if st.button("Quick AI Analysis", type="primary"):
                _run_quick_analysis(vr)
        else:
            st.info("Run validation first, then generate AI insights.")
        return

    llm = _get_llm_client()
    if llm.is_available():
        st.success(llm.get_status())
    else:
        st.warning(f"{llm.get_status()} — using fallback analysis")

    for i, analysis in enumerate(analyses[:10]):
        rule_id = analysis.get("rule_id", f"R{i}")
        col = analysis.get("column", "unknown")
        rtype = analysis.get("rule_type", "unknown")
        with st.expander(f"{rule_id}: {col} → {rtype}", expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            c1.metric("Severity", analysis.get("severity", "medium").upper())
            c2.metric("Confidence", f"{analysis.get('confidence', 0)}/100")
            c3.metric("Affected Rows", analysis.get("estimated_affected_rows", analysis.get("failed_count", "—")))
            st.markdown("**Root Cause**")
            st.markdown(analysis.get("root_cause", "N/A"))
            st.markdown("**Explanation**")
            st.markdown(analysis.get("explanation", "N/A"))
            st.markdown("**Business Impact**")
            st.markdown(analysis.get("business_impact", "N/A"))
            st.code(analysis.get("sql_fix", "-- No fix"), language="sql")
            st.code(analysis.get("pandas_fix", "# No fix"), language="python")
            st.markdown("**Prevention**")
            st.markdown(analysis.get("prevention", "N/A"))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: AGENT LOOP STATUS
# ═══════════════════════════════════════════════════════════════════════════

def _page_agent_loop():
    st.markdown("### Agent Loop Status")
    df = st.session_state.df
    re = st.session_state.rule_engine
    vr = st.session_state.validation_result

    if df is None or re is None:
        st.info("Complete setup on Dataset Overview — upload a dataset and load rules first.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Run Agent Loop", type="primary", use_container_width=True,
                     disabled=not (vr and not vr.all_passed)):
            _execute_agent_loop(df, re)
    with c2:
        agent = st.session_state.agent_result
        if agent:
            st.markdown(
                f"**Status:** {agent.get('status', 'idle').replace('_', ' ').title()} | "
                f"**Iterations:** {agent.get('total_iterations', 0)}/3"
            )

    agent = st.session_state.agent_result
    if not agent:
        st.caption("Agent loop has not been run yet.")
        return

    for it_data in agent.get("iterations", []):
        with st.expander(
            f"Iteration {it_data['iteration']}: {it_data['status']} — "
            f"{it_data['failed_rules']} rules failed"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Passed Rules", it_data["passed_rules"])
            c2.metric("Failed Rules", it_data["failed_rules"])
            c3.metric("Fixes Applied", len(it_data.get("fixes_applied", [])))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: VALIDATION HISTORY
# ═══════════════════════════════════════════════════════════════════════════

def _page_validation_history():
    st.markdown("### Validation History")
    if not st.session_state.db:
        st.warning("Database not available.")
        return

    history_tab = st.tabs(["Runs", "AI Analysis", "Remediations", "Agent Loop", "API Results", "Stats"])

    with history_tab[0]:
        runs = st.session_state.db.get_validation_history(limit=20)
        if runs:
            for r in runs:
                icon = "PASS" if r["overall_status"] == "passed" else "FAIL"
                with st.expander(
                    f"{icon} #{r['run_id']} | {r['dataset_name']} | "
                    f"{r['passed_rules']}/{r['total_rules']} | {r['validation_timestamp'][:16]}"
                ):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Rows", r["total_rows"])
                    c2.metric("Columns", r.get("total_columns", "—"))
                    c3.metric("Passed", r["passed_rules"])
                    c4.metric("Failed", r["failed_rules"])
        else:
            st.info("No validation runs yet.")

    with history_tab[1]:
        analyses = st.session_state.db.get_ai_analysis_history(limit=30)
        if analyses:
            for a in analyses[:15]:
                with st.expander(
                    f"{a.get('rule_id', '')} | {a.get('column_name', '')} | Run#{a['run_id']}"
                ):
                    st.markdown(f"**Root Cause:** {a.get('root_cause', 'N/A')}")
                    st.markdown(f"**Confidence:** {a.get('confidence_score', 0)}%")
        else:
            st.info("No AI analyses yet.")

    with history_tab[2]:
        remediations = st.session_state.db.get_remediation_history(limit=30)
        if remediations:
            for rem in remediations[:15]:
                with st.expander(f"{rem.get('rule_id', '')} | Run#{rem['run_id']}"):
                    st.code(rem.get("sql_fix", "N/A"), language="sql")
                    st.code(rem.get("pandas_fix", "N/A"), language="python")
        else:
            st.info("No remediations yet.")

    with history_tab[3]:
        iterations = st.session_state.db.get_agent_iterations(limit=30)
        if iterations:
            for it in iterations[:15]:
                with st.expander(f"Run#{it['run_id']} | Iteration {it['iteration_number']}"):
                    st.markdown(f"**Action:** {it.get('action_taken', 'N/A')}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Passed", it.get("passed_rules", 0))
                    c2.metric("Failed", it.get("failed_rules", 0))
                    c3.metric("Fixes", it.get("fixes_applied", 0))
        else:
            st.info("No agent iterations yet.")

    with history_tab[4]:
        api_results = st.session_state.db.get_api_validation_history(limit=30)
        if api_results:
            for api in api_results[:15]:
                status = "Valid" if api.get("is_valid") else "Invalid"
                st.markdown(
                    f"**{api['email']}** — {status} | "
                    f"Confidence: {api.get('confidence_score', 0)}"
                )
        else:
            st.info("No API results yet.")

    with history_tab[5]:
        stats = st.session_state.db.get_statistics()
        if stats:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Runs", stats.get("validation_runs", 0))
            c2.metric("Rules Checked", stats.get("total_rules_checked", 0))
            c3.metric("Pass Rate", f"{stats.get('pass_rate', 0)}%")
            c4.metric("AI Analyses", stats.get("ai_analysis", 0))
            if st.button("Clear All History"):
                st.session_state.db.clear_all_history()
                st.success("History cleared.")
                st.rerun()
        else:
            st.info("No statistics available.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

def _page_settings():
    st.markdown("### Settings")

    st.subheader("AI Provider")
    st.caption("Also configurable in Step 3 on Dataset Overview.")
    _render_ai_provider_selector(radio_key="settings_provider_radio")

    st.subheader("Email Verification API")
    from config.settings import EMAIL_API_KEY
    if EMAIL_API_KEY:
        st.success("EMAIL_API_KEY loaded from .env")
    else:
        st.warning(
            "EMAIL_API_KEY not set — API calls will use regex fallback only. "
            "Get a free key at https://app.emailvalidation.io and add `EMAIL_API_KEY=...` to `.env`."
        )
    test_email = st.text_input("Test email address", value="test@example.com", key="email_test")
    if st.button("Verify Email", use_container_width=True):
        verifier = EmailVerifier()
        result = verifier.verify(test_email)
        result["email"] = test_email
        st.session_state.email_results.append(result)
        if st.session_state.db:
            try:
                st.session_state.db.save_api_validation(test_email, result)
            except Exception:
                pass
        st.json(result)

    if st.session_state.email_results:
        for er in st.session_state.email_results[-5:]:
            status = "Valid" if er["is_valid"] else "Invalid"
            st.markdown(f"**{er['email']}** — {status} | Confidence: {er['confidence']}")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _process_upload(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            reader = CSVReader()
            df, info = reader.read(file_buffer=uploaded_file)
        elif name.endswith(".parquet"):
            reader = ParquetReader()
            df, info = reader.read(file_buffer=uploaded_file)
        else:
            return
        st.session_state.df = df
        st.session_state.dataset_info = info
        upload_id = getattr(uploaded_file, 'id', None) or uploaded_file.name
        st.session_state._last_upload_id = upload_id
        st.session_state._last_uploaded_file = uploaded_file.name
        # Reset ALL downstream state for a clean start
        st.session_state.rule_engine = None
        st.session_state.validation_result = None
        st.session_state.ai_analyses = []
        st.session_state.agent_result = None
        st.session_state.cleaned_df = None
        st.success(f"✅ Loaded {info['file_name']} ({info['rows']} rows × {info['columns']} cols)")
        st.rerun()
    except Exception as e:
        st.error(f"Error reading file: {e}")


def _load_sample(filename):
    path = os.path.join(SAMPLE_DATA_DIR, filename)
    try:
        reader = CSVReader()
        df, info = reader.read(path)
        st.session_state.df = df
        st.session_state.dataset_info = info
        st.session_state._last_upload_id = None  # Reset upload tracking
        st.session_state._last_uploaded_file = None
        # Reset all downstream state for a clean start
        st.session_state.rule_engine = None
        st.session_state.validation_result = None
        st.session_state.ai_analyses = []
        st.session_state.agent_result = None
        st.session_state.cleaned_df = None
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


def _load_rules(yaml_path):
    try:
        engine = RuleEngine(yaml_path=yaml_path)
        st.session_state.rule_engine = engine
        # Reset downstream state
        st.session_state.validation_result = None
        st.session_state.ai_analyses = []
        st.session_state.agent_result = None
        st.session_state.cleaned_df = None
        st.rerun()
    except Exception as e:
        st.error(f"Error loading rules: {e}")


def _load_rules_from_buffer(uploaded_file):
    try:
        content = uploaded_file.read().decode("utf-8")
        engine = RuleEngine(yaml_content=content)
        st.session_state.rule_engine = engine
        # Reset downstream state
        st.session_state.validation_result = None
        st.session_state.ai_analyses = []
        st.session_state.agent_result = None
        st.session_state.cleaned_df = None
        st.rerun()
    except Exception as e:
        st.error(f"Error parsing rules: {e}")


def _run_quick_analysis(vr):
    """Run quick AI analysis without agent loop."""
    llm = _get_llm_client()
    sev_engine = SeverityEngine()
    analyses = []
    for rr in vr.get_failed_results()[:5]:
        analysis = llm.analyze_failure(rr, rr.failed_samples)
        analysis["severity"] = sev_engine.calculate_severity(
            rr.rule_type, rr.failed_count, rr.total_rows, rr.severity)
        analysis["confidence"] = sev_engine.calculate_confidence(
            rr.rule_type, rr.failed_count, rr.total_rows, True, llm.is_available())
        analysis["rule_id"] = rr.rule_id
        analysis["rule_type"] = rr.rule_type
        analysis["column"] = rr.column
        analysis["failed_count"] = rr.failed_count
        analysis["provider"] = st.session_state.get("ai_provider", "fallback")
        analyses.append(analysis)
        # Save to DB
        if st.session_state.db:
            try:
                run_id = getattr(st.session_state, 'current_run_id', 1)
                st.session_state.db.save_ai_analysis(run_id, analysis)
            except Exception:
                pass
    st.session_state.ai_analyses = analyses
    st.rerun()


def _get_llm_client() -> LLMClient:
    """Get an LLM client configured with the selected provider and API key."""
    provider = st.session_state.get("ai_provider", DEFAULT_PROVIDER)
    api_key = st.session_state.get("ai_api_key", "")
    # Fallback: if session state key is empty, reload from settings
    if not api_key:
        if provider == "groq":
            api_key = GROQ_API_KEY
        elif provider == "openai":
            api_key = OPENAI_API_KEY
        if api_key:
            st.session_state.ai_api_key = api_key
    import logging
    logging.getLogger("dq_ai").info(f"_get_llm_client: provider={provider}, key_len={len(api_key)}, key_empty={not api_key}")
    return LLMClient(provider=provider, api_key=api_key)


def _auto_generate_rules(df, dataset_name):
    """Use AI to analyze the dataset and generate validation rules automatically."""
    with st.spinner("AI is analyzing your dataset and generating rules..."):
        try:
            llm = _get_llm_client()
            yaml_content = llm.generate_rules(df, dataset_name)

            # Try to parse the generated YAML
            import yaml
            parsed = yaml.safe_load(yaml_content)
            if not parsed or "rules" not in parsed:
                st.error("AI generated invalid rules format. Using fallback rule generation.")
                # Use fallback directly
                yaml_content = llm._fallback_generate_rules(df, dataset_name)
                parsed = yaml.safe_load(yaml_content)

            # Load into RuleEngine
            engine = RuleEngine(yaml_content=yaml_content)
            st.session_state.rule_engine = engine
            st.session_state.validation_result = None
            st.session_state.ai_analyses = []
            st.session_state.agent_result = None
            st.session_state.cleaned_df = None
            st.success(f"✅ Generated {engine.summary()['total_rules']} rules for {len(df.columns)} columns!")
            st.rerun()
        except Exception as e:
            st.error(f"Error generating rules: {e}")
            # Try fallback
            try:
                llm = _get_llm_client()
                yaml_content = llm._fallback_generate_rules(df, dataset_name)
                engine = RuleEngine(yaml_content=yaml_content)
                st.session_state.rule_engine = engine
                st.session_state.validation_result = None
                st.session_state.ai_analyses = []
                st.session_state.agent_result = None
                st.session_state.cleaned_df = None
                st.success(f"✅ Generated {engine.summary()['total_rules']} rules (heuristic fallback)")
                st.rerun()
            except Exception as e2:
                st.error(f"Fallback also failed: {e2}")


if __name__ == "__main__":
    main()
