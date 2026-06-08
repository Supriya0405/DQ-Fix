"""
Tests for the AI rule generation workflow.

This file validates that the LLM client can produce fallback YAML rules when the provider is unavailable,
and that the generated YAML can be loaded by the RuleEngine for validation.
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.ai.llm_client import LLMClient
from src.rules.rule_engine import RuleEngine, VALID_RULE_TYPES, VALID_SEVERITIES


class TestAppRuleGeneration:
    def test_generate_rules_fallback_returns_yaml(self):
        df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "email": ["alice@example.com", None, "charlie@example.com"],
            "age": [25, 30, 22],
            "amount": [100.0, 250.5, 0.0],
            "country": ["US", "CA", "US"],
        })

        client = LLMClient(provider="openai", api_key="")
        yaml_str = client.generate_rules(df, dataset_name="test_dataset")

        assert isinstance(yaml_str, str)
        assert yaml_str.strip().startswith("rules:")
        assert "id:" in yaml_str
        assert "column:" in yaml_str

    def test_generated_rules_are_parseable_by_rule_engine(self):
        df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "email": ["alice@example.com", None, "charlie@example.com"],
            "age": [25, 30, 22],
            "amount": [100.0, 250.5, 0.0],
            "country": ["US", "CA", "US"],
        })

        client = LLMClient(provider="openai", api_key="")
        yaml_str = client.generate_rules(df, dataset_name="test_dataset")
        engine = RuleEngine(yaml_content=yaml_str)

        rules = engine.get_rules()
        assert len(rules) >= 1
        columns = {rule.column for rule in rules}
        assert "user_id" in columns
        assert "email" in columns
        assert "age" in columns

        # Ensure rules are parseable with valid type and severity
        assert all(rule.type in VALID_RULE_TYPES for rule in rules)
        assert all(rule.severity in VALID_SEVERITIES for rule in rules)
