"""
LLM Client — Multi-Provider Integration
========================================
Supports Ollama (local), Groq (free API), and OpenAI (paid API).
Provides failure analysis and auto-rule generation from CSV data.

Usage:
    from src.ai.llm_client import LLMClient
    client = LLMClient(provider="ollama")
    analysis = client.analyze_failure(rule_result, sample_rows, column_info)
    rules_yaml = client.generate_rules(df, dataset_name)
"""

import requests
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    SUPPORTED_PROVIDERS, DEFAULT_PROVIDER,
)


class LLMClient:
    """Connects to Ollama, Groq, or OpenAI and generates AI analysis."""

    def __init__(self, provider=None, api_key=None):
        self.provider = provider or DEFAULT_PROVIDER
        self.api_key = api_key or ""
        config = SUPPORTED_PROVIDERS.get(self.provider, SUPPORTED_PROVIDERS["ollama"])
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.needs_key = config["needs_key"]
        self._available_cache = None

    # ═══════════════════════════════════════════════════════════════════════
    # AVAILABILITY CHECK
    # ═══════════════════════════════════════════════════════════════════════

    def is_available(self) -> bool:
        """Check if the selected LLM provider is available (cached)."""
        if self._available_cache is not None:
            return self._available_cache

        if self.provider == "ollama":
            self._available_cache = self._check_ollama()
        elif self.needs_key:
            # For API-based providers, check if key is provided
            self._available_cache = bool(self.api_key and len(self.api_key) > 5)
        else:
            self._available_cache = True
        return self._available_cache

    def _check_ollama(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
            return False
        except Exception:
            return False

    def get_status(self) -> str:
        """Return human-readable status."""
        if self.is_available():
            return f"{self.provider.title()} / {self.model}"
        if self.needs_key and not self.api_key:
            return f"{self.provider.title()} — API key required"
        return f"{self.provider.title()} — not available"

    # ═══════════════════════════════════════════════════════════════════════
    # FAILURE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    def analyze_failure(self, rule_result, sample_rows_df=None, column_info=None) -> dict:
        """Send a validation failure to the LLM and get structured analysis."""
        if not self.is_available():
            return self._fallback_analysis(rule_result, f"{self.provider} not available")

        prompt = self._build_analysis_prompt(rule_result, sample_rows_df, column_info)

        try:
            response = self._call_llm(prompt)
            return self._parse_analysis_response(response, rule_result)
        except Exception as e:
            return self._fallback_analysis(rule_result, str(e))

    def _build_analysis_prompt(self, rule_result, sample_rows_df, column_info) -> str:
        sample_data = ""
        if sample_rows_df is not None and len(sample_rows_df) > 0:
            sample_data = sample_rows_df.head(5).to_string(index=False)

        col_info_str = ""
        if column_info:
            col_info_str = f"Column type: {column_info}"

        return f"""You are a Senior Data Engineer analyzing data quality failures.

VALIDATION FAILURE:
- Rule: {rule_result.rule_type}
- Column: {rule_result.column}
- Rule ID: {rule_result.rule_id}
- Severity: {rule_result.severity}
- Description: {rule_result.description}
- Total rows checked: {rule_result.total_rows}
- Failed rows: {rule_result.failed_count}
- Failed row indices: {rule_result.failed_row_indices[:10]}

ERROR DETAILS:
{chr(10).join(rule_result.error_details[:5])}

{f'SAMPLE FAILED ROWS:{chr(10)}{sample_data}' if sample_data else ''}
{f'COLUMN INFO: {col_info_str}' if col_info_str else ''}

Respond in EXACTLY this JSON format (no markdown, no code blocks):
{{
    "root_cause": "Detailed root cause analysis of why this failure occurred",
    "explanation": "Human readable explanation for a non-technical stakeholder",
    "business_impact": "What business impact this data quality issue creates",
    "sql_fix": "SQL UPDATE/DELETE statement to fix the data",
    "pandas_fix": "Python pandas code to fix the data (one line)",
    "prevention": "How to prevent this issue from recurring",
    "severity": "low or medium or high",
    "confidence": 85,
    "estimated_affected_rows": {rule_result.failed_count},
    "permanent_fix": "Long-term solution recommendation"
}}"""

    def _parse_analysis_response(self, raw_response: str, rule_result) -> dict:
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(raw_response[start:end])
                except json.JSONDecodeError:
                    return self._fallback_analysis(rule_result, "JSON parse failed")
            else:
                return self._fallback_analysis(rule_result, "No JSON in response")

        return {
            "root_cause": data.get("root_cause", "Unable to determine root cause"),
            "explanation": data.get("explanation", raw_response[:200]),
            "business_impact": data.get("business_impact", "Data quality issue may affect downstream processes"),
            "sql_fix": data.get("sql_fix", f"-- Fix for {rule_result.column} {rule_result.rule_type}"),
            "pandas_fix": data.get("pandas_fix", f"# Fix for {rule_result.column}"),
            "prevention": data.get("prevention", "Add input validation at data entry point"),
            "severity": data.get("severity", rule_result.severity),
            "confidence": min(100, max(0, int(data.get("confidence", 70)))),
            "estimated_affected_rows": data.get("estimated_affected_rows", rule_result.failed_count),
            "permanent_fix": data.get("permanent_fix", "Implement automated data quality checks"),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # AUTO-RULE GENERATION FROM CSV
    # ═══════════════════════════════════════════════════════════════════════

    def generate_rules(self, df, dataset_name="dataset") -> str:
        """
        Analyze a DataFrame and generate YAML validation rules using LLM.
        Returns a YAML string ready to be parsed by RuleEngine.
        """
        if not self.is_available():
            return self._fallback_generate_rules(df, dataset_name)

        # Build column summary for the LLM
        col_summary = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            nulls = int(df[col].isnull().sum())
            nunique = int(df[col].nunique())
            sample_vals = df[col].dropna().head(3).tolist()
            col_summary.append(
                f"- {col}: dtype={dtype}, nulls={nulls}, unique={nunique}, samples={sample_vals}"
            )
        col_info = "\n".join(col_summary[:30])  # limit to 30 columns

        prompt = f"""You are a Data Quality Engineer. Analyze this dataset and generate validation rules in YAML format.

DATASET: {dataset_name}
ROWS: {len(df)}
COLUMNS ({len(df.columns)}):
{col_info}

VALID RULE TYPES available:
not_null, unique, range, regex, email, date, phone, allowed_values, numeric, positive, min_length, max_length, duplicate_row, future_date, date_format, placeholder, missing_threshold, customer_id_pattern, email_domain, currency, country, date_order, age, salary, transaction_amount, outlier, cross_field, business_rule, data_consistency, data_freshness

Generate 15-25 rules that make sense for THIS specific dataset. Choose appropriate rule types based on column names and data types.

Respond with ONLY valid YAML (no markdown, no explanation):
rules:
  - id: R001
    column: column_name
    type: rule_type
    description: "What this checks"
    severity: high/medium/low
    params:
      key: value
"""

        try:
            response = self._call_llm(prompt, max_tokens=2048)
            # Clean up response
            yaml_str = response.strip()
            if yaml_str.startswith("```"):
                lines = yaml_str.split("\n")
                yaml_str = "\n".join(lines[1:])
                if yaml_str.endswith("```"):
                    yaml_str = yaml_str[:-3]
                yaml_str = yaml_str.strip()
            return yaml_str
        except Exception as e:
            return self._fallback_generate_rules(df, dataset_name, str(e))

    def _fallback_generate_rules(self, df, dataset_name="dataset", error_msg="") -> str:
        """Generate rules without LLM using column analysis heuristics."""
        rules = []
        rule_id = 1

        for col in df.columns:
            dtype = str(df[col].dtype)
            nulls = int(df[col].isnull().sum())
            nunique = int(df[col].nunique())
            col_lower = col.lower()

            # Not null check for important columns
            if nulls > 0:
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "not_null",
                    "description": f"Ensure {col} is not null",
                    "severity": "high" if nulls > len(df) * 0.3 else "medium",
                })
                rule_id += 1

            # Unique check for ID-like columns
            if "id" in col_lower and nunique == len(df):
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "unique",
                    "description": f"Ensure {col} is unique", "severity": "high",
                })
                rule_id += 1

            # Range for numeric columns
            if "int" in dtype or "float" in dtype:
                mn = float(df[col].min()) if df[col].notna().any() else 0
                mx = float(df[col].max()) if df[col].notna().any() else 100
                margin = (mx - mn) * 0.1 if mx > mn else 1
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "range",
                    "description": f"Ensure {col} is within expected range",
                    "severity": "medium",
                    "params": {"min": round(mn - margin, 2), "max": round(mx + margin, 2)},
                })
                rule_id += 1

            # Positive check for amount/money/income columns
            money_keywords = ["income", "amount", "salary", "price", "cost", "revenue",
                              "mnt", "spend", "payment", "fee"]
            if any(kw in col_lower for kw in money_keywords):
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "positive",
                    "description": f"Ensure {col} is positive", "severity": "high",
                })
                rule_id += 1

            # Email validation
            if "email" in col_lower:
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "email",
                    "description": f"Validate email format in {col}", "severity": "medium",
                })
                rule_id += 1

            # Date validation
            if "date" in col_lower or "dt_" in col_lower:
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "date",
                    "description": f"Validate date format in {col}", "severity": "low",
                })
                rule_id += 1

            # Allowed values for categorical columns
            if dtype == "object" and 2 <= nunique <= 15:
                vals = df[col].dropna().unique().tolist()
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "allowed_values",
                    "description": f"Ensure {col} has valid values",
                    "severity": "medium",
                    "params": {"values": vals},
                })
                rule_id += 1

            # Phone validation
            if "phone" in col_lower or "mobile" in col_lower:
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "phone",
                    "description": f"Validate phone format in {col}", "severity": "low",
                })
                rule_id += 1

            # Age validation
            if col_lower in ["age", "year_birth"]:
                if col_lower == "year_birth":
                    rules.append({
                        "id": f"R{rule_id:03d}", "column": col, "type": "range",
                        "description": f"Ensure {col} is valid year", "severity": "high",
                        "params": {"min": 1900, "max": 2010},
                    })
                else:
                    rules.append({
                        "id": f"R{rule_id:03d}", "column": col, "type": "range",
                        "description": f"Ensure {col} is valid", "severity": "high",
                        "params": {"min": 0, "max": 120},
                    })
                rule_id += 1

            # Outlier detection for numeric
            if ("int" in dtype or "float" in dtype) and nunique > 10:
                rules.append({
                    "id": f"R{rule_id:03d}", "column": col, "type": "outlier",
                    "description": f"Detect outliers in {col}", "severity": "medium",
                })
                rule_id += 1

            # Stop if we have enough rules
            if rule_id > 25:
                break

        # Add duplicate row check
        rules.append({
            "id": f"R{rule_id:03d}", "column": "_all", "type": "duplicate_row",
            "description": "Check for duplicate rows", "severity": "high",
        })

        # Build YAML string
        import yaml
        yaml_str = yaml.dump({"rules": rules}, default_flow_style=False, sort_keys=False)
        return yaml_str

    # ═══════════════════════════════════════════════════════════════════════
    # LLM API CALLS (Multi-Provider)
    # ═══════════════════════════════════════════════════════════════════════

    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call the selected LLM provider."""
        if self.provider == "ollama":
            return self._call_ollama(prompt, max_tokens)
        else:
            return self._call_openai_compatible(prompt, max_tokens)

    def _call_ollama(self, prompt: str, max_tokens: int) -> str:
        """Call the Ollama API."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": max_tokens,
            },
        }
        response = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def _call_openai_compatible(self, prompt: str, max_tokens: int) -> str:
        """Call OpenAI-compatible APIs (OpenAI, Groq)."""
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful data quality engineer. Respond only with valid JSON or YAML as requested."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    # ═══════════════════════════════════════════════════════════════════════
    # FALLBACK ANALYSIS (No LLM)
    # ═══════════════════════════════════════════════════════════════════════

    def _fallback_analysis(self, rule_result, error_msg: str) -> dict:
        """Generate analysis without LLM."""
        type_fixes = {
            "not_null": {
                "sql": f"DELETE FROM table_name WHERE {rule_result.column} IS NULL;",
                "pandas": f"df = df.dropna(subset=['{rule_result.column}'])",
                "root": f"Column '{rule_result.column}' contains {rule_result.failed_count} null values.",
            },
            "unique": {
                "sql": f"DELETE FROM table_name WHERE rowid NOT IN (SELECT MIN(rowid) FROM table_name GROUP BY {rule_result.column});",
                "pandas": f"df = df.drop_duplicates(subset=['{rule_result.column}'], keep='first')",
                "root": f"Column '{rule_result.column}' has {rule_result.failed_count} duplicate values.",
            },
            "range": {
                "sql": f"UPDATE table_name SET {rule_result.column} = NULL WHERE {rule_result.column} < 0 OR {rule_result.column} > 120;",
                "pandas": f"df.loc[(df['{rule_result.column}'] < 0) | (df['{rule_result.column}'] > 120), '{rule_result.column}'] = None",
                "root": f"Column '{rule_result.column}' has values outside expected range.",
            },
            "positive": {
                "sql": f"UPDATE table_name SET {rule_result.column} = 0 WHERE {rule_result.column} < 0;",
                "pandas": f"df.loc[df['{rule_result.column}'] < 0, '{rule_result.column}'] = 0",
                "root": f"Column '{rule_result.column}' has negative values.",
            },
            "outlier": {
                "sql": f"-- Review outliers in {rule_result.column}",
                "pandas": f"# Review and cap outliers in {rule_result.column}",
                "root": f"Column '{rule_result.column}' has statistical outliers.",
            },
            "email": {
                "sql": f"UPDATE table_name SET {rule_result.column} = NULL WHERE {rule_result.column} NOT LIKE '%_@_%.__%';",
                "pandas": f"df.loc[~df['{rule_result.column}'].str.contains(r'@.*\\.', na=False), '{rule_result.column}'] = None",
                "root": f"Column '{rule_result.column}' has invalid email formats.",
            },
            "date": {
                "sql": f"UPDATE table_name SET {rule_result.column} = NULL WHERE {rule_result.column} NOT LIKE '____-__-__';",
                "pandas": f"df['{rule_result.column}'] = pd.to_datetime(df['{rule_result.column}'], errors='coerce')",
                "root": f"Column '{rule_result.column}' has invalid date formats.",
            },
        }

        fix = type_fixes.get(rule_result.rule_type, {
            "sql": f"-- Manual review needed for {rule_result.column}",
            "pandas": f"# Manual review needed for {rule_result.column}",
            "root": f"Column '{rule_result.column}' failed {rule_result.rule_type} with {rule_result.failed_count} failures.",
        })

        return {
            "root_cause": fix["root"],
            "explanation": f"The {rule_result.rule_type} check on '{rule_result.column}' found {rule_result.failed_count} issues.",
            "business_impact": "Data quality issues may cause incorrect reporting or downstream errors.",
            "sql_fix": fix["sql"],
            "pandas_fix": fix["pandas"],
            "prevention": f"Add {rule_result.rule_type} validation at data ingestion.",
            "severity": rule_result.severity,
            "confidence": 60,
            "estimated_affected_rows": rule_result.failed_count,
            "permanent_fix": f"Implement automated {rule_result.rule_type} checks.",
            "fallback": True,
            "llm_error": error_msg,
        }
