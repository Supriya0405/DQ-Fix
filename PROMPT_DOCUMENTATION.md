# Prompt Documentation — DQ-FIX Project

All LLM prompts used in the Data Quality Agent system, documented for reproducibility and transparency.

## 1. Failure Analysis Prompt

**Location:** `src/ai/llm_client.py` → `_build_analysis_prompt()`

**Purpose:** Sent to the LLM when analyzing a validation failure to get structured root cause analysis and fix suggestions.

**System Message (for OpenAI-compatible APIs):**
```
You are a helpful data quality engineer. Respond only with valid JSON or YAML as requested.
```

**User Prompt Template:**
```
You are a Senior Data Engineer analyzing data quality failures.

VALIDATION FAILURE:
- Rule: {rule_type}
- Column: {column}
- Rule ID: {rule_id}
- Severity: {severity}
- Description: {description}
- Total rows checked: {total_rows}
- Failed rows: {failed_count}
- Failed row indices: {failed_row_indices[:10]}

ERROR DETAILS:
{error_details[:5]}

SAMPLE FAILED ROWS:
{sample_rows_df.head(5).to_string()}

COLUMN INFO: Column type: {dtype}

Respond in EXACTLY this JSON format (no markdown, no code blocks):
{
    "root_cause": "Detailed root cause analysis of why this failure occurred",
    "explanation": "Human readable explanation for a non-technical stakeholder",
    "business_impact": "What business impact this data quality issue creates",
    "sql_fix": "SQL UPDATE/DELETE statement to fix the data",
    "pandas_fix": "Python pandas code to fix the data (one line)",
    "prevention": "How to prevent this issue from recurring",
    "severity": "low or medium or high",
    "confidence": 85,
    "estimated_affected_rows": {failed_count},
    "permanent_fix": "Long-term solution recommendation"
}
```

**Parameters substituted:**
| Parameter | Source |
|-----------|--------|
| `rule_type` | `rule_result.rule_type` (e.g., "not_null", "range") |
| `column` | `rule_result.column` (e.g., "email", "age") |
| `rule_id` | `rule_result.rule_id` (e.g., "R001") |
| `severity` | `rule_result.severity` (low/medium/high) |
| `description` | `rule_result.description` from YAML |
| `total_rows` | `rule_result.total_rows` |
| `failed_count` | `rule_result.failed_count` |
| `failed_row_indices` | First 10 failed indices |
| `error_details` | First 5 error detail strings |
| `sample_rows_df` | First 5 failed rows as Pandas string |
| `dtype` | Column's Pandas dtype |

**API parameters:** `temperature=0.3`, `max_tokens=1024`

---

## 2. Auto-Rule Generation Prompt

**Location:** `src/ai/llm_client.py` → `generate_rules()`

**Purpose:** Sent to the LLM to generate YAML validation rules based on a dataset's structure and statistics.

**System Message:**
```
You are a helpful data quality engineer. Respond only with valid JSON or YAML as requested.
```

**User Prompt Template:**
```
You are an expert Data Quality Engineer. Analyze this EXACT dataset and generate
validation rules that PERFECTLY match its columns and data.

DATASET: {dataset_name}
TOTAL ROWS: {len(df)}
TOTAL COLUMNS: {len(df.columns)}

COLUMN DETAILS (use these EXACT column names in your rules):
{col_info}

IMPORTANT RULES:
1. Every rule MUST use an EXACT column name from the dataset above
2. Use the min/max/mean values shown to set realistic range params
3. Use sample values to determine allowed_values params
4. Generate 15-25 rules covering the most important columns
5. Focus on columns that have nulls, outliers, or specific patterns

VALID RULE TYPES: not_null, unique, range, regex, email, date, phone,
allowed_values, numeric, positive, min_length, max_length, duplicate_row,
future_date, date_format, placeholder, missing_threshold, outlier,
cross_field, business_rule, data_consistency

Respond with ONLY valid YAML (no markdown, no code blocks, no explanation):
rules:
  - id: R001
    column: exact_column_name_from_dataset
    type: rule_type
    description: "What this checks and why"
    severity: high/medium/low
    params:
      key: value
```

**Column Info Format (per column):**
```
- column_name: dtype=int64, nulls=5(2.5%), unique=200, min=18, max=95, mean=42.3, samples=[25, 30, 45, 60, 22]
```

**API parameters:** `temperature=0.3`, `max_tokens=4096`

**Post-processing:**
- Strip markdown code blocks if present
- Parse with `yaml.safe_load()` via `RuleEngine(yaml_content=...)`

---

## 3. Response Parsing Strategies

The LLM may not always return perfectly formatted JSON. The system handles this with 3 strategies:

### Strategy 1: Direct Parse
```python
data = json.loads(raw_response.strip())
```

### Strategy 2: Strip Markdown Code Blocks
```python
if cleaned.startswith("```"):
    cleaned = cleaned.split("\n", 1)[1]  # Remove ```json line
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]          # Remove closing ```
data = json.loads(cleaned)
```

### Strategy 3: Extract and Fix JSON
```python
start = raw_response.find("{")
end = raw_response.rfind("}")
json_str = raw_response[start:end+1]
# Fix trailing commas: ,} → } and ,] → ]
json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
# Fix unescaped newlines in strings
json_str = re.sub(r'(?<=:)\s*"([^"]*?)\n([^"]*?)"',
                  lambda m: f'"{m.group(1)} {m.group(2)}"', json_str)
data = json.loads(json_str)
```

---

## 4. Fallback Analysis Templates

When no LLM is available, the system uses rule-type-specific templates:

| Rule Type | SQL Fix | Pandas Fix |
|-----------|---------|------------|
| `not_null` | `DELETE FROM t WHERE col IS NULL` | `df.dropna(subset=['col'])` |
| `unique` | `DELETE FROM t WHERE rowid NOT IN (...)` | `df.drop_duplicates(subset=['col'])` |
| `range` | `UPDATE t SET col = NULL WHERE col < 0` | `df.loc[(...) , col] = None` |
| `positive` | `UPDATE t SET col = 0 WHERE col < 0` | `df.loc[df[col] < 0, col] = 0` |
| `email` | `UPDATE t SET col = NULL WHERE col NOT LIKE '%@%'` | Regex-based filter |
| `date` | `UPDATE t SET col = NULL WHERE format mismatch` | `pd.to_datetime(errors='coerce')` |
| `outlier` | `-- Review outliers` | Cap/review |

---

## 5. Fallback Rule Generation Heuristics

When no LLM is available, rules are generated based on column analysis:

| Condition | Rule Generated |
|-----------|---------------|
| Column has nulls | `not_null` |
| Column name contains "id" + all unique | `unique` |
| Numeric column | `range` (with min/max ± 10% margin) |
| Column name contains money keywords | `positive` |
| Column name contains "email" | `email` |
| Column name contains "date" or "dt_" | `date` |
| Object column with 2-15 unique values | `allowed_values` |
| Column name contains "phone" | `phone` |
| Column named "age" or "year_birth" | `range` (0-120 or 1900-2010) |
| Numeric column with >10 unique values | `outlier` |
| Always added | `duplicate_row` |
