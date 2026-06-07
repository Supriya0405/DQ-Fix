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


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title=APP_TITLE, page_icon=APP_ICON,
        layout="wide", initial_sidebar_state="expanded",
    )

    _init_session_state()

    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown("---")

    # ── Top Metrics Bar ──────────────────────────────────────────────────
    _render_top_metrics()

    # ── 3-Panel Layout ──────────────────────────────────────────────────
    left_col, center_col, right_col = st.columns([1, 2, 2])

    with left_col:
        _render_left_panel()

    with center_col:
        _render_center_panel()

    with right_col:
        _render_right_panel()


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
# TOP METRICS BAR
# ═══════════════════════════════════════════════════════════════════════════

def _render_top_metrics():
    """Render the top KPI metrics bar."""
    df = st.session_state.df
    vr = st.session_state.validation_result

    m1, m2, m3, m4, m5, m6 = st.columns(6)

    with m1:
        total = len(df) if df is not None else 0
        st.metric("Total Records", f"{total:,}")

    with m2:
        if vr:
            failed = vr.total_failures
            st.metric("Failed Records", failed,
                       delta=f"{failed} issues" if failed > 0 else "Clean",
                       delta_color="inverse" if failed > 0 else "normal")
        else:
            st.metric("Failed Records", "—")

    with m3:
        if st.session_state.ai_analyses:
            avg_conf = sum(a.get("confidence", 0) for a in st.session_state.ai_analyses) / len(st.session_state.ai_analyses)
            st.metric("Avg Confidence", f"{avg_conf:.0f}/100")
        else:
            st.metric("Avg Confidence", "—")

    with m4:
        if st.session_state.ai_analyses:
            high_sev = sum(1 for a in st.session_state.ai_analyses if a.get("severity") == "high")
            st.metric("High Severity", high_sev,
                       delta="Critical" if high_sev > 0 else None,
                       delta_color="inverse" if high_sev > 0 else "off")
        else:
            st.metric("High Severity", "—")

    with m5:
        if df is not None:
            summary = get_dataset_summary(df)
            health = calculate_health_score(summary["total_rows"], summary["null_count"],
                                            summary["duplicated_rows"],
                                            vr.total_failures if vr else 0)
            st.metric("Health Score", f"{health}/100",
                       delta="Good" if health >= 70 else "Needs Work",
                       delta_color="normal" if health >= 70 else "inverse")
        else:
            st.metric("Health Score", "—")

    with m6:
        agent = st.session_state.agent_result
        if agent:
            st.metric("Agent Status", agent.get("status", "idle").replace("_", " ").title())
        else:
            st.metric("Agent Status", "Idle")


# ═══════════════════════════════════════════════════════════════════════════
# LEFT PANEL — Upload, Rules, History
# ═══════════════════════════════════════════════════════════════════════════

def _render_left_panel():
    st.header("📂 Dataset")

    uploaded = st.file_uploader("Upload CSV/Parquet", type=["csv", "parquet"], key="data_upload")
    if uploaded:
        # Process if this is a new/different upload
        current_id = getattr(uploaded, 'id', None) or uploaded.name
        last_id = st.session_state.get("_last_upload_id")
        if last_id != current_id:
            _process_upload(uploaded)
    elif st.session_state.get("_last_upload_id") and st.session_state.df is not None:
        pass  # Keep data loaded even if uploader cleared
    else:
        st.info("👆 Upload a CSV or Parquet file to get started")

    # Dataset preview
    if st.session_state.df is not None:
        info = st.session_state.dataset_info
        st.markdown(f"**{info['file_name']}** | {info['rows']} rows × {info['columns']} cols")
        with st.expander("🔍 Preview Data"):
            st.dataframe(st.session_state.df.head(20), use_container_width=True)
        with st.expander("📊 Column Types"):
            dtype_df = pd.DataFrame([{"Column": c, "Type": t} for c, t in info["dtypes"].items()])
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)

        # Auto-Generate Rules Button — ALWAYS shown when data is loaded
        has_rules = st.session_state.rule_engine is not None
        btn_label = "🔄 Regenerate Rules with AI" if has_rules else "⚡ Auto-Generate Rules (AI)"
        if st.button(btn_label, use_container_width=True,
                     help="AI analyzes YOUR uploaded dataset and generates matching validation rules"):
            _auto_generate_rules(st.session_state.df, info.get("file_name", "dataset"))

    st.markdown("---")
    st.header("📜 Rules")

    rules_file = st.file_uploader("Upload YAML rules", type=["yaml", "yml"], key="rules_upload")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Default Rules", use_container_width=True):
            _load_rules(DEFAULT_RULES_PATH)
    with c2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.rule_engine = None
            st.session_state.validation_result = None
            st.session_state.ai_analyses = []
            st.rerun()

    if rules_file:
        _load_rules_from_buffer(rules_file)

    if st.session_state.rule_engine:
        re = st.session_state.rule_engine
        s = re.summary()
        st.markdown(f"**{s['total_rules']} rules** loaded | {len(s['columns_covered'])} columns")

    st.markdown("---")
    st.header("📊 History")
    if st.session_state.db:
        try:
            history = st.session_state.db.get_validation_history(limit=5)
            if history:
                for h in history:
                    status_icon = "✅" if h.get("overall_status", h.get("status")) == "passed" else "❌"
                    ts = h.get("validation_timestamp", h.get("timestamp", ""))[:16]
                    st.markdown(f"{status_icon} **{h['dataset_name']}** — {h['passed_rules']}/{h['total_rules']} passed | {ts}")
            else:
                st.caption("No validation history yet")
        except Exception:
            st.caption("Database not available")

    # AI Provider Settings
    st.markdown("---")
    st.header("🤖 AI Provider")
    provider_options = list(SUPPORTED_PROVIDERS.keys())
    provider_labels = [SUPPORTED_PROVIDERS[p]["name"] for p in provider_options]
    selected_idx = provider_options.index(st.session_state.ai_provider) if st.session_state.ai_provider in provider_options else 0

    selected_provider = st.radio(
        "Choose AI provider",
        options=provider_options,
        format_func=lambda x: SUPPORTED_PROVIDERS[x]["name"],
        index=selected_idx,
        key="_provider_radio",
        horizontal=False,
    )
    st.session_state.ai_provider = selected_provider

    # Show current status (API keys loaded from .env automatically)
    llm = _get_llm_client()
    if llm.is_available():
        st.success(f"✅ Connected: {llm.get_status()}")
    else:
        st.warning(f"⚠️ {llm.get_status()}")

    # Email Verification API
    st.markdown("---")
    st.header("📧 Email API")
    test_email = st.text_input("Test email address", value="test@example.com", key="email_test")
    if st.button("Verify Email", use_container_width=True):
        verifier = EmailVerifier()
        result = verifier.verify(test_email)
        result["email"] = test_email
        st.session_state.email_results.append(result)
        api_status = verifier.check_api_status()
        # Save to DB
        if st.session_state.db:
            try:
                st.session_state.db.save_api_validation(test_email, result)
            except Exception:
                pass
        st.json({"result": result, "api_status": api_status})

    if st.session_state.email_results:
        for er in st.session_state.email_results[-3:]:
            icon = "✅" if er["is_valid"] else "❌"
            st.markdown(f"{icon} **{er['email']}** | Status: {er['api_status']} | Confidence: {er['confidence']}")


# ═══════════════════════════════════════════════════════════════════════════
# CENTER PANEL — Validation Results, Failed Records, Agent Loop
# ═══════════════════════════════════════════════════════════════════════════

def _render_center_panel():
    st.header("🔍 Validation")

    df = st.session_state.df
    re = st.session_state.rule_engine

    if df is None or re is None:
        st.info("👈 Load a dataset and rules from the left panel to begin validation.")
        return

    # Check column compatibility between dataset and rules
    rule_columns = set(r.column for r in re.get_rules())
    data_columns = set(df.columns.tolist())
    matching_columns = rule_columns & data_columns
    missing_columns = rule_columns - data_columns

    if missing_columns and not matching_columns:
        st.error(f"❌ No matching columns! Your data has: {sorted(data_columns)[:10]}... "
                 f"but rules expect: {sorted(rule_columns)[:10]}...")
        st.info("💡 Tip: Use the sample data with default rules, or upload a matching CSV.")
        return
    elif missing_columns:
        st.warning(f"⚠️ {len(missing_columns)} rule columns not found in data: {sorted(missing_columns)[:5]}... "
                   f"({len(matching_columns)} rules will run)")

    # Run Validation Button
    c1, c2 = st.columns([1, 2])
    with c1:
        run_val = st.button("▶️ Run Validation", type="primary", use_container_width=True)
    with c2:
        vr = st.session_state.validation_result
        if vr:
            if vr.all_passed:
                st.success(f"✅ All {vr.total_rules} rules passed!")
            else:
                st.warning(f"⚠️ {vr.failed_rules}/{vr.total_rules} rules failed | {vr.total_failures} row failures")

    if run_val:
        with st.spinner("Running 33 validation rules..."):
            engine = ValidationEngine()
            result = engine.validate(df, re.get_rules())
            st.session_state.validation_result = result
            # Save to DB
            if st.session_state.db:
                try:
                    run_id = st.session_state.db.save_validation_run(
                        st.session_state.dataset_info.get("file_name", "unknown"),
                        len(df), result,
                        total_columns=len(df.columns),
                    )
                    st.session_state.current_run_id = run_id
                except Exception as e:
                    import logging
                    logging.getLogger("dq_database").error(f"Validation save failed: {e}")
        st.rerun()

    # Validation Results Table
    vr = st.session_state.validation_result
    if vr:
        st.subheader("📋 Rule Summary")
        summary_df = vr.to_dataframe()

        def highlight(row):
            if row["Status"] == "FAIL":
                return ["background-color: #ffffff; color: #000000; font-weight: bold"] * len(row)
            else:
                return ["background-color: #2a2a2a; color: #ffffff"] * len(row)

        st.dataframe(summary_df.style.apply(highlight, axis=1),
                      use_container_width=True, hide_index=True)

        # Failed Records
        failed = vr.get_failed_results()
        if failed:
            st.subheader(f"Failed Records ({len(failed)} rules)")
            for rr in failed:
                with st.expander(
                    f"{rr.rule_id}: {rr.column} → {rr.rule_type} ({rr.failed_count} failures, {rr.severity})",
                    expanded=False,
                ):
                    st.markdown(f"**Description:** {rr.description}")
                    st.markdown(f"**Severity:** `{rr.severity.upper()}` | **Failed:** {rr.failed_count}/{rr.total_rows}")
                    st.markdown(f"**Failed row indices:** {rr.failed_row_indices[:20]}")
                    for detail in rr.error_details[:5]:
                        st.markdown(f"- {detail}")
                    if len(rr.error_details) > 5:
                        st.caption(f"...and {len(rr.error_details) - 5} more")
                    if rr.failed_samples is not None:
                        st.dataframe(rr.failed_samples.head(5), use_container_width=True)

    # Agent Loop Section
    st.markdown("---")
    st.header("🤖 Agent Loop")

    if vr and not vr.all_passed:
        c1, c2 = st.columns([1, 2])
        with c1:
            run_agent = st.button("🔄 Run Agent Loop", use_container_width=True,
                                   help="Auto-validate → LLM analyze → fix → re-validate (max 3 iterations)")
        with c2:
            agent = st.session_state.agent_result
            if agent:
                status = agent.get("status", "idle")
                iters = agent.get("total_iterations", 0)
                st.markdown(f"**Status:** {status.replace('_', ' ').title()} | **Iterations:** {iters}/3")

        if run_agent:
            progress_bar = st.progress(0, text="Agent loop starting...")
            llm_for_agent = _get_llm_client()
            loop = AgentLoop(max_iterations=3, llm=llm_for_agent)
            progress_bar.progress(10, text="Analyzing failures with AI...")
            result = loop.run(df, re.get_rules())
            progress_bar.progress(90, text="Finalizing results...")
            st.session_state.agent_result = result
            st.session_state.cleaned_df = result.get("final_df")
            # Collect AI analyses
            all_analyses = []
            for it in result.get("iterations", []):
                all_analyses.extend(it.get("ai_analyses", []))
            st.session_state.ai_analyses = all_analyses

            # ── Save to Database ──────────────────────────────────────
            if st.session_state.db:
                try:
                    # Save the initial validation run (first iteration)
                    engine = ValidationEngine()
                    initial_result = engine.validate(df, re.get_rules())
                    run_id = st.session_state.db.save_validation_run(
                        st.session_state.dataset_info.get("file_name", "unknown"),
                        len(df), initial_result,
                        total_columns=len(df.columns),
                    )
                    st.session_state.current_run_id = run_id

                    # Save each agent iteration
                    for it in result.get("iterations", []):
                        st.session_state.db.save_agent_iteration(
                            run_id=run_id,
                            iteration=it["iteration"],
                            status=it.get("status", "unknown"),
                            passed_rules=it.get("passed_rules", 0),
                            failed_rules=it.get("failed_rules", 0),
                            total_failures=it.get("total_failures", 0),
                            fixes_applied=len(it.get("fixes_applied", [])),
                            action_taken=f"Iteration {it['iteration']}: {len(it.get('ai_analyses', []))} analyzed, {len(it.get('fixes_applied', []))} fixes applied",
                            details=it,
                        )

                    # Save all AI analyses and remediations
                    for it in result.get("iterations", []):
                        for analysis in it.get("ai_analyses", []):
                            analysis["provider"] = st.session_state.get("ai_provider", "fallback")
                            st.session_state.db.save_ai_analysis(run_id, analysis)

                    # Save API validations if any
                    for email_res in st.session_state.get("email_results", []):
                        st.session_state.db.save_api_validation(
                            email_res.get("email", ""), email_res
                        )

                except Exception as e:
                    import logging
                    logging.getLogger("dq_database").error(f"Agent loop DB save failed: {e}")

            progress_bar.progress(100, text=f"Done! {result['total_iterations']} iteration(s) completed")
            import time
            time.sleep(1)
            st.rerun()

        # Agent Loop Iteration Details
        agent = st.session_state.agent_result
        if agent:
            for it_data in agent.get("iterations", []):
                it_num = it_data["iteration"]
                with st.expander(f"🔄 Iteration {it_num}: {it_data['status']} — {it_data['failed_rules']} rules failed, {it_data['total_failures']} failures"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Passed Rules", it_data["passed_rules"])
                    with c2:
                        st.metric("Failed Rules", it_data["failed_rules"])
                    with c3:
                        st.metric("Fixes Applied", len(it_data.get("fixes_applied", [])))

    # ── History Dashboard ───────────────────────────────────────────────
    st.markdown("---")
    st.header("📊 Audit History")

    if st.session_state.db:
        history_tab = st.tabs(["Runs", "AI Analysis", "Remediations", "Agent Loop", "API Results", "Stats"])

        with history_tab[0]:
            runs = st.session_state.db.get_validation_history(limit=20)
            if runs:
                for r in runs:
                    icon = "✅" if r["overall_status"] == "passed" else "❌"
                    with st.expander(f"{icon} #{r['run_id']} | {r['dataset_name']} | "
                                     f"{r['passed_rules']}/{r['total_rules']} passed | {r['validation_timestamp'][:16]}"):
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
                    with st.expander(f"🧠 {a.get('rule_id', '')} | {a.get('validation_type', '')} on {a.get('column_name', '')} | "
                                     f"Run#{a['run_id']} | {a.get('provider', 'fallback')}"):
                        st.markdown(f"**Root Cause:** {a.get('root_cause', 'N/A')}")
                        st.markdown(f"**Explanation:** {a.get('explanation', 'N/A')}")
                        st.markdown(f"**Impact:** {a.get('business_impact', 'N/A')}")
                        st.markdown(f"**Recommendation:** {a.get('recommendation', 'N/A')}")
                        st.markdown(f"**Confidence:** {a.get('confidence_score', 0)}% | **Severity:** {a.get('severity', 'N/A')}")
            else:
                st.info("No AI analyses yet.")

        with history_tab[2]:
            remediations = st.session_state.db.get_remediation_history(limit=30)
            if remediations:
                for rem in remediations[:15]:
                    with st.expander(f"🔧 {rem.get('rule_id', '')} | {rem.get('validation_type', '')} on {rem.get('column_name', '')} | "
                                     f"Run#{rem['run_id']}"):
                        st.markdown(f"**SQL Fix:**\n```sql\n{rem.get('sql_fix', 'N/A')}\n```")
                        st.markdown(f"**Pandas Fix:**\n```python\n{rem.get('pandas_fix', 'N/A')}\n```")
                        applied = "✅ Applied" if rem.get('fix_applied') else "⬜ Not applied"
                        st.markdown(f"**Status:** {applied} | **Confidence:** {rem.get('confidence_score', 0)}%")
            else:
                st.info("No remediations yet.")

        with history_tab[3]:
            iterations = st.session_state.db.get_agent_iterations(limit=30)
            if iterations:
                for it in iterations[:15]:
                    with st.expander(f"🔄 Run#{it['run_id']} | Iteration {it['iteration_number']} | "
                                     f"{it.get('validation_status', '')} | {it.get('fixes_applied', 0)} fixes"):
                        st.markdown(f"**Action:** {it.get('action_taken', 'N/A')}")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Passed", it.get("passed_rules", 0))
                        c2.metric("Failed", it.get("failed_rules", 0))
                        c3.metric("Failures", it.get("total_failures", 0))
                        c4.metric("Fixes", it.get("fixes_applied", 0))
            else:
                st.info("No agent iterations yet.")

        with history_tab[4]:
            api_results = st.session_state.db.get_api_validation_history(limit=30)
            if api_results:
                for api in api_results[:15]:
                    icon = "✅" if api.get("is_valid") else "❌"
                    st.markdown(f"{icon} **{api['email']}** | Status: {api.get('api_status', 'N/A')} | "
                                f"Confidence: {api.get('confidence_score', 0)} | {api.get('created_at', '')[:16]}")
            else:
                st.info("No API validation results yet.")

        with history_tab[5]:
            stats = st.session_state.db.get_statistics()
            if stats:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Runs", stats.get("validation_runs", 0))
                c2.metric("Total Rules Checked", stats.get("total_rules_checked", 0))
                c3.metric("Pass Rate", f"{stats.get('pass_rate', 0)}%")
                c4.metric("AI Analyses", stats.get("ai_analysis", 0))
                st.markdown("---")
                c5, c6, c7 = st.columns(3)
                c5.metric("Failed Records", stats.get("failed_records", 0))
                c6.metric("Remediations", stats.get("remediation_suggestions", 0))
                c7.metric("Agent Iterations", stats.get("agent_iterations", 0))
                st.markdown("---")
                if st.button("🗑️ Clear All History", type="secondary"):
                    st.session_state.db.clear_all_history()
                    st.success("All history cleared!")
                    st.rerun()
            else:
                st.info("No statistics available.")


# ═══════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — AI Insights, Fixes, Download
# ═══════════════════════════════════════════════════════════════════════════

def _render_right_panel():
    st.header("🧠 AI Insights")

    analyses = st.session_state.ai_analyses

    if not analyses:
        # Check if we have validation results but no AI analysis yet
        vr = st.session_state.validation_result
        if vr and not vr.all_passed:
            st.info("Run the Agent Loop to generate AI insights, or click below for quick analysis.")
            if st.button("⚡ Quick AI Analysis", use_container_width=True):
                _run_quick_analysis(vr)
        else:
            st.info("No AI insights yet. Run validation and the agent loop to generate insights.")
        return

    # LLM status
    llm = _get_llm_client()
    llm_status = llm.is_available()
    if llm_status:
        st.success(f"🟢 {llm.get_status()}")
    else:
        st.warning(f"🟡 {llm.get_status()} — using fallback analysis")

    # AI Analysis Cards
    for i, analysis in enumerate(analyses[:10]):
        rule_id = analysis.get("rule_id", f"R{i}")
        col = analysis.get("column", "unknown")
        rtype = analysis.get("rule_type", "unknown")

        with st.expander(f"🔍 {rule_id}: {col} → {rtype}", expanded=(i == 0)):
            # Severity & Confidence badges
            sev = analysis.get("severity", "medium")
            conf = analysis.get("confidence", 0)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Severity:** {sev.upper()}")
            with c2:
                st.markdown(f"**🎯 Confidence:** {conf}/100")
            with c3:
                st.markdown(f"**📊 Affected Rows:** {analysis.get('estimated_affected_rows', '—')}")

            st.markdown("---")

            # Root Cause Analysis
            st.markdown("**🔬 Root Cause Analysis**")
            st.markdown(analysis.get("root_cause", "N/A"))

            # Human Readable Explanation
            st.markdown("**💬 Explanation**")
            st.markdown(analysis.get("explanation", "N/A"))

            # Business Impact
            st.markdown("**💼 Business Impact**")
            st.markdown(analysis.get("business_impact", "N/A"))

            st.markdown("---")

            # SQL Fix
            st.markdown("**🗄️ SQL Fix**")
            st.code(analysis.get("sql_fix", "-- No fix available"), language="sql")

            # Pandas Fix
            st.markdown("**🐍 Pandas Fix**")
            st.code(analysis.get("pandas_fix", "# No fix available"), language="python")

            # Prevention
            st.markdown("**🛡️ Prevention**")
            st.markdown(analysis.get("prevention", "N/A"))

            # Permanent Fix
            st.markdown("**🔧 Permanent Fix**")
            st.markdown(analysis.get("permanent_fix", "N/A"))

            if analysis.get("fallback"):
                err = analysis.get("llm_error", "unknown")
                st.warning(f"⚠️ Fallback used — LLM error: `{err}`")
            elif analysis.get("provider"):
                st.caption(f"✅ Generated by {analysis['provider']} / {analysis.get('model', '')}")

    # Apply Fix & Download
    st.markdown("---")
    st.subheader("🔧 Actions")

    if st.session_state.cleaned_df is not None:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Apply Suggested Fix", use_container_width=True, type="primary"):
                st.session_state.df = st.session_state.cleaned_df
                st.session_state.validation_result = None
                st.success("Fix applied! Re-run validation to verify.")
                st.rerun()
        with c2:
            fixer = AutoFixer()
            csv_bytes = fixer.to_csv_bytes(st.session_state.cleaned_df)
            st.download_button(
                "⬇️ Download Cleaned CSV",
                data=csv_bytes,
                file_name="cleaned_data.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.caption("Run the agent loop to generate fix suggestions.")


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
