"""Professional dark-theme CSS and HTML card helpers for the DQ-FIX dashboard."""

import html


def inject_global_css():
    """Return CSS string to inject via st.markdown(unsafe_allow_html=True)."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}

.stApp {
    background: linear-gradient(145deg, #0b0b14 0%, #10102a 50%, #0d0d1a 100%);
}

section[data-testid="stSidebar"] {
    background: #0e0e1c !important;
    border-right: 1px solid rgba(124, 58, 237, 0.15);
}

section[data-testid="stSidebar"] .stRadio > label {
    display: none;
}

section[data-testid="stSidebar"] .stRadio > div {
    gap: 4px;
}

section[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
    background: transparent;
    border-radius: 8px;
    padding: 10px 14px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
    width: 100%;
}

section[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:hover {
    background: rgba(124, 58, 237, 0.1);
    border-color: rgba(124, 58, 237, 0.2);
}

section[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"][aria-checked="true"] {
    background: rgba(124, 58, 237, 0.18) !important;
    border-color: rgba(124, 58, 237, 0.4) !important;
}

.dq-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 20px 0;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.dq-header-left {
    display: flex;
    align-items: center;
    gap: 14px;
}

.dq-logo {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    color: white;
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
}

.dq-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #f0f0f8;
    margin: 0;
    letter-spacing: -0.02em;
}

.dq-header-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.dq-pulse {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: #94a3b8;
}

.dq-pulse-dot {
    width: 8px;
    height: 8px;
    background: #3b82f6;
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 8px #3b82f6;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
}

.dq-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.dq-badge-green {
    background: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ade80;
}

.dq-badge-purple {
    background: rgba(124, 58, 237, 0.12);
    border: 1px solid rgba(124, 58, 237, 0.35);
    color: #a78bfa;
}

.dq-card {
    background: rgba(26, 26, 46, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 16px;
    backdrop-filter: blur(8px);
}

.dq-card-sm { min-height: 110px; }

.dq-card-label {
    font-size: 0.78rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
    margin-bottom: 8px;
}

.dq-card-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.1;
    letter-spacing: -0.03em;
}

.dq-card-sub {
    font-size: 0.82rem;
    color: #64748b;
    margin-top: 8px;
}

.dq-trend-up {
    color: #4ade80;
    font-size: 0.82rem;
    font-weight: 500;
}

.dq-trend-down {
    color: #f87171;
    font-size: 0.82rem;
    font-weight: 500;
}

.dq-section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 16px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.dq-rule-badge {
    font-size: 0.7rem;
    padding: 4px 10px;
    border-radius: 6px;
    background: rgba(100, 116, 139, 0.2);
    color: #94a3b8;
    font-weight: 500;
}

.dq-failure-item {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    gap: 12px;
}

.dq-failure-item:last-child { border-bottom: none; }

.dq-failure-name {
    font-size: 0.88rem;
    font-weight: 600;
    color: #e2e8f0;
    font-family: 'Consolas', 'Monaco', monospace;
    margin-bottom: 4px;
}

.dq-failure-desc {
    font-size: 0.8rem;
    color: #64748b;
    line-height: 1.4;
}

.dq-sev {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    flex-shrink: 0;
}

.dq-sev-critical { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.dq-sev-high { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }
.dq-sev-medium { background: rgba(249, 115, 22, 0.15); color: #fdba74; border: 1px solid rgba(249,115,22,0.25); }
.dq-sev-low { background: rgba(100, 116, 139, 0.2); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }

.dq-code-label {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 14px 0 6px 0;
    font-weight: 600;
}

.dq-code-block {
    background: #0d0d1a;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.78rem;
    color: #a5b4fc;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

.dq-insight-text {
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin-top: 8px;
}

.dq-confidence {
    display: inline-block;
    margin-top: 12px;
    font-size: 0.8rem;
    color: #7c3aed;
    font-weight: 600;
}

.dq-sidebar-brand {
    padding: 8px 4px 20px 4px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 16px;
}

.dq-sidebar-brand-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #e2e8f0;
}

.dq-sidebar-brand-sub {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 2px;
}

.dq-empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #64748b;
    font-size: 0.9rem;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #6366f1) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35) !important;
    transition: all 0.2s ease !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(124, 58, 237, 0.5) !important;
    transform: translateY(-1px);
}

div[data-testid="stMetric"] {
    background: rgba(26, 26, 46, 0.6);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 12px 16px;
}

div[data-testid="stExpander"] {
    background: rgba(26, 26, 46, 0.5);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
}

.dq-steps {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 24px;
    padding: 16px 20px;
    background: rgba(26, 26, 46, 0.6);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
}

.dq-step {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
}

.dq-step-num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 700;
}

.dq-step-pending .dq-step-num {
    background: rgba(100, 116, 139, 0.2);
    color: #64748b;
    border: 1px solid rgba(100, 116, 139, 0.3);
}

.dq-step-active .dq-step-num {
    background: linear-gradient(135deg, #7c3aed, #6366f1);
    color: white;
    box-shadow: 0 0 12px rgba(124, 58, 237, 0.4);
}

.dq-step-done .dq-step-num {
    background: rgba(34, 197, 94, 0.2);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.4);
}

.dq-step-label {
    font-size: 0.82rem;
    font-weight: 500;
    color: #94a3b8;
}

.dq-step-active .dq-step-label { color: #e2e8f0; }
.dq-step-done .dq-step-label { color: #4ade80; }

.dq-step-line {
    flex: 1;
    height: 2px;
    background: rgba(255,255,255,0.08);
    margin: 0 12px;
    min-width: 24px;
}

.dq-wf-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

.dq-wf-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.dq-wf-active .dq-wf-badge {
    background: rgba(124, 58, 237, 0.2);
    color: #a78bfa;
    border: 1px solid rgba(124, 58, 237, 0.3);
}

.dq-wf-done .dq-wf-badge {
    background: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.dq-wf-title {
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
}

.dq-setup-card {
    background: rgba(26, 26, 46, 0.5);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 8px;
}
</style>
"""


def _esc(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def severity_class(severity: str) -> str:
    sev = (severity or "medium").lower()
    if sev == "critical":
        return "dq-sev-critical"
    if sev == "high":
        return "dq-sev-high"
    if sev == "low":
        return "dq-sev-low"
    return "dq-sev-medium"


def severity_label(severity: str) -> str:
    sev = (severity or "medium").lower()
    labels = {
        "critical": "Critical",
        "high": "High Severity",
        "medium": "Medium Severity",
        "low": "Low Severity",
    }
    return labels.get(sev, sev.title() + " Severity")


def header_html(title: str, agent_status: str = "Idle", iteration: int = 0,
                dataset_name: str = None, agent_active: bool = False) -> str:
    status_text = agent_status.replace("_", " ").title()
    if agent_active and iteration > 0:
        pulse = f'<span class="dq-pulse"><span class="dq-pulse-dot"></span>Agent Loop Active (Iteration {iteration})</span>'
    else:
        pulse = f'<span class="dq-pulse"><span class="dq-pulse-dot" style="background:#64748b;box-shadow:none;"></span>{status_text}</span>'

    dataset_badge = ""
    if dataset_name:
        dataset_badge = f'<span class="dq-badge dq-badge-green">Processing: {_esc(dataset_name.upper())}</span>'

    return f"""
<div class="dq-header">
    <div class="dq-header-left">
        <div class="dq-logo">DQ</div>
        <h1 class="dq-title">{_esc(title)}</h1>
    </div>
    <div class="dq-header-right">
        {pulse}
        {dataset_badge}
    </div>
</div>
"""


def metric_card(label: str, value: str, sub: str = "", trend: str = "", trend_up: bool = True) -> str:
    trend_html = ""
    if trend:
        cls = "dq-trend-up" if trend_up else "dq-trend-down"
        trend_html = f'<div class="{cls}">{_esc(trend)}</div>'
    sub_html = f'<div class="dq-card-sub">{_esc(sub)}</div>' if sub else ""
    return f"""
<div class="dq-card dq-card-sm">
    <div class="dq-card-label">{_esc(label)}</div>
    <div class="dq-card-value">{_esc(value)}</div>
    {trend_html}
    {sub_html}
</div>
"""


def insight_card(title: str, text: str, confidence: float = None) -> str:
    conf_html = ""
    if confidence is not None:
        conf_html = f'<div class="dq-confidence">Confidence Score: {confidence:.0f}%</div>'
    return f"""
<div class="dq-card" style="min-height:110px;">
    <div class="dq-card-label">{_esc(title)}</div>
    <div class="dq-insight-text">{_esc(text)}</div>
    {conf_html}
</div>
"""


def failure_item(rule_id: str, description: str, severity: str) -> str:
    return f"""
<div class="dq-failure-item">
    <div>
        <div class="dq-failure-name">{_esc(rule_id)}</div>
        <div class="dq-failure-desc">{_esc(description)}</div>
    </div>
    <span class="dq-sev {severity_class(severity)}">{_esc(severity_label(severity))}</span>
</div>
"""


def failures_card(failures: list, rule_engine_label: str = "Great Expectations Standard") -> str:
    if not failures:
        items = '<div class="dq-empty-state">No validation failures — all rules passed</div>'
    else:
        items = "".join(
            failure_item(
                f.get("rule_id", "unknown"),
                f.get("description", ""),
                f.get("severity", "medium"),
            )
            for f in failures
        )
    return f"""
<div class="dq-card">
    <div class="dq-section-title">
        <span>Current Validation Failures</span>
        <span class="dq-rule-badge">Rule: {_esc(rule_engine_label)}</span>
    </div>
    {items}
</div>
"""


def remediation_card(sql_fix: str, pandas_fix: str, provider: str = "LLAMA3-OLLAMA") -> str:
    sql = _esc(sql_fix or "-- No SQL fix available")
    pandas = _esc(pandas_fix or "# No pandas fix available")
    return f"""
<div class="dq-card">
    <div class="dq-section-title"><span>Remediation Proposal</span></div>
    <div class="dq-code-label">SQL Remediator ({_esc(provider.upper())})</div>
    <div class="dq-code-block">{sql}</div>
    <div class="dq-code-label">Pandas Auto-Fix</div>
    <div class="dq-code-block">{pandas}</div>
</div>
"""


def sidebar_brand_html() -> str:
    return """
<div class="dq-sidebar-brand">
    <div class="dq-sidebar-brand-title">DQ-Fix Agent</div>
    <div class="dq-sidebar-brand-sub">Data Quality Dashboard</div>
</div>
"""


def step_indicator_html(steps: list) -> str:
    """Render a horizontal step progress bar. Each step: {label, status: done|active|pending}."""
    items = []
    for i, step in enumerate(steps):
        status = step.get("status", "pending")
        num = i + 1
        connector = '<div class="dq-step-line"></div>' if i < len(steps) - 1 else ""
        items.append(
            f'<div class="dq-step dq-step-{status}">'
            f'<div class="dq-step-num">{num}</div>'
            f'<div class="dq-step-label">{_esc(step.get("label", ""))}</div>'
            f'</div>{connector}'
        )
    return f'<div class="dq-steps">{"".join(items)}</div>'


def workflow_step_header(step_num: int, title: str, done: bool = False) -> str:
    badge = "Done" if done else f"Step {step_num}"
    cls = "dq-wf-done" if done else "dq-wf-active"
    return f"""
<div class="dq-wf-header {cls}">
    <span class="dq-wf-badge">{badge}</span>
    <span class="dq-wf-title">{_esc(title)}</span>
</div>
"""
