"""
Validation Engine (30 Validators)
=================================
Executes validation rules against a Pandas DataFrame.
Implements all 30 validation types with backward compatibility.

Usage:
    from src.validators.validation_engine import ValidationEngine
    engine = ValidationEngine()
    result = engine.validate(df, rules)
"""

import re
import pandas as pd
import numpy as np
from typing import List
from datetime import datetime, date

from src.rules.rule_engine import ValidationRule
from src.validators.result_models import RuleResult, ValidationResult


class ValidationEngine:
    """Executes validation rules against a DataFrame and returns structured results."""

    def validate(self, df: pd.DataFrame, rules: List[ValidationRule]) -> ValidationResult:
        """Run all rules against the DataFrame."""
        results: List[RuleResult] = []
        for rule in rules:
            if rule.column not in df.columns and rule.type not in ("duplicate_row", "missing_threshold", "data_freshness", "cross_field", "business_rule", "data_consistency", "date_order"):
                results.append(self._build_result(rule, len(df), list(range(len(df))),
                    [f"Column '{rule.column}' not in dataset"] * len(df), df))
                continue
            try:
                validator = self._DISPATCH.get(rule.type)
                if validator is None:
                    results.append(self._build_result(rule, len(df), list(range(len(df))),
                        [f"Unknown rule type: {rule.type}"] * len(df), df))
                    continue
                result = validator(self, df, rule)
                results.append(result)
            except Exception as e:
                results.append(self._build_result(rule, len(df), list(range(len(df))),
                    [f"Validator error: {e}"] * len(df), df))

        passed_rules = sum(1 for r in results if r.passed)
        return ValidationResult(
            total_rules=len(results), passed_rules=passed_rules,
            failed_rules=len(results) - passed_rules,
            total_failures=sum(r.failed_count for r in results if not r.passed),
            results=results,
        )

    def _build_result(self, rule, total_rows, failed_indices, error_details, df) -> RuleResult:
        """Helper to build a RuleResult."""
        return RuleResult(
            rule_id=rule.id, rule_type=rule.type, column=rule.column,
            severity=rule.severity, description=rule.description,
            passed=len(failed_indices) == 0, total_rows=total_rows,
            passed_count=total_rows - len(failed_indices),
            failed_count=len(failed_indices),
            failed_row_indices=failed_indices, error_details=error_details,
            failed_samples=df.iloc[failed_indices] if failed_indices and len(failed_indices) <= 100 else None,
        )

    def _non_null_mask(self, col):
        """Mask for non-null, non-empty values."""
        mask = col.notna()
        if col.dtype == object:
            mask = mask & (col.astype(str).str.strip() != "")
        return mask

    # ═══════════════════════════════════════════════════════════════════════
    # CORE VALIDATORS (Original 7)
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_not_null(self, df, rule):
        col = df[rule.column]
        mask = col.isna() | col.isnull()
        if col.dtype == object:
            mask = mask | (col.astype(str).str.strip() == "")
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' is null or empty" for i in fi], df)

    def _validate_unique(self, df, rule):
        col = df[rule.column]
        mask = col.duplicated(keep="first")
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is duplicated" for i in fi], df)

    def _validate_range(self, df, rule):
        col = pd.to_numeric(df[rule.column], errors="coerce")
        mn = rule.params.get("min", float("-inf"))
        mx = rule.params.get("max", float("inf"))
        mask = ((col < mn) | (col > mx)) & col.notna()
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value {col.iloc[i]} outside [{mn}, {mx}]" for i in fi], df)

    def _validate_regex(self, df, rule):
        col = df[rule.column]
        pat = rule.params.get("pattern", ".*")
        try:
            re.compile(pat)
        except re.error as e:
            return self._build_result(rule, len(df), list(range(len(df))),
                [f"Invalid regex: {e}"] * len(df), df)
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.match(pat, na=False)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' doesn't match '{pat}'" for i in fi], df)

    def _validate_email(self, df, rule):
        col = df[rule.column]
        pat = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.match(pat, na=False)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is not a valid email" for i in fi], df)

    def _validate_date(self, df, rule):
        col = df[rule.column]
        fmt = rule.params.get("format", "%Y-%m-%d")
        fi, errs = [], []
        for i, val in col.items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            try:
                datetime.strptime(str(val).strip(), fmt)
            except ValueError:
                fi.append(i)
                errs.append(f"Row {i}: '{rule.column}' value '{val}' invalid date (expected {fmt})")
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_phone(self, df, rule):
        col = df[rule.column]
        pat = rule.params.get("pattern", r"^\+\d{1,3}-\d{3}-\d{4}$")
        try:
            re.compile(pat)
        except re.error:
            pat = r"^\+\d{1,3}-\d{3}-\d{4}$"
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.match(pat, na=False)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is not a valid phone" for i in fi], df)

    # ═══════════════════════════════════════════════════════════════════════
    # EXTENDED VALIDATORS (23 new)
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_allowed_values(self, df, rule):
        """Check values are in an allowed list. Params: values: [list]"""
        col = df[rule.column]
        allowed = set(rule.params.get("values", []))
        nn = self._non_null_mask(col)
        mask = nn & ~col.isin(allowed)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' not in {allowed}" for i in fi], df)

    def _validate_numeric(self, df, rule):
        """Check all non-null values are numeric."""
        col = df[rule.column]
        numeric = pd.to_numeric(col, errors="coerce")
        nn = self._non_null_mask(col)
        mask = nn & numeric.isna()
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is not numeric" for i in fi], df)

    def _validate_positive(self, df, rule):
        """Check numeric values are > 0. Params: allow_zero: bool (default False)"""
        col = pd.to_numeric(df[rule.column], errors="coerce")
        allow_zero = rule.params.get("allow_zero", False)
        threshold = 0 if not allow_zero else -0.0001
        mask = col.notna() & (col <= threshold)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value {col.iloc[i]} is not positive" for i in fi], df)

    def _validate_min_length(self, df, rule):
        """Check string length >= min_length. Params: min_length: int"""
        col = df[rule.column].astype(str)
        min_len = rule.params.get("min_length", 1)
        nn = self._non_null_mask(df[rule.column])
        mask = nn & (col.str.len() < min_len)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{df[rule.column].iloc[i]}' length < {min_len}" for i in fi], df)

    def _validate_max_length(self, df, rule):
        """Check string length <= max_length. Params: max_length: int"""
        col = df[rule.column].astype(str)
        max_len = rule.params.get("max_length", 255)
        nn = self._non_null_mask(df[rule.column])
        mask = nn & (col.str.len() > max_len)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value length > {max_len}" for i in fi], df)

    def _validate_duplicate_row(self, df, rule):
        """Check for fully duplicated rows across all columns or subset. Params: columns: [list]"""
        cols = rule.params.get("columns", None)
        subset = cols if cols else list(df.columns)
        mask = df.duplicated(subset=subset, keep="first")
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: Entire row is a duplicate" for i in fi], df)

    def _validate_future_date(self, df, rule):
        """Check dates are not in the future. Params: format: str"""
        col = df[rule.column]
        fmt = rule.params.get("format", "%Y-%m-%d")
        today = date.today()
        fi, errs = [], []
        for i, val in col.items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            try:
                d = datetime.strptime(str(val).strip(), fmt).date()
                if d > today:
                    fi.append(i)
                    errs.append(f"Row {i}: '{rule.column}' value '{val}' is a future date")
            except ValueError:
                fi.append(i)
                errs.append(f"Row {i}: '{rule.column}' value '{val}' is not a valid date")
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_date_format(self, df, rule):
        """Check all dates match a specific format. Params: format: str"""
        return self._validate_date(df, rule)  # Same logic, different rule type name

    def _validate_placeholder(self, df, rule):
        """Detect placeholder values. Params: values: [list] of placeholders"""
        col = df[rule.column]
        placeholders = set(str(v).lower() for v in rule.params.get("values",
            ["N/A", "NA", "null", "none", "TODO", "TBD", "XXX", "test", "dummy", "placeholder", "-", "."]))
        nn = self._non_null_mask(col)
        mask = nn & col.astype(str).str.lower().isin(placeholders)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is a placeholder" for i in fi], df)

    def _validate_missing_threshold(self, df, rule):
        """Fail if null percentage exceeds threshold. Params: max_null_pct: float (0-100)"""
        col = df[rule.column]
        max_pct = rule.params.get("max_null_pct", 20.0)
        null_pct = (col.isna().sum() / len(df)) * 100 if len(df) > 0 else 0
        if null_pct > max_pct:
            fi = list(df[col.isna()].index)
            return self._build_result(rule, len(df), fi,
                [f"Column '{rule.column}' has {null_pct:.1f}% nulls (threshold: {max_pct}%)"], df)
        return self._build_result(rule, len(df), [], [], df)

    def _validate_customer_id_pattern(self, df, rule):
        """Check customer ID matches a pattern. Params: pattern: str"""
        col = df[rule.column]
        pat = rule.params.get("pattern", r"^\d+$")
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.match(pat, na=False)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' doesn't match ID pattern" for i in fi], df)

    def _validate_email_domain(self, df, rule):
        """Check email belongs to allowed domain(s). Params: domains: [list]"""
        col = df[rule.column]
        domains = set(d.lower() for d in rule.params.get("domains", []))
        fi, errs = [], []
        for i, val in col.items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            val_str = str(val).strip()
            if "@" not in val_str:
                fi.append(i)
                errs.append(f"Row {i}: '{rule.column}' value '{val_str}' is not a valid email")
                continue
            domain = val_str.split("@")[1].lower()
            if domains and domain not in domains:
                fi.append(i)
                errs.append(f"Row {i}: '{rule.column}' domain '{domain}' not in allowed {domains}")
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_currency(self, df, rule):
        """Check currency format. Params: currencies: [list] of ISO codes"""
        col = df[rule.column]
        valid_currencies = set(rule.params.get("currencies",
            ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY"]))
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.upper().isin(valid_currencies)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is not a valid currency code" for i in fi], df)

    def _validate_country(self, df, rule):
        """Check country code is valid ISO 3166-1 alpha-2. Params: valid_countries: [list]"""
        col = df[rule.column]
        valid = set(c.upper() for c in rule.params.get("valid_countries", [
            "US", "UK", "CA", "AU", "DE", "FR", "JP", "CN", "IN", "BR", "MX",
            "IT", "ES", "NL", "SE", "NO", "DK", "FI", "CH", "AT", "BE", "IE",
            "NZ", "SG", "KR", "ZA", "RU", "AR", "CL", "CO"]))
        nn = self._non_null_mask(col)
        mask = nn & ~col.astype(str).str.upper().isin(valid)
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value '{col.iloc[i]}' is not a recognized country" for i in fi], df)

    def _validate_date_order(self, df, rule):
        """Check date_col1 <= date_col2. Params: start_column, end_column, format"""
        start_col = rule.params.get("start_column", rule.column)
        end_col = rule.params.get("end_column", "")
        fmt = rule.params.get("format", "%Y-%m-%d")
        if end_col not in df.columns:
            return self._build_result(rule, len(df), [], [], df)
        fi, errs = [], []
        for i in range(len(df)):
            v1, v2 = df[start_col].iloc[i], df[end_col].iloc[i]
            if pd.isna(v1) or pd.isna(v2):
                continue
            try:
                d1 = datetime.strptime(str(v1).strip(), fmt)
                d2 = datetime.strptime(str(v2).strip(), fmt)
                if d1 > d2:
                    fi.append(i)
                    errs.append(f"Row {i}: {start_col} '{v1}' > {end_col} '{v2}'")
            except ValueError:
                pass
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_age(self, df, rule):
        """Realistic age check. Params: min: 0, max: 120"""
        return self._validate_range(df, ValidationRule(
            id=rule.id, column=rule.column, type="range",
            severity=rule.severity, description=rule.description,
            params={"min": rule.params.get("min", 0), "max": rule.params.get("max", 120)}))

    def _validate_salary(self, df, rule):
        """Realistic salary check. Params: min: 0, max: 10000000, currency"""
        col = pd.to_numeric(df[rule.column], errors="coerce")
        mn = rule.params.get("min", 0)
        mx = rule.params.get("max", 10000000)
        mask = ((col < mn) | (col > mx)) & col.notna()
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value {col.iloc[i]} outside salary range [{mn}, {mx}]" for i in fi], df)

    def _validate_transaction_amount(self, df, rule):
        """Check transaction amounts are valid. Params: min: 0, max: float"""
        col = pd.to_numeric(df[rule.column], errors="coerce")
        mn = rule.params.get("min", 0.01)
        mx = rule.params.get("max", float("inf"))
        mask = ((col < mn) | (col > mx) | col.isna()) & (self._non_null_mask(df[rule.column]) if df[rule.column].dtype == object else col.notna())
        # Only flag non-null values that are out of range
        nn = self._non_null_mask(df[rule.column]) if df[rule.column].dtype == object else col.notna()
        mask = nn & ((col < mn) | (col > mx) | col.isna())
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value {df[rule.column].iloc[i]} invalid transaction amount" for i in fi], df)

    def _validate_outlier(self, df, rule):
        """Detect outliers using IQR method. Params: factor: 1.5 (default)"""
        col = pd.to_numeric(df[rule.column], errors="coerce")
        factor = rule.params.get("factor", 1.5)
        q1, q3 = col.quantile(0.25), col.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - factor * iqr, q3 + factor * iqr
        mask = col.notna() & ((col < lower) | (col > upper))
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: '{rule.column}' value {col.iloc[i]} is an outlier (IQR bounds: [{lower:.1f}, {upper:.1f}])" for i in fi], df)

    def _validate_cross_field(self, df, rule):
        """Validate relationship between two columns. Params: column_a, column_b, operator"""
        col_a_name = rule.params.get("column_a", rule.column)
        col_b_name = rule.params.get("column_b", "")
        op = rule.params.get("operator", ">")
        if col_b_name not in df.columns or col_a_name not in df.columns:
            return self._build_result(rule, len(df), [], [], df)
        a = pd.to_numeric(df[col_a_name], errors="coerce")
        b = pd.to_numeric(df[col_b_name], errors="coerce")
        ops = {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b, "==": a == b, "!=": a != b}
        mask = a.notna() & b.notna() & ~ops.get(op, pd.Series(False, index=df.index))
        fi = list(df[mask].index)
        return self._build_result(rule, len(df), fi,
            [f"Row {i}: {col_a_name} ({a.iloc[i]}) not {op} {col_b_name} ({b.iloc[i]})" for i in fi], df)

    def _validate_business_rule(self, df, rule):
        """Custom expression-based rule. Params: expression: str (Python eval)"""
        expr = rule.params.get("expression", "True")
        fi, errs = [], []
        for i in range(len(df)):
            row = df.iloc[i]
            try:
                result = eval(expr, {"__builtins__": {}}, dict(row))
                if not result:
                    fi.append(i)
                    errs.append(f"Row {i}: Business rule '{expr}' failed")
            except Exception as e:
                fi.append(i)
                errs.append(f"Row {i}: Business rule error: {e}")
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_data_consistency(self, df, rule):
        """Check logical consistency. Params: mappings: {col_a_val: {col_b: expected_val}}"""
        mappings = rule.params.get("mappings", {})
        check_col = rule.params.get("check_column", "")
        ref_col = rule.params.get("reference_column", rule.column)
        if not check_col or check_col not in df.columns or ref_col not in df.columns:
            return self._build_result(rule, len(df), [], [], df)
        fi, errs = [], []
        for i in range(len(df)):
            ref_val = str(df[ref_col].iloc[i]).strip()
            if ref_val in mappings:
                expected = mappings[ref_val]
                actual = str(df[check_col].iloc[i]).strip()
                if actual != str(expected):
                    fi.append(i)
                    errs.append(f"Row {i}: {ref_col}='{ref_val}' expects {check_col}='{expected}', got '{actual}'")
        return self._build_result(rule, len(df), fi, errs, df)

    def _validate_data_freshness(self, df, rule):
        """Check data isn't too old. Params: max_age_days: int, format: str"""
        col = df[rule.column]
        max_days = rule.params.get("max_age_days", 365)
        fmt = rule.params.get("format", "%Y-%m-%d")
        today = date.today()
        fi, errs = [], []
        for i, val in col.items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            try:
                d = datetime.strptime(str(val).strip(), fmt).date()
                age = (today - d).days
                if age > max_days:
                    fi.append(i)
                    errs.append(f"Row {i}: '{rule.column}' value '{val}' is {age} days old (max: {max_days})")
            except ValueError:
                fi.append(i)
                errs.append(f"Row {i}: '{rule.column}' value '{val}' invalid date")
        return self._build_result(rule, len(df), fi, errs, df)

    # ═══════════════════════════════════════════════════════════════════════
    # DISPATCH TABLE (all 30 validators)
    # ═══════════════════════════════════════════════════════════════════════
    _DISPATCH = {
        "not_null": _validate_not_null,
        "unique": _validate_unique,
        "range": _validate_range,
        "regex": _validate_regex,
        "email": _validate_email,
        "date": _validate_date,
        "phone": _validate_phone,
        "allowed_values": _validate_allowed_values,
        "numeric": _validate_numeric,
        "positive": _validate_positive,
        "min_length": _validate_min_length,
        "max_length": _validate_max_length,
        "duplicate_row": _validate_duplicate_row,
        "future_date": _validate_future_date,
        "date_format": _validate_date_format,
        "placeholder": _validate_placeholder,
        "missing_threshold": _validate_missing_threshold,
        "customer_id_pattern": _validate_customer_id_pattern,
        "email_domain": _validate_email_domain,
        "currency": _validate_currency,
        "country": _validate_country,
        "date_order": _validate_date_order,
        "age": _validate_age,
        "salary": _validate_salary,
        "transaction_amount": _validate_transaction_amount,
        "outlier": _validate_outlier,
        "cross_field": _validate_cross_field,
        "business_rule": _validate_business_rule,
        "data_consistency": _validate_data_consistency,
        "data_freshness": _validate_data_freshness,
    }
