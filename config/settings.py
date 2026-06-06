"""
DQ-FIX Global Configuration Settings
=====================================
All project-wide settings live here. Single source of truth for configuration.
"""

import os

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "SAMPLE_DATA")
DATABASE_PATH = os.path.join(BASE_DIR, "dq_results.db")
DEFAULT_RULES_PATH = os.path.join(SAMPLE_DATA_DIR, "sample_rules.yaml")

# ─── Ollama / LLM Configuration ────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_API_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds

# ─── Agent Loop Configuration ───────────────────────────────────────────────
MAX_AGENT_ITERATIONS = 3  # Maximum fix-retry cycles before stopping
AGENT_STOP_ON_SUCCESS = True  # Stop immediately when all validations pass

# ─── External API Configuration ─────────────────────────────────────────────
# Using emailvalidation.io free tier (no API key needed for basic checks)
EMAIL_API_URL = "https://api.emailvalidation.io/v1/info"
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")

# ─── Validation Defaults ───────────────────────────────────────────────────
DEFAULT_SEVERITY_MAP = {
    "not_null": "high",
    "unique": "high",
    "range": "medium",
    "regex": "medium",
    "email": "medium",
    "date": "low",
    "phone": "low",
}

# ─── Confidence Scoring ────────────────────────────────────────────────────
CONFIDENCE_WEIGHTS = {
    "fix_success_rate": 0.40,   # How often the fix worked before
    "rule_clarity": 0.30,       # How specific the rule is
    "data_coverage": 0.30,      # How many rows the rule covers
}

# ─── Streamlit UI ──────────────────────────────────────────────────────────
APP_TITLE = "Data Quality Agent — Auto-Fix Suggestions"
APP_ICON = "🔧"
MAX_ROWS_PREVIEW = 50  # Max rows shown in preview tables
