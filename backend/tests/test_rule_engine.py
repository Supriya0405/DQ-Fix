"""
Tests for YAML Rule Engine
===========================
Tests rule parsing, validation, querying, and error handling.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.rules.rule_engine import RuleEngine, ValidationRule, VALID_RULE_TYPES, VALID_SEVERITIES


# ─── Fixtures ───────────────────────────────────────────────────────────────

VALID_YAML = """
dataset: test_dataset
description: Test dataset for unit tests
rules:
  - id: R001
    column: name
    type: not_null
    severity: high
    description: Name must not be null
  - id: R002
    column: email
    type: email
    severity: medium
    description: Email must be valid
  - id: R003
    column: age
    type: range
    severity: low
    description: Age must be in range
    params:
      min: 0
      max: 120
"""

YAML_MISSING_RULES_KEY = """
dataset: test
description: No rules key
"""

YAML_INVALID_TYPE = """
rules:
  - id: R001
    column: name
    type: invalid_type_xyz
    severity: high
"""

YAML_INVALID_SEVERITY = """
rules:
  - id: R001
    column: name
    type: not_null
    severity: critical
"""

YAML_MISSING_REQUIRED = """
rules:
  - id: R001
    column: name
"""


# ─── Tests: Loading ─────────────────────────────────────────────────────────

class TestRuleEngineLoading:
    """Test YAML loading and parsing."""

    def test_load_valid_yaml(self):
        engine = RuleEngine(yaml_content=VALID_YAML)
        rules = engine.get_rules()
        assert len(rules) == 3
        assert engine.get_dataset_name() == "test_dataset"

    def test_load_from_file(self):
        """Test loading from the actual sample_rules.yaml file."""
        from config.settings import DEFAULT_RULES_PATH
        if os.path.exists(DEFAULT_RULES_PATH):
            engine = RuleEngine(yaml_path=DEFAULT_RULES_PATH)
            rules = engine.get_rules()
            assert len(rules) >= 30  # Should have at least 30 rules
        else:
            pytest.skip("sample_rules.yaml not found")

    def test_no_input_raises_error(self):
        with pytest.raises(ValueError, match="Provide either"):
            RuleEngine()

    def test_missing_file_raises_error(self):
        with pytest.raises(FileNotFoundError):
            RuleEngine(yaml_path="/nonexistent/path.yaml")

    def test_missing_rules_key_raises_error(self):
        with pytest.raises(ValueError, match="No rules found"):
            RuleEngine(yaml_content=YAML_MISSING_RULES_KEY)

    def test_invalid_yaml_syntax(self):
        with pytest.raises(ValueError, match="YAML syntax error"):
            RuleEngine(yaml_content=": invalid: yaml: [")

    def test_yaml_root_not_dict(self):
        with pytest.raises(ValueError, match="root must be a mapping"):
            RuleEngine(yaml_content="- item1\n- item2")


# ─── Tests: ValidationRule Dataclass ────────────────────────────────────────

class TestValidationRule:
    """Test the ValidationRule dataclass."""

    def test_valid_rule(self):
        rule = ValidationRule(id="R001", column="name", type="not_null")
        assert rule.id == "R001"
        assert rule.column == "name"
        assert rule.type == "not_null"
        assert rule.severity == "medium"  # default
        assert rule.params == {}

    def test_rule_with_params(self):
        rule = ValidationRule(
            id="R002", column="age", type="range",
            severity="high", params={"min": 0, "max": 120}
        )
        assert rule.params["min"] == 0
        assert rule.params["max"] == 120

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid type"):
            ValidationRule(id="R001", column="name", type="nonexistent_type")

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            ValidationRule(id="R001", column="name", type="not_null", severity="critical")

    def test_empty_column_raises(self):
        with pytest.raises(ValueError, match="Column name cannot be empty"):
            ValidationRule(id="R001", column="", type="not_null")

    def test_to_dict(self):
        rule = ValidationRule(id="R001", column="name", type="not_null", severity="high")
        d = rule.to_dict()
        assert d["id"] == "R001"
        assert d["column"] == "name"
        assert d["type"] == "not_null"

    def test_summary(self):
        rule = ValidationRule(id="R001", column="name", type="not_null", severity="high")
        assert "R001" in rule.summary()
        assert "name" in rule.summary()
        assert "not_null" in rule.summary()

    def test_all_30_types_valid(self):
        """Verify all 30 validation types are accepted."""
        for vtype in VALID_RULE_TYPES:
            rule = ValidationRule(id="T001", column="col", type=vtype)
            assert rule.type == vtype


# ─── Tests: Query Methods ───────────────────────────────────────────────────

class TestRuleEngineQueries:
    """Test rule querying and filtering."""

    @pytest.fixture
    def engine(self):
        return RuleEngine(yaml_content=VALID_YAML)

    def test_get_rules(self, engine):
        assert len(engine.get_rules()) == 3

    def test_get_rules_for_column(self, engine):
        name_rules = engine.get_rules_for_column("name")
        assert len(name_rules) == 1
        assert name_rules[0].id == "R001"

    def test_get_rules_by_type(self, engine):
        email_rules = engine.get_rules_by_type("email")
        assert len(email_rules) == 1

    def test_get_rules_by_severity(self, engine):
        high_rules = engine.get_rules_by_severity("high")
        assert len(high_rules) == 1
        assert high_rules[0].id == "R001"

    def test_summary(self, engine):
        s = engine.summary()
        assert s["total_rules"] == 3
        assert "by_type" in s
        assert "by_severity" in s
        assert s["parse_errors"] == 0

    def test_to_dataframe(self, engine):
        df = engine.to_dataframe()
        assert len(df) == 3
        assert "id" in df.columns
        assert "column" in df.columns

    def test_get_dataset_description(self, engine):
        assert "Test dataset" in engine.get_dataset_description()
