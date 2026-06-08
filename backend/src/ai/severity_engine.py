"""
Severity & Confidence Engine
=============================
Calculates severity levels and confidence scores for validation failures.
"""

from config.settings import DEFAULT_SEVERITY_MAP, CONFIDENCE_WEIGHTS


class SeverityEngine:
    """Calculates and adjusts severity based on failure context."""

    def calculate_severity(self, rule_type: str, failed_count: int, total_rows: int,
                           base_severity: str = None) -> str:
        """Calculate severity considering rule type, failure rate, and context."""
        if base_severity and base_severity in ("low", "medium", "high"):
            severity = base_severity
        else:
            severity = DEFAULT_SEVERITY_MAP.get(rule_type, "medium")

        # Escalate severity if failure rate is very high
        if total_rows > 0:
            failure_rate = failed_count / total_rows
            if failure_rate > 0.5 and severity == "low":
                severity = "medium"
            elif failure_rate > 0.8 and severity == "medium":
                severity = "high"

        return severity

    def calculate_confidence(self, rule_type: str, failed_count: int, total_rows: int,
                             has_params: bool = True, llm_available: bool = False) -> int:
        """
        Calculate confidence score (0-100) for the fix suggestion.

        Factors:
        - fix_success_rate: How likely this fix type works (40%)
        - rule_clarity: How specific the rule is (30%)
        - data_coverage: What % of data the rule covers (30%)
        """
        # Fix success rates by type
        success_rates = {
            "not_null": 0.95, "unique": 0.90, "range": 0.85, "regex": 0.80,
            "email": 0.75, "date": 0.85, "phone": 0.80,
            "allowed_values": 0.90, "numeric": 0.95, "positive": 0.90,
            "min_length": 0.85, "max_length": 0.85, "duplicate_row": 0.88,
            "future_date": 0.90, "date_format": 0.85, "placeholder": 0.92,
            "missing_threshold": 0.80, "customer_id_pattern": 0.85,
            "email_domain": 0.88, "currency": 0.90, "country": 0.85,
            "date_order": 0.85, "age": 0.85, "salary": 0.80,
            "transaction_amount": 0.85, "outlier": 0.70,
            "cross_field": 0.75, "business_rule": 0.70,
            "data_consistency": 0.70, "data_freshness": 0.90,
        }

        fix_rate = success_rates.get(rule_type, 0.75)
        if llm_available:
            fix_rate = min(1.0, fix_rate + 0.1)

        # Rule clarity
        clarity = 0.9 if has_params else 0.7

        # Data coverage
        coverage = 1.0 - (failed_count / max(total_rows, 1))

        score = (
            fix_rate * CONFIDENCE_WEIGHTS["fix_success_rate"] +
            clarity * CONFIDENCE_WEIGHTS["rule_clarity"] +
            coverage * CONFIDENCE_WEIGHTS["data_coverage"]
        )

        return min(100, max(0, int(score * 100)))
