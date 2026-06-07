"""
DQ-FIX Global Configuration Settings
=====================================
All project-wide settings live here. Single source of truth for configuration.
"""

import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, ".env"))  # Load API keys from .env file (gitignored)

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

# ─── External LLM Provider Configuration ───────────────────────────────────
# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  PASTE YOUR API KEY BELOW (for Groq or OpenAI)                       ║
# ║  Groq free key: https://console.groq.com → API Keys → Create         ║
# ║  OpenAI key:    https://platform.openai.com → API Keys               ║
# ╚═══════════════════════════════════════════════════════════════════════╝
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")       # Set in .env file (gitignored)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")   # Set in .env file (gitignored)

SUPPORTED_PROVIDERS = {
    "ollama": {
        "name": "Ollama (Local/Free)",
        "base_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "needs_key": False,
    },
    "groq": {
        "name": "Groq (Free API)",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "needs_key": True,
    },
    "openai": {
        "name": "OpenAI (Paid)",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "needs_key": True,
    },
}
DEFAULT_PROVIDER = "groq"  # groq=fast+free, ollama=local, openai=paid

# ─── Agent Loop Configuration ───────────────────────────────────────────────
MAX_AGENT_ITERATIONS = 3  # Maximum fix-retry cycles before stopping
AGENT_STOP_ON_SUCCESS = True  # Stop immediately when all validations pass

# ─── External API Configuration ─────────────────────────────────────────────
# emailvalidation.io — free key at https://app.emailvalidation.io → Dashboard
EMAIL_API_URL = "https://api.emailvalidation.io/v1/info"
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")

# ─── Validation Defaults ───────────────────────────────────────────────────
DEFAULT_SEVERITY_MAP = {
    # Core validations
    "not_null": "high",
    "unique": "high",
    "range": "medium",
    "regex": "medium",
    "email": "medium",
    "date": "low",
    "phone": "low",
    # Extended validations
    "allowed_values": "medium",
    "numeric": "medium",
    "positive": "medium",
    "min_length": "low",
    "max_length": "low",
    "duplicate_row": "high",
    "future_date": "medium",
    "date_format": "low",
    "placeholder": "medium",
    "missing_threshold": "high",
    "customer_id_pattern": "medium",
    "email_domain": "medium",
    "currency": "medium",
    "country": "low",
    "date_order": "medium",
    "age": "medium",
    "salary": "medium",
    "transaction_amount": "high",
    "outlier": "medium",
    "cross_field": "high",
    "business_rule": "high",
    "data_consistency": "high",
    "data_freshness": "low",
}

# ─── Confidence Scoring ────────────────────────────────────────────────────
CONFIDENCE_WEIGHTS = {
    "fix_success_rate": 0.40,   # How often the fix worked before
    "rule_clarity": 0.30,       # How specific the rule is
    "data_coverage": 0.30,      # How many rows the rule covers
}

# ─── Streamlit UI ──────────────────────────────────────────────────────────
APP_TITLE = "DQ-Fix Agent DE-02"
APP_ICON = "DQ"
MAX_ROWS_PREVIEW = 50  # Max rows shown in preview tables
