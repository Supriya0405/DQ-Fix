# Demo Script — DQ-FIX Hackathon Presentation

## Setup (Before Demo)

1. Ensure `.env` file has Groq API key
2. Run: `streamlit run app.py`
3. Have a CSV file ready with intentional data quality issues

## Demo Flow (15 minutes)

---

### Part 1: Introduction (2 min)

**Say:** "This is DQ-FIX — a Data Quality Agent that automatically detects, analyzes, and fixes data quality issues using AI."

**Show:** The 3-panel Streamlit dashboard

**Key points:**
- Left panel: Configuration and controls
- Center panel: Data preview and agent execution
- Right panel: Results, AI insights, and audit history

---

### Part 2: Upload & Preview (2 min)

**Action:** Upload a CSV file with data quality issues

**Say:** "Upload any CSV file and the system immediately shows a data preview with column statistics — null counts, data types, unique values, and sample data."

**Show:**
- Data preview table
- Column statistics (rows, columns, null counts)

---

### Part 3: AI Auto-Generate Rules (3 min)

**Action:** Click "Auto-Generate Rules (AI)" button

**Say:** "Instead of writing validation rules manually, the AI analyzes the dataset structure — column names, data types, value distributions — and generates 15-25 validation rules perfectly matched to this data."

**Show:**
- Loading spinner while Groq generates rules
- Rule summary table with all generated rules
- Rule count and severity breakdown

**Technical note:** "The prompt includes exact column names, null percentages, min/max/mean for numeric columns, and sample values — so the AI generates rules with realistic parameters."

---

### Part 4: Run Agent Loop (4 min)

**Action:** Click "Run Agent Loop" button

**Say:** "Now the Agent Loop runs autonomously: validate, analyze failures with AI, apply fixes, and re-validate — up to 3 iterations."

**Show:**
- Progress bar for each iteration
- Iteration status (passed rules, failed rules, fixes applied)
- Final result summary

**After completion, show:**
- **Rule Summary** table: PASS/FAIL status for each rule
- **AI Insights**: Root cause analysis, business impact, SQL/Pandas fix suggestions
- **Fix Suggestions**: Confidence scores and severity levels

**Say:** "For each failure, the AI provides: root cause analysis, business impact assessment, SQL and Pandas fix code, prevention recommendations, and a confidence score."

---

### Part 5: Audit History (2 min)

**Action:** Click on "History" tab in the right panel

**Show:**
- **Runs tab**: All validation runs with timestamps, pass/fail counts
- **AI Analysis tab**: Historical AI analyses with provider info (Groq)
- **Remediations tab**: SQL/Pandas fix suggestions
- **Agent Loop tab**: Iteration-by-iteration audit trail
- **Stats tab**: Overall statistics (total runs, pass rate, table counts)

**Say:** "Everything is persisted in SQLite — 7 tables tracking validation runs, individual results, failed records, AI analyses, remediation suggestions, agent iterations, and API validations."

---

### Part 6: Technical Deep Dive (2 min)

**Show:** Architecture diagram (ARCHITECTURE.md)

**Key talking points:**
1. **30 Validation Types** — From basic (not_null, unique, range) to advanced (outlier, cross_field, business_rule, data_consistency)
2. **Multi-Provider AI** — Groq (free), Ollama (local), OpenAI (paid) with automatic fallback
3. **Agent Loop** — Autonomous validate → analyze → fix → re-validate cycle
4. **SQLite Persistence** — 7-table audit database with CASCADE deletes and WAL mode
5. **122 Pytest Tests** — Comprehensive test coverage across all modules

---

## Talking Points for Q&A

### "How does it handle when the AI is unavailable?"
"The system has intelligent fallback analysis — pre-built templates for each rule type that generate SQL/Pandas fixes based on the rule type and column statistics. The system never breaks if AI is unavailable."

### "How accurate are the AI-generated rules?"
"The prompt includes exact column names and real data statistics (min/max/mean, null percentages, sample values). The AI is instructed to use EXACT column names and realistic ranges. We also have a 3-strategy JSON/YAML parser that handles common LLM output issues."

### "What happens with very large datasets?"
"The system processes data in Pandas DataFrames, so it's memory-bound. For hackathon-scale data (up to ~100K rows), it works perfectly. For production, we'd add database-source connectors and streaming."

### "How is the Agent Loop prevented from infinite loops?"
"Maximum 3 iterations, configurable in settings. The loop stops early if all validations pass. Each iteration analyzes only the top 3 failures to keep processing time reasonable."

### "What data is sent to the AI?"
"Only rule metadata and up to 5 sample failed rows per analysis. No entire datasets are sent. Column names, data types, and error details are included for context."

### "How does the SQLite database work?"
"7 tables with foreign keys and CASCADE deletes: validation_runs, validation_results, failed_records, ai_analysis, remediation_suggestions, agent_iterations, api_validation_results. Uses WAL mode for better concurrency in Streamlit."

## Demo Data Suggestion

Create a CSV with these intentional issues:
- Null values in required fields
- Duplicate IDs
- Invalid emails
- Out-of-range ages
- Future dates
- Placeholder values (N/A, TBD)
- Negative amounts
- Inconsistent country codes

This will trigger multiple validation types and showcase the AI analysis capabilities.
