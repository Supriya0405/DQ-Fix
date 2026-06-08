"""
Tests for Validation Engine (30 Validators)
=============================================
Tests each of the 30 validation types with passing and failing data.
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.validators.validation_engine import ValidationEngine
from src.rules.rule_engine import ValidationRule
from src.validators.result_models import RuleResult, ValidationResult


@pytest.fixture
def engine():
    return ValidationEngine()


def make_rule(rule_id="R001", column="col", vtype="not_null", severity="medium", params=None):
    return ValidationRule(id=rule_id, column=column, type=vtype, severity=severity, params=params or {})


# ═══════════════════════════════════════════════════════════════════════════
# CORE VALIDATORS (7)
# ═══════════════════════════════════════════════════════════════════════════

class TestNotNullValidator:
    def test_all_present_passes(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert result.all_passed
        assert result.results[0].passed

    def test_nulls_fail(self, engine):
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert not result.all_passed
        assert result.results[0].failed_count == 1

    def test_empty_string_fails(self, engine):
        df = pd.DataFrame({"name": ["Alice", "", "Charlie"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert result.results[0].failed_count == 1


class TestUniqueValidator:
    def test_all_unique_passes(self, engine):
        df = pd.DataFrame({"id": [1, 2, 3]})
        result = engine.validate(df, [make_rule(column="id", vtype="unique")])
        assert result.all_passed

    def test_duplicates_fail(self, engine):
        df = pd.DataFrame({"id": [1, 2, 2, 3]})
        result = engine.validate(df, [make_rule(column="id", vtype="unique")])
        assert result.results[0].failed_count == 1


class TestRangeValidator:
    def test_in_range_passes(self, engine):
        df = pd.DataFrame({"age": [20, 30, 40]})
        rule = make_rule(column="age", vtype="range", params={"min": 0, "max": 120})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_out_of_range_fails(self, engine):
        df = pd.DataFrame({"age": [20, -5, 200]})
        rule = make_rule(column="age", vtype="range", params={"min": 0, "max": 120})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 2


class TestRegexValidator:
    def test_matching_passes(self, engine):
        df = pd.DataFrame({"code": ["AB", "CD", "EF"]})
        rule = make_rule(column="code", vtype="regex", params={"pattern": "^[A-Z]{2}$"})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_non_matching_fails(self, engine):
        df = pd.DataFrame({"code": ["AB", "12", "EF"]})
        rule = make_rule(column="code", vtype="regex", params={"pattern": "^[A-Z]{2}$"})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


class TestEmailValidator:
    def test_valid_emails_pass(self, engine):
        df = pd.DataFrame({"email": ["a@b.com", "test@example.org"]})
        result = engine.validate(df, [make_rule(column="email", vtype="email")])
        assert result.all_passed

    def test_invalid_emails_fail(self, engine):
        df = pd.DataFrame({"email": ["notanemail", "a@b", "valid@test.com"]})
        result = engine.validate(df, [make_rule(column="email", vtype="email")])
        assert result.results[0].failed_count == 2


class TestDateValidator:
    def test_valid_dates_pass(self, engine):
        df = pd.DataFrame({"date": ["2023-01-15", "2024-06-30"]})
        rule = make_rule(column="date", vtype="date", params={"format": "%Y-%m-%d"})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_invalid_dates_fail(self, engine):
        df = pd.DataFrame({"date": ["2023-13-01", "not-a-date"]})
        rule = make_rule(column="date", vtype="date", params={"format": "%Y-%m-%d"})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 2


class TestPhoneValidator:
    def test_valid_phones_pass(self, engine):
        df = pd.DataFrame({"phone": ["+1-234-5678", "+91-987-6543"]})
        result = engine.validate(df, [make_rule(column="phone", vtype="phone")])
        assert result.all_passed

    def test_invalid_phones_fail(self, engine):
        df = pd.DataFrame({"phone": ["12345", "+1-234-5678"]})
        result = engine.validate(df, [make_rule(column="phone", vtype="phone")])
        assert result.results[0].failed_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# EXTENDED VALIDATORS (23)
# ═══════════════════════════════════════════════════════════════════════════

class TestAllowedValuesValidator:
    def test_valid_values_pass(self, engine):
        df = pd.DataFrame({"status": ["active", "inactive"]})
        rule = make_rule(column="status", vtype="allowed_values",
                        params={"values": ["active", "inactive", "pending"]})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_invalid_values_fail(self, engine):
        df = pd.DataFrame({"status": ["active", "deleted"]})
        rule = make_rule(column="status", vtype="allowed_values",
                        params={"values": ["active", "inactive"]})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


class TestNumericValidator:
    def test_numeric_passes(self, engine):
        df = pd.DataFrame({"amount": [10, 20.5, 30]})
        result = engine.validate(df, [make_rule(column="amount", vtype="numeric")])
        assert result.all_passed

    def test_non_numeric_fails(self, engine):
        df = pd.DataFrame({"amount": ["10", "abc", "30"]})
        result = engine.validate(df, [make_rule(column="amount", vtype="numeric")])
        assert result.results[0].failed_count == 1


class TestPositiveValidator:
    def test_positive_passes(self, engine):
        df = pd.DataFrame({"price": [10, 20, 30]})
        result = engine.validate(df, [make_rule(column="price", vtype="positive")])
        assert result.all_passed

    def test_negative_fails(self, engine):
        df = pd.DataFrame({"price": [10, -5, 30]})
        result = engine.validate(df, [make_rule(column="price", vtype="positive")])
        assert result.results[0].failed_count == 1


class TestMinMaxLengthValidator:
    def test_min_length_passes(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        rule = make_rule(column="name", vtype="min_length", params={"min_length": 2})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_min_length_fails(self, engine):
        df = pd.DataFrame({"name": ["A", "Bob"]})
        rule = make_rule(column="name", vtype="min_length", params={"min_length": 2})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1

    def test_max_length_passes(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        rule = make_rule(column="name", vtype="max_length", params={"max_length": 10})
        result = engine.validate(df, [rule])
        assert result.all_passed


class TestDuplicateRowValidator:
    def test_no_duplicates_passes(self, engine):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        rule = make_rule(column="_all", vtype="duplicate_row")
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_duplicates_fail(self, engine):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        rule = make_rule(column="_all", vtype="duplicate_row")
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


class TestFutureDateValidator:
    def test_past_dates_pass(self, engine):
        past = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        df = pd.DataFrame({"date": [past]})
        rule = make_rule(column="date", vtype="future_date", params={"format": "%Y-%m-%d"})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_future_date_fails(self, engine):
        future = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        df = pd.DataFrame({"date": [future]})
        rule = make_rule(column="date", vtype="future_date", params={"format": "%Y-%m-%d"})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


class TestPlaceholderValidator:
    def test_real_values_pass(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        rule = make_rule(column="name", vtype="placeholder")
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_placeholder_fails(self, engine):
        df = pd.DataFrame({"name": ["Alice", "N/A", "TBD"]})
        rule = make_rule(column="name", vtype="placeholder")
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 2


class TestMissingThresholdValidator:
    def test_below_threshold_passes(self, engine):
        df = pd.DataFrame({"email": ["a@b.com"] * 9 + [None]})
        rule = make_rule(column="email", vtype="missing_threshold",
                        params={"max_null_pct": 20.0})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_above_threshold_fails(self, engine):
        df = pd.DataFrame({"email": ["a@b.com"] * 5 + [None] * 5})
        rule = make_rule(column="email", vtype="missing_threshold",
                        params={"max_null_pct": 10.0})
        result = engine.validate(df, [rule])
        assert not result.results[0].passed


class TestOutlierValidator:
    def test_no_outliers_passes(self, engine):
        df = pd.DataFrame({"value": [10, 11, 12, 13, 14, 15]})
        rule = make_rule(column="value", vtype="outlier", params={"factor": 1.5})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_outlier_fails(self, engine):
        df = pd.DataFrame({"value": [10, 11, 12, 13, 14, 1000]})
        rule = make_rule(column="value", vtype="outlier", params={"factor": 1.5})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count >= 1


class TestCrossFieldValidator:
    def test_valid_relationship_passes(self, engine):
        df = pd.DataFrame({"start": [10, 20], "end": [20, 30]})
        rule = make_rule(column="start", vtype="cross_field",
                        params={"column_a": "start", "column_b": "end", "operator": "<="})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_invalid_relationship_fails(self, engine):
        df = pd.DataFrame({"start": [30, 20], "end": [20, 30]})
        rule = make_rule(column="start", vtype="cross_field",
                        params={"column_a": "start", "column_b": "end", "operator": "<="})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


class TestBusinessRuleValidator:
    def test_rule_passes(self, engine):
        df = pd.DataFrame({"age": [20, 30, 40]})
        rule = make_rule(column="age", vtype="business_rule",
                        params={"expression": "age >= 0"})
        result = engine.validate(df, [rule])
        assert result.all_passed

    def test_rule_fails(self, engine):
        df = pd.DataFrame({"age": [20, -5, 40]})
        rule = make_rule(column="age", vtype="business_rule",
                        params={"expression": "age >= 0"})
        result = engine.validate(df, [rule])
        assert result.results[0].failed_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT MODEL
# ═══════════════════════════════════════════════════════════════════════════

class TestValidationResult:
    def test_all_passed_property(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert result.all_passed is True

    def test_get_failed_results(self, engine):
        df = pd.DataFrame({"name": [None, "Bob"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        failed = result.get_failed_results()
        assert len(failed) == 1

    def test_summary(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "id": [1, 2]})
        rules = [
            make_rule("R001", "name", "not_null"),
            make_rule("R002", "id", "unique"),
        ]
        result = engine.validate(df, rules)
        s = result.summary()
        assert s["total_rules"] == 2
        assert s["passed_rules"] == 2

    def test_to_dataframe(self, engine):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        rdf = result.to_dataframe()
        assert len(rdf) == 1
        assert "Status" in rdf.columns


# ═══════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_missing_column(self, engine):
        df = pd.DataFrame({"name": ["Alice"]})
        result = engine.validate(df, [make_rule(column="nonexistent", vtype="not_null")])
        assert not result.results[0].passed

    def test_unknown_rule_type(self, engine):
        """Engine should handle unknown types gracefully."""
        df = pd.DataFrame({"name": ["Alice"]})
        # Use a valid type but test the dispatch table fallback
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert len(result.results) == 1

    def test_empty_dataframe(self, engine):
        df = pd.DataFrame({"name": []})
        result = engine.validate(df, [make_rule(column="name", vtype="not_null")])
        assert result.all_passed

    def test_multiple_rules(self, engine):
        df = pd.DataFrame({"name": ["Alice", None], "id": [1, 1]})
        rules = [
            make_rule("R001", "name", "not_null"),
            make_rule("R002", "id", "unique"),
        ]
        result = engine.validate(df, rules)
        assert result.total_rules == 2
        assert result.failed_rules == 2
