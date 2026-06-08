"""
Validation Result Models
========================
Dataclasses to hold validation results for each rule and the overall run.

Usage:
    from src.validators.result_models import RuleResult, ValidationResult
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class RuleResult:
    """
    Result of running a single validation rule against a DataFrame.

    Attributes
    ----------
    rule_id : str
        The rule identifier (e.g. "R001")
    rule_type : str
        Validation type (not_null, unique, range, etc.)
    column : str
        Target column name
    severity : str
        low, medium, high
    description : str
        Rule description from YAML
    passed : bool
        True if ALL rows passed the rule
    total_rows : int
        Total number of rows checked
    passed_count : int
        Number of rows that passed
    failed_count : int
        Number of rows that failed
    failed_row_indices : List[int]
        Zero-based row indices that failed
    failed_samples : pd.DataFrame
        Subset of the original DataFrame containing only failed rows
    error_details : List[str]
        Human-readable error message per failed row
    """
    rule_id: str
    rule_type: str
    column: str
    severity: str
    description: str
    passed: bool
    total_rows: int
    passed_count: int
    failed_count: int
    failed_row_indices: List[int] = field(default_factory=list)
    failed_samples: Optional[pd.DataFrame] = None
    error_details: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict (excluding DataFrame for JSON safety)."""
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "column": self.column,
            "severity": self.severity,
            "description": self.description,
            "passed": self.passed,
            "total_rows": self.total_rows,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "failed_row_indices": self.failed_row_indices,
            "error_details": self.error_details,
        }

    def summary_line(self) -> str:
        """One-line summary."""
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.rule_id} | {self.column} → {self.rule_type} | "
            f"{self.failed_count}/{self.total_rows} failed"
        )


@dataclass
class ValidationResult:
    """
    Aggregated result of running ALL rules against a DataFrame.

    Attributes
    ----------
    total_rules : int
        Number of rules executed
    passed_rules : int
        Number of rules where ALL rows passed
    failed_rules : int
        Number of rules where at least one row failed
    total_failures : int
        Sum of all failed row counts across all rules
    results : List[RuleResult]
        Individual rule results
    """
    total_rules: int
    passed_rules: int
    failed_rules: int
    total_failures: int
    results: List[RuleResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """True if every rule passed (zero failures)."""
        return self.failed_rules == 0

    def get_failed_results(self) -> List[RuleResult]:
        """Return only the rules that had failures."""
        return [r for r in self.results if not r.passed]

    def get_all_failed_rows(self) -> Dict[str, List[int]]:
        """Return a mapping of rule_id → failed row indices."""
        return {
            r.rule_id: r.failed_row_indices
            for r in self.results
            if not r.passed
        }

    def summary(self) -> dict:
        """High-level summary dict for dashboard display."""
        by_severity = {"high": 0, "medium": 0, "low": 0}
        for r in self.results:
            if not r.passed:
                by_severity[r.severity] += r.failed_count

        return {
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "total_failures": self.total_failures,
            "all_passed": self.all_passed,
            "failures_by_severity": by_severity,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Return a summary DataFrame of all rule results."""
        rows = []
        for r in self.results:
            rows.append({
                "Rule ID": r.rule_id,
                "Column": r.column,
                "Type": r.rule_type,
                "Severity": r.severity,
                "Status": "PASS" if r.passed else "FAIL",
                "Passed": r.passed_count,
                "Failed": r.failed_count,
                "Total": r.total_rows,
            })
        return pd.DataFrame(rows)
