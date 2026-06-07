# Architecture — DQ-FIX Project

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard (app.py)                  │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ Left     │  │ Center           │  │ Right                 │  │
│  │ Panel    │  │ Panel            │  │ Panel                 │  │
│  │ - Upload │  │ - Data Preview   │  │ - Rule Summary        │  │
│  │ - Config │  │ - Column Stats   │  │ - Validation Results  │  │
│  │ - Rules  │  │ - Agent Loop     │  │ - AI Insights         │  │
│  │ - Run    │  │ - Progress       │  │ - Fix Suggestions     │  │
│  │          │  │                  │  │ - History Dashboard   │  │
│  └──────────┘  └──────────────────┘  └───────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Rule Engine    │ │ Validation      │ │  Agent Loop     │
│  (rule_engine)  │ │ Engine          │ │  (agent_loop)   │
│                 │ │ (validation_    │ │                 │
│  YAML Parser    │ │  engine.py)     │ │  Validate →     │
│  30 Rule Types  │ │                 │ │  Analyze →      │
│  Query Methods  │ │  30 Validators  │ │  Fix →          │
│  Validation     │ │  Dispatch Table │ │  Re-validate    │
└─────────────────┘ └────────┬────────┘ └────────┬────────┘
                             │                   │
                             ▼                   ▼
                  ┌─────────────────┐ ┌─────────────────┐
                  │ Result Models   │ │  LLM Client     │
                  │ (result_models) │ │  (llm_client)   │
                  │                 │ │                 │
                  │ RuleResult      │ │  Groq API       │
                  │ ValidationResult│ │  Ollama API     │
                  │ to_dataframe()  │ │  OpenAI API     │
                  └─────────────────┘ │  Fallback       │
                                      └────────┬────────┘
                                               │
                  ┌─────────────────┐ ┌────────┴────────┐
                  │ Severity Engine │ │  Database Mgr   │
                  │ (severity_      │ │  (db_manager)   │
                  │  engine.py)     │ │                 │
                  │                 │ │  7 Tables       │
                  │ Severity Calc   │ │  CRUD Ops       │
                  │ Confidence Calc │ │  WAL Mode       │
                  └─────────────────┘ │  Foreign Keys   │
                                      └─────────────────┘
```

## Data Flow

### 1. Upload Flow
```
User uploads CSV → CSVReader.read() → DataFrame + metadata
    → Session state stores df, info, file_name
    → Rule engine reset (ready for auto-generate)
```

### 2. Rule Generation Flow
```
User clicks "Auto-Generate Rules" →
    LLMClient.generate_rules(df, dataset_name) →
        Build column summary (dtype, nulls, min/max/mean, samples) →
        Send prompt to LLM (Groq/Ollama/OpenAI) →
        Parse YAML response →
        RuleEngine(yaml_content=yaml_str) →
        Session state stores rule_engine
```

### 3. Validation Flow
```
User clicks "Run Agent Loop" →
    AgentLoop.__init__(llm=configured_client) →
    AgentLoop.run(df, rules):
        for iteration in 1..max_iterations:
            ValidationEngine.validate(df, rules) → ValidationResult
            if all_passed: break
            For top 3 failures:
                LLMClient.analyze_failure(rule_result, samples, dtype)
                SeverityEngine.calculate_severity/confidence
            AgentLoop._apply_fixes(df, analyses)
                _apply_typed_fix(): not_null→fillna, unique→dedup, etc.
    Return: {iterations, final_df, status, history}
```

### 4. Database Persistence Flow
```
After Agent Loop completes:
    db.save_validation_run(dataset_name, rows, result, columns)
        → validation_runs (1 row)
        → validation_results (N rows, one per rule)
        → failed_records (sample failed rows)
    For each iteration:
        db.save_agent_iteration(run_id, iter, status, ...)
    For each AI analysis:
        db.save_ai_analysis(run_id, analysis_dict)
            → ai_analysis (1 row)
            → remediation_suggestions (1 row if sql/pandas fix exists)
    For each email validation:
        db.save_api_validation(email, result, run_id)
```

## Module Dependencies

```
app.py (Streamlit UI)
├── src/readers/csv_reader.py
├── src/readers/parquet_reader.py
├── src/rules/rule_engine.py
├── src/validators/validation_engine.py
│   └── src/rules/rule_engine.py (ValidationRule)
│   └── src/validators/result_models.py
├── src/agent/agent_loop.py
│   └── src/validators/validation_engine.py
│   └── src/ai/llm_client.py
│   └── src/ai/severity_engine.py
│   └── src/rules/rule_engine.py
│   └── src/validators/result_models.py
├── src/ai/llm_client.py
│   └── config/settings.py
├── src/database/db_manager.py
│   └── config/settings.py
└── src/api/email_verifier.py
```

## Design Decisions

### 1. YAML-Based Rule Configuration
- Rules defined in YAML for human readability
- Compatible with Great Expectations-style validation design
- Easy to version control and share

### 2. Dispatch Table Pattern
- ValidationEngine uses a `_DISPATCH` dict mapping rule types to methods
- O(1) lookup for validator execution
- Easy to add new validators

### 3. Multi-Provider LLM Abstraction
- Single `LLMClient` class supports 3 providers
- OpenAI-compatible API format for Groq and OpenAI
- Ollama uses its native API format
- Fallback analysis when no LLM available

### 4. SQLite with WAL Mode
- Write-Ahead Logging for better concurrency in Streamlit
- `check_same_thread=False` for multi-threaded Streamlit
- Foreign keys with CASCADE delete for data integrity
- Fresh connection per `_get_conn()` call

### 5. Agent Loop Design
- Maximum 3 iterations to prevent infinite loops
- Analyzes only top 3 failures per iteration (speed optimization)
- Built-in typed fixes (not_null, unique, duplicate_row, etc.)
- LLM-enhanced fixes when available

### 6. Session State Management
- Streamlit session state stores: df, info, rule_engine, validation results
- Upload ID tracking for reliable file change detection
- API key fallback from .env if session state is empty
