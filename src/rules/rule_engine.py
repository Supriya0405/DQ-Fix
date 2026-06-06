"""
YAML Rule Engine
================
Parses validation rules from YAML files into typed Python objects.

Usage:
    from src.rules.rule_engine import RuleEngine

    engine = RuleEngine("sample_rules.yaml")
    rules = engine.get_rules()
    column_rules = engine.get_rules_for_column("email")
"""

import yaml
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ─── Supported Validation Types (30 types) ─────────────────────────────────
VALID_RULE_TYPES = {
    # Core (original 7)
    "not_null", "unique", "range", "regex", "email", "date", "phone",
    # Extended (23 new)
    "allowed_values", "numeric", "positive", "min_length", "max_length",
    "duplicate_row", "future_date", "date_format", "placeholder",
    "missing_threshold", "customer_id_pattern", "email_domain",
    "currency", "country", "date_order", "age", "salary",
    "transaction_amount", "outlier", "cross_field", "business_rule",
    "data_consistency", "data_freshness",
}
VALID_SEVERITIES = {"low", "medium", "high"}


@dataclass
class ValidationRule:
    """
    Represents a single validation rule.

    Attributes
    ----------
    id : str
        Unique rule identifier (e.g. "R001")
    column : str
        Target column name
    type : str
        Validation type: not_null, unique, range, regex, email, date, phone
    severity : str
        Severity level: low, medium, high
    description : str
        Human-readable description of the rule
    params : dict
        Type-specific parameters (e.g. min/max for range, pattern for regex)
    """
    id: str
    column: str
    type: str
    severity: str = "medium"
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate rule fields after initialization."""
        if self.type not in VALID_RULE_TYPES:
            raise ValueError(
                f"Rule {self.id}: Invalid type '{self.type}'. "
                f"Must be one of {VALID_RULE_TYPES}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Rule {self.id}: Invalid severity '{self.severity}'. "
                f"Must be one of {VALID_SEVERITIES}"
            )
        if not self.column:
            raise ValueError(f"Rule {self.id}: Column name cannot be empty.")

    def to_dict(self) -> dict:
        """Convert rule to dictionary for JSON/YAML serialization."""
        return {
            "id": self.id,
            "column": self.column,
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "params": self.params,
        }

    def summary(self) -> str:
        """One-line summary of the rule."""
        return f"[{self.id}] {self.column} → {self.type} ({self.severity})"


class RuleEngine:
    """
    Loads, validates, and manages YAML validation rules.

    Methods
    -------
    get_rules() -> List[ValidationRule]
        Returns all loaded rules.
    get_rules_for_column(column) -> List[ValidationRule]
        Returns rules targeting a specific column.
    get_rules_by_type(rule_type) -> List[ValidationRule]
        Returns rules of a specific validation type.
    get_rules_by_severity(severity) -> List[ValidationRule]
        Returns rules matching a severity level.
    summary() -> dict
        Returns counts of rules by type and severity.
    """

    def __init__(self, yaml_path: str = None, yaml_content: str = None):
        """
        Load rules from a YAML file or raw YAML string.

        Parameters
        ----------
        yaml_path : str, optional
            Path to the YAML rules file.
        yaml_content : str, optional
            Raw YAML string (used for testing or Streamlit text area input).
        """
        if yaml_path is None and yaml_content is None:
            raise ValueError("Provide either yaml_path or yaml_content.")

        if yaml_path is not None and not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Rules file not found: {yaml_path}")

        self._raw_config = {}
        self._rules: List[ValidationRule] = []
        self._errors: List[str] = []
        self._source = yaml_path or "inline_yaml"

        # Load and parse
        self._load(yaml_path, yaml_content)

    def _load(self, yaml_path: str, yaml_content: str):
        """Parse YAML and build rule objects."""
        try:
            if yaml_content:
                self._raw_config = yaml.safe_load(yaml_content)
            else:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    self._raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML syntax error: {e}")

        if not isinstance(self._raw_config, dict):
            raise ValueError("YAML root must be a mapping (dict), not a list.")

        raw_rules = self._raw_config.get("rules", [])
        if not raw_rules:
            raise ValueError("No rules found in YAML. Expected a 'rules:' key.")

        for i, raw_rule in enumerate(raw_rules):
            try:
                rule = self._parse_rule(raw_rule, index=i)
                self._rules.append(rule)
            except Exception as e:
                self._errors.append(f"Rule #{i+1}: {e}")

    def _parse_rule(self, raw: dict, index: int) -> ValidationRule:
        """Parse a single raw dict into a ValidationRule dataclass."""
        if not isinstance(raw, dict):
            raise ValueError(f"Rule #{index+1} is not a valid mapping.")

        required_keys = {"id", "column", "type"}
        missing = required_keys - set(raw.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")

        return ValidationRule(
            id=str(raw["id"]),
            column=str(raw["column"]),
            type=str(raw["type"]).lower(),
            severity=str(raw.get("severity", "medium")).lower(),
            description=str(raw.get("description", "")),
            params=raw.get("params", {}) or {},
        )

    # ── Query Methods ─────────────────────────────────────────────────────

    def get_rules(self) -> List[ValidationRule]:
        """Return all loaded rules."""
        return self._rules

    def get_rules_for_column(self, column: str) -> List[ValidationRule]:
        """Return rules targeting a specific column."""
        return [r for r in self._rules if r.column == column]

    def get_rules_by_type(self, rule_type: str) -> List[ValidationRule]:
        """Return rules of a specific validation type."""
        return [r for r in self._rules if r.type == rule_type]

    def get_rules_by_severity(self, severity: str) -> List[ValidationRule]:
        """Return rules matching a severity level."""
        return [r for r in self._rules if r.severity == severity]

    def get_errors(self) -> List[str]:
        """Return any parsing errors encountered."""
        return self._errors

    def get_dataset_name(self) -> str:
        """Return the dataset name from YAML config."""
        return self._raw_config.get("dataset", "unknown")

    def get_dataset_description(self) -> str:
        """Return the dataset description from YAML config."""
        return self._raw_config.get("description", "")

    def summary(self) -> dict:
        """Return counts of rules grouped by type and severity."""
        by_type = {}
        by_severity = {}
        for r in self._rules:
            by_type[r.type] = by_type.get(r.type, 0) + 1
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1

        return {
            "total_rules": len(self._rules),
            "by_type": by_type,
            "by_severity": by_severity,
            "columns_covered": list(set(r.column for r in self._rules)),
            "parse_errors": len(self._errors),
            "source": self._source,
        }

    def to_dataframe(self):
        """Return rules as a Pandas DataFrame for display."""
        import pandas as pd
        return pd.DataFrame([r.to_dict() for r in self._rules])


# ── Quick Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config.settings import DEFAULT_RULES_PATH

    print("=" * 60)
    print(f"Loading rules from: {DEFAULT_RULES_PATH}")
    print("=" * 60)

    engine = RuleEngine(yaml_path=DEFAULT_RULES_PATH)
    rules = engine.get_rules()

    print(f"\nLoaded {len(rules)} rules:")
    for r in rules:
        print(f"  {r.summary()}")

    print(f"\nSummary: {engine.summary()}")

    if engine.get_errors():
        print(f"\nErrors: {engine.get_errors()}")

    print(f"\nRules for 'email' column:")
    for r in engine.get_rules_for_column("email"):
        print(f"  {r.summary()}")

    print(f"\nRules by type 'not_null':")
    for r in engine.get_rules_by_type("not_null"):
        print(f"  {r.summary()}")

    print(f"\nRules as DataFrame:")
    print(engine.to_dataframe().to_string(index=False))
