# AI Usage Note — DQ-FIX Project

## Overview of AI/LLM Integration

This project uses Large Language Models (LLMs) in two critical ways to enhance data quality validation beyond rule-based approaches.

## 1. Failure Analysis (AI-Powered Root Cause Analysis)

**When triggered:** After the validation engine identifies failures, the Agent Loop sends the top 3 failing rules to the LLM for deep analysis.

**What the AI does:**
- Analyzes the validation failure context (rule type, column, sample failed rows, data types)
- Generates a structured JSON response containing:
  - `root_cause` — Why the failure occurred
  - `explanation` — Human-readable description for non-technical stakeholders
  - `business_impact` — What business risk this creates
  - `sql_fix` — SQL statement to fix the data
  - `pandas_fix` — Python/Pandas code to fix the data
  - `prevention` — How to prevent recurrence
  - `confidence` — AI's confidence in the fix (0-100)
  - `permanent_fix` — Long-term solution recommendation

**Prompt design:** The system prompt includes the rule ID, type, column, severity, error details, sample failed rows, and column dtype — giving the LLM full context for accurate analysis.

**Fallback:** When no LLM is available (no API key, Ollama not running), the system uses pre-built rule-type-specific fix templates (not_null → dropna, unique → drop_duplicates, etc.)

## 2. Auto-Rule Generation (AI-Powered Schema Analysis)

**When triggered:** User clicks "Auto-Generate Rules (AI)" button after uploading a CSV.

**What the AI does:**
- Analyzes the uploaded dataset's column names, data types, null percentages, unique counts, min/max/mean values, and sample values
- Generates 15-25 YAML validation rules perfectly matched to the dataset
- Uses exact column names from the data (no guessing)
- Sets realistic parameter ranges based on actual data statistics

**Prompt design:** The prompt includes a detailed column summary with:
- Column name, dtype, null count/percentage
- Unique value count
- Min/max/mean for numeric columns
- 5 sample values per column
- List of valid rule types

The AI is instructed to use EXACT column names and realistic ranges from the provided statistics.

**Fallback:** When no LLM is available, a heuristic engine generates rules based on column name patterns (email → email validation, id → unique check, etc.) and data types.

## 3. Multi-Provider Support

| Provider | Use Case | API Format |
|----------|----------|-----------|
| **Groq** (default) | Free, fast cloud inference | OpenAI-compatible `/v1/chat/completions` |
| **Ollama** | Local/offline inference | `/api/generate` |
| **OpenAI** | Premium cloud inference | `/v1/chat/completions` |

## 4. JSON Response Parsing

LLMs sometimes return imperfect JSON (markdown wrappers, trailing commas, unescaped newlines). The system uses a 3-strategy parser:
1. Direct `json.loads()` parse
2. Strip markdown code blocks (```json ... ```)
3. Extract JSON between first `{` and last `}`, fix trailing commas and unescaped newlines

## 5. Confidence Scoring

Confidence scores (0-100) are calculated using weighted factors:
- **Fix Success Rate** (40%) — Historical success rate for this rule type
- **Rule Clarity** (30%) — Whether the rule has specific parameters
- **Data Coverage** (30%) — Percentage of data the rule covers

LLM availability adds a +10% bonus to the fix success rate factor.

## 6. Severity Escalation

Severity can be escalated based on failure context:
- >50% failure rate escalates `low` → `medium`
- >80% failure rate escalates `medium` → `high`

## 7. Data Privacy

- No data is sent to external APIs unless the user configures an API key
- Ollama provider keeps all data local (no network calls)
- API keys are stored in `.env` file (gitignored, never committed)
- Only sample failed rows (up to 5) are sent in LLM prompts
- No PII is explicitly extracted or stored separately
