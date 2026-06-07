# Data Quality Agent with Auto-Fix Suggestions (DQ-FIX)

An intelligent data quality validation system that automatically detects, analyzes, and suggests fixes for data quality issues using AI/LLM integration. Built for hackathon demonstration.

## Features

- **30 Validation Types** — not_null, unique, range, regex, email, date, phone, allowed_values, numeric, positive, min/max_length, duplicate_row, future_date, placeholder, missing_threshold, outlier, cross_field, business_rule, data_consistency, data_freshness, and more
- **Multi-Provider AI** — Ollama (local/free), Groq (free API), OpenAI (paid)
- **Agent Loop** — Autonomous validate → analyze → fix → re-validate cycle (max 3 iterations)
- **AI-Powered Rule Generation** — Upload any CSV and LLM auto-generates validation rules
- **SQLite Persistence** — 7-table audit database tracking all validation history
- **Streamlit Dashboard** — 3-panel interactive UI with real-time results and audit history
- **External API Validation** — Email verification via emailvalidation.io
- **Severity & Confidence Scoring** — Calculated based on failure rate, rule type, and LLM availability

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Data Processing | Pandas, PyArrow |
| Dashboard | Streamlit |
| Database | SQLite3 (7 tables, WAL mode) |
| AI/LLM | Ollama, Groq, OpenAI APIs |
| Config | YAML, python-dotenv |
| Testing | Pytest (122 tests) |

## Project Structure

```
DQ-FIX/
├── app.py                          # Streamlit dashboard (main entry point)
├── config/
│   └── settings.py                 # All configuration settings
├── src/
│   ├── agent/
│   │   └── agent_loop.py           # Autonomous fix-revalidate loop
│   ├── ai/
│   │   ├── llm_client.py           # Multi-provider LLM integration
│   │   └── severity_engine.py      # Severity & confidence scoring
│   ├── api/
│   │   └── email_verifier.py       # External email validation API
│   ├── database/
│   │   └── db_manager.py           # SQLite 7-table persistence
│   ├── fixer/
│   │   └── auto_fixer.py           # Auto-fix suggestions
│   ├── readers/
│   │   ├── csv_reader.py           # CSV file reader
│   │   └── parquet_reader.py       # Parquet file reader
│   ├── rules/
│   │   └── rule_engine.py          # YAML rule parser (30 types)
│   ├── validators/
│   │   ├── result_models.py        # RuleResult & ValidationResult dataclasses
│   │   └── validation_engine.py    # 30 validator implementations
│   └── utils/
│       └── helpers.py              # Utility functions
├── tests/
│   ├── test_rule_engine.py         # Rule parsing tests
│   ├── test_validation_engine.py   # Validator tests (all 30 types)
│   ├── test_db_manager.py          # Database CRUD tests
│   └── test_llm_and_agent.py       # LLM client + Agent Loop tests
├── SAMPLE_DATA/
│   ├── valid_customers.csv
│   ├── invalid_customers.csv
│   ├── sample_rules.yaml           # 33 validation rules
│   └── expected_output.json
├── requirements.txt
└── .env                            # API keys (gitignored)
```

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd DQ-FIX
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_groq_key_here
OPENAI_API_KEY=sk-proj-your-openai-key-here
```

- **Groq** (free): Get key at https://console.groq.com → API Keys
- **OpenAI** (paid): Get key at https://platform.openai.com → API Keys
- **Ollama** (local): Install from https://ollama.ai, run `ollama pull llama3`

### 3. Run the Dashboard

```bash
streamlit run app.py
```

### 4. Run Tests

```bash
python -m pytest tests/ -v
```

## Usage

1. **Upload** a CSV or Parquet file using the left panel
2. **Preview** the data and column statistics
3. **Auto-Generate Rules** — Click the AI button to generate validation rules from your data
4. **Run Agent Loop** — The system validates data, analyzes failures with AI, applies fixes, and re-validates
5. **View Results** — Rule summary table, AI insights, and fix suggestions
6. **Audit History** — Browse all past runs in the History tab

## SQLite Database Schema (7 Tables)

| Table | Purpose |
|-------|---------|
| `validation_runs` | Track every validation execution |
| `validation_results` | Individual rule pass/fail per run |
| `failed_records` | Sample failed row data |
| `ai_analysis` | AI-generated root cause & explanations |
| `remediation_suggestions` | AI-generated SQL/Pandas fixes |
| `agent_iterations` | Agent Loop execution audit trail |
| `api_validation_results` | External API (email) validation results |

## AI Providers

| Provider | Model | Cost | Speed | Setup |
|----------|-------|------|-------|-------|
| Groq | llama-3.3-70b-versatile | Free | Fast | API key in .env |
| Ollama | llama3 (local) | Free | Medium | Install Ollama |
| OpenAI | gpt-4o-mini | Paid | Fast | API key in .env |

When no LLM is available, the system uses intelligent rule-based fallback analysis.

## Configuration

All settings are in `config/settings.py`:

- `DEFAULT_PROVIDER` — Default AI provider ("groq", "ollama", "openai")
- `MAX_AGENT_ITERATIONS` — Max fix-retry cycles (default: 3)
- `MAX_ROWS_PREVIEW` — Max rows in preview tables (default: 50)
- `DATABASE_PATH` — SQLite database location

## License

Hackathon project — for demonstration purposes.
