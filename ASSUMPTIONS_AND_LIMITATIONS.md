# Assumptions and Limitations — DQ-FIX Project

## Assumptions

### Data Assumptions
1. **CSV files are well-formed** — The CSV reader assumes standard CSV format with headers in the first row
2. **Column names are consistent** — Rules reference exact column names; mismatched names cause rule failures
3. **Data fits in memory** — All processing uses Pandas DataFrames loaded entirely into RAM
4. **Date formats are consistent** — Date validators expect a single format per column (specified in rule params)
5. **Numeric columns can be coerced** — Range/numeric validators use `pd.to_numeric(errors="coerce")`, converting non-numeric values to NaN

### AI/LLM Assumptions
1. **LLM responses are mostly valid JSON** — The 3-strategy parser handles common issues but cannot fix all malformed responses
2. **Groq API remains free** — The default provider relies on Groq's free tier availability
3. **LLM context window is sufficient** — Prompts include up to 5 sample rows and 40 columns; very wide datasets may exceed context limits
4. **Temperature 0.3 produces consistent results** — Low temperature for reproducibility, but LLM outputs are inherently non-deterministic

### Infrastructure Assumptions
1. **SQLite is single-writer** — WAL mode improves concurrency but SQLite is not designed for high-concurrency production use
2. **Streamlit session state persists** — Page refreshes lose all session state (data, rules, results)
3. **Local file paths work** — Database path and sample data paths are relative to the project directory
4. **Python 3.10+** — Code uses modern Python features (dataclasses, f-strings, walrus operator)

### Rule Engine Assumptions
1. **YAML files follow the expected schema** — Must have a `rules:` key with a list of rule mappings
2. **Rule IDs are unique within a file** — No duplicate ID enforcement, but duplicates may cause confusion
3. **Validation types are in the supported set** — 30 types are supported; unknown types are reported as errors
4. **Severity levels are low/medium/high** — Other values raise validation errors

## Limitations

### Data Processing Limitations
1. **Memory-bound** — Large datasets (>1GB) may cause memory issues since all data is loaded into Pandas DataFrames
2. **No streaming support** — Cannot process data incrementally or in real-time streams
3. **Single-file input** — Only processes one CSV/Parquet file at a time; no multi-file or database-source support
4. **No schema evolution tracking** — If column structure changes between runs, old rules may not apply
5. **Encoding detection is sequential** — Tries 5 encodings × 4 separators = 20 combinations; may be slow for large files

### Validation Limitations
1. **30 validation types only** — Cannot create custom validation types without modifying source code
2. **No cross-dataset validation** — Rules operate on a single DataFrame; cannot compare across datasets
3. **Business rules use eval()** — The `business_rule` validator uses Python `eval()` with restricted builtins; complex expressions may fail
4. **No fuzzy matching** — Email, phone, and regex validators use strict patterns; no tolerance for minor variations
5. **Row-level only** — No dataset-level aggregate validations (e.g., "total revenue > $1M")

### AI/LLM Limitations
1. **Non-deterministic output** — Same input may produce different analysis results each time
2. **No fine-tuning** — Uses base models (llama-3.3-70b, gpt-4o-mini) without domain-specific fine-tuning
3. **Limited context for fixes** — Only top 3 failures analyzed per iteration; remaining failures get template fixes
4. **No code execution** — Pandas/SQL fixes are suggestions only; the agent loop applies its own typed fixes
5. **Rate limits** — Groq free tier has rate limits; rapid consecutive requests may be throttled
6. **JSON parsing failures** — ~5-10% of LLM responses may fail to parse, falling back to template analysis
7. **No image/binary data support** — Only text/numeric data is analyzed; no image or binary column support

### Agent Loop Limitations
1. **Maximum 3 iterations** — Configurable but capped to prevent infinite loops
2. **Simple fix strategies** — Built-in fixes are basic (fillna median/mode, dedup, parse dates); complex transformations not supported
3. **No undo** — Fixes are applied in-place; cannot revert to original data within the loop
4. **No user intervention** — Fully autonomous; user cannot approve/reject individual fixes
5. **Fixes may introduce new issues** — Filling nulls with median may create outliers; dedup may remove valid records

### Database Limitations
1. **SQLite only** — No support for PostgreSQL, MySQL, or other production databases
2. **No backup/restore** — No built-in database backup or migration tooling
3. **No query optimization** — Simple queries without indexes on non-primary-key columns
4. **Thread safety** — `check_same_thread=False` allows cross-thread use but no write locking
5. **No data retention policy** — History grows indefinitely; no automatic cleanup

### Dashboard Limitations
1. **Single-user** — Streamlit is designed for single-user local apps; multi-user access shares session state unpredictably
2. **No authentication** — No login or access control
3. **No deployment config** — Not configured for cloud deployment (Streamlit Cloud, Docker, etc.)
4. **Limited visualization** — Uses basic Streamlit tables and text; no interactive charts or graphs
5. **Page refresh loses state** — All uploaded data and results are lost on browser refresh

### Security Limitations
1. **eval() in business rules** — Potential code injection risk if rules come from untrusted sources
2. **API keys in .env** — Stored in plaintext; not encrypted at rest
3. **No HTTPS enforcement** — Local Streamlit runs over HTTP by default
4. **No input sanitization** — Uploaded CSV data is not sanitized; malicious CSV content could cause unexpected behavior

## Future Improvements
- Add database source support (PostgreSQL, MySQL connectors)
- Implement production database backend (PostgreSQL with connection pooling)
- Add interactive charts (Plotly/Altair) for validation result visualization
- Support multi-file and cross-dataset validation
- Add user authentication and multi-user support
- Implement fine-tuned data quality model
- Add real-time/streaming data validation
- Docker deployment configuration
- CI/CD pipeline with automated testing
