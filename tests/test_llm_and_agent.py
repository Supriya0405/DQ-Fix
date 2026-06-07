"""
Tests for LLM Client and Agent Loop
=====================================
Tests LLM client availability, fallback analysis, JSON parsing,
and agent loop iteration logic.
"""

import pytest
import pandas as pd
import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.ai.llm_client import LLMClient
from src.agent.agent_loop import AgentLoop
from src.validators.result_models import RuleResult, ValidationResult
from src.rules.rule_engine import ValidationRule


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def sample_rule_result():
    return RuleResult(
        rule_id="R001", rule_type="not_null", column="name",
        severity="high", description="Name must not be null",
        passed=False, total_rows=10, passed_count=8, failed_count=2,
        failed_row_indices=[3, 7],
        error_details=["Row 3: name is null", "Row 7: name is null"],
    )


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", None, "Charlie", None, "Eve"],
        "email": ["a@b.com", "bad", "c@d.com", "e@f.com", None],
        "age": [25, 30, 150, -5, 45],
    })


# ═══════════════════════════════════════════════════════════════════════════
# LLM CLIENT
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMClientAvailability:
    def test_groq_without_key_unavailable(self):
        client = LLMClient(provider="groq", api_key="")
        assert not client.is_available()

    def test_groq_with_key_available(self):
        client = LLMClient(provider="groq", api_key="gsk_abcdef123456789")
        assert client.is_available()

    def test_openai_without_key_unavailable(self):
        client = LLMClient(provider="openai", api_key="")
        assert client.is_available() is False

    def test_status_message(self):
        client = LLMClient(provider="groq", api_key="")
        status = client.get_status()
        assert "API key required" in status or "not available" in status

    def test_status_with_key(self):
        client = LLMClient(provider="groq", api_key="gsk_abcdef123456789")
        status = client.get_status()
        assert "Groq" in status


class TestLLMClientFallbackAnalysis:
    def test_fallback_when_unavailable(self, sample_rule_result):
        client = LLMClient(provider="groq", api_key="")
        analysis = client.analyze_failure(sample_rule_result)
        assert "fallback" in analysis
        assert analysis["fallback"] is True
        assert "root_cause" in analysis
        assert "sql_fix" in analysis
        assert "pandas_fix" in analysis

    def test_fallback_not_null(self, sample_rule_result):
        client = LLMClient(provider="openai", api_key="")
        analysis = client.analyze_failure(sample_rule_result)
        assert "null" in analysis["root_cause"].lower()

    def test_fallback_unique(self):
        result = RuleResult(
            rule_id="R002", rule_type="unique", column="id",
            severity="high", description="ID must be unique",
            passed=False, total_rows=10, passed_count=8, failed_count=2,
            failed_row_indices=[5, 8], error_details=["Duplicate id"],
        )
        client = LLMClient(provider="groq", api_key="")
        analysis = client.analyze_failure(result)
        assert "duplicate" in analysis["root_cause"].lower()

    def test_fallback_range(self):
        result = RuleResult(
            rule_id="R003", rule_type="range", column="age",
            severity="medium", description="Age range",
            passed=False, total_rows=10, passed_count=8, failed_count=2,
            failed_row_indices=[2, 3], error_details=["Out of range"],
        )
        client = LLMClient(provider="groq", api_key="")
        analysis = client.analyze_failure(result)
        assert "range" in analysis["root_cause"].lower() or "outside" in analysis["root_cause"].lower()


class TestLLMClientJSONParsing:
    def test_parse_clean_json(self, sample_rule_result):
        client = LLMClient(provider="groq", api_key="gsk_test123456789")
        raw = json.dumps({
            "root_cause": "Test root cause",
            "explanation": "Test explanation",
            "business_impact": "Test impact",
            "sql_fix": "DELETE FROM t",
            "pandas_fix": "df.dropna()",
            "prevention": "Validate input",
            "severity": "high",
            "confidence": 90,
            "estimated_affected_rows": 2,
            "permanent_fix": "Automated checks",
        })
        result = client._parse_analysis_response(raw, sample_rule_result)
        assert result["root_cause"] == "Test root cause"
        assert result["confidence"] == 90

    def test_parse_markdown_wrapped_json(self, sample_rule_result):
        client = LLMClient(provider="groq", api_key="gsk_test123456789")
        data = {
            "root_cause": "Markdown root",
            "explanation": "Test",
            "sql_fix": "DELETE",
            "pandas_fix": "dropna()",
            "confidence": 80,
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        result = client._parse_analysis_response(raw, sample_rule_result)
        assert result["root_cause"] == "Markdown root"

    def test_parse_json_with_trailing_commas(self, sample_rule_result):
        client = LLMClient(provider="groq", api_key="gsk_test123456789")
        raw = '{"root_cause": "test", "confidence": 85, "sql_fix": "DELETE",}'
        result = client._parse_analysis_response(raw, sample_rule_result)
        assert result["root_cause"] == "test"

    def test_parse_no_json_falls_back(self, sample_rule_result):
        client = LLMClient(provider="groq", api_key="gsk_test123456789")
        raw = "This is just text with no JSON at all"
        result = client._parse_analysis_response(raw, sample_rule_result)
        assert "fallback" in result or "root_cause" in result


class TestLLMClientRuleGeneration:
    def test_fallback_rule_generation(self, sample_df):
        client = LLMClient(provider="groq", api_key="")
        yaml_str = client.generate_rules(sample_df, "test_dataset")
        assert "rules:" in yaml_str
        assert "not_null" in yaml_str or "unique" in yaml_str or "range" in yaml_str

    def test_fallback_generates_email_rule(self, sample_df):
        client = LLMClient(provider="groq", api_key="")
        yaml_str = client.generate_rules(sample_df, "test")
        assert "email" in yaml_str

    def test_fallback_generates_duplicate_row(self, sample_df):
        client = LLMClient(provider="groq", api_key="")
        yaml_str = client.generate_rules(sample_df, "test")
        assert "duplicate_row" in yaml_str


# ═══════════════════════════════════════════════════════════════════════════
# AGENT LOOP
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentLoop:
    def test_init_default(self):
        loop = AgentLoop()
        assert loop.max_iterations == 3
        assert loop.status == "idle"

    def test_init_custom_iterations(self):
        loop = AgentLoop(max_iterations=5)
        assert loop.max_iterations == 5

    def test_init_with_llm(self):
        mock_llm = MagicMock()
        loop = AgentLoop(llm=mock_llm)
        assert loop.llm is mock_llm

    def test_run_all_pass(self):
        """Agent should stop immediately if all rules pass."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = False
        loop = AgentLoop(max_iterations=3, llm=mock_llm)

        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        rules = [ValidationRule(id="R001", column="name", type="not_null")]

        result = loop.run(df, rules)
        assert result["status"] == "completed"
        assert result["total_iterations"] == 1

    def test_run_with_failures(self, sample_df):
        """Agent should iterate and try to fix failures."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = False
        mock_llm.analyze_failure.return_value = {
            "root_cause": "Null values",
            "explanation": "Missing data",
            "business_impact": "Errors",
            "sql_fix": "DELETE WHERE null",
            "pandas_fix": "df['name'].fillna('Unknown', inplace=True)",
            "prevention": "Validate",
            "severity": "high",
            "confidence": 80,
            "estimated_affected_rows": 2,
            "permanent_fix": "Checks",
        }
        loop = AgentLoop(max_iterations=2, llm=mock_llm)

        rules = [ValidationRule(id="R001", column="name", type="not_null")]
        result = loop.run(sample_df, rules)
        assert result["total_iterations"] >= 1
        assert len(result["iterations"]) >= 1

    def test_run_max_iterations_reached(self, sample_df):
        """Agent should stop at max_iterations."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = False
        mock_llm.analyze_failure.return_value = {
            "root_cause": "issue", "pandas_fix": "# fix",
            "severity": "high", "confidence": 50,
        }
        loop = AgentLoop(max_iterations=2, llm=mock_llm)

        # Rules that can't be fully fixed
        rules = [
            ValidationRule(id="R001", column="name", type="not_null"),
            ValidationRule(id="R002", column="age", type="range",
                          params={"min": 0, "max": 120}),
        ]
        result = loop.run(sample_df, rules)
        assert result["total_iterations"] <= 2

    def test_get_status(self):
        loop = AgentLoop()
        status = loop.get_status()
        assert status["status"] == "idle"
        assert status["max_iterations"] == 3

    def test_apply_fixes_not_null(self):
        """Test the built-in fix for not_null with fallback if AI code is not executable."""
        loop = AgentLoop()
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]})
        analyses = [{
            "rule_id": "R001", "rule_type": "not_null",
            "column": "name", "pandas_fix": "fill nulls",
        }]
        updated_df, fixes = loop._apply_fixes(df, analyses)
        assert len(fixes) >= 1
        assert updated_df["name"].isna().sum() == 0

    def test_apply_fixes_uses_ai_pandas_code(self):
        """AI-provided pandas fix code should be executed when available."""
        loop = AgentLoop()
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]})
        analyses = [{
            "rule_id": "R001", "rule_type": "not_null",
            "column": "name", "pandas_fix": "df['name'] = df['name'].fillna('Unknown')",
        }]
        updated_df, fixes = loop._apply_fixes(df, analyses)
        assert updated_df.loc[1, 'name'] == 'Unknown'
        assert fixes[0]["success"] is True

    def test_apply_fixes_duplicate_row(self):
        """Test the built-in fix for duplicate rows via _apply_typed_fix directly."""
        loop = AgentLoop()
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        result = loop._apply_typed_fix(df, "duplicate_row", "_all")
        assert "Removed" in result or "duplicate" in result.lower()

    def test_apply_fixes_placeholder(self):
        """Test the built-in fix for placeholder values."""
        loop = AgentLoop()
        df = pd.DataFrame({"name": ["Alice", "N/A", "TBD"]})
        analyses = [{
            "rule_id": "R001", "rule_type": "placeholder",
            "column": "name", "pandas_fix": "remove placeholders",
        }]
        updated_df, fixes = loop._apply_fixes(df, analyses)
        assert len(fixes) >= 1
        assert updated_df["name"].isna().sum() == 2


# ═══════════════════════════════════════════════════════════════════════════
# SEVERITY ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class TestSeverityEngine:
    def test_severity_escalation(self):
        from src.ai.severity_engine import SeverityEngine
        engine = SeverityEngine()
        # >50% failure rate should escalate low→medium
        result = engine.calculate_severity("not_null", 60, 100, "low")
        assert result == "medium"

    def test_severity_high_failure_escalation(self):
        from src.ai.severity_engine import SeverityEngine
        engine = SeverityEngine()
        # >80% failure rate should escalate medium→high
        result = engine.calculate_severity("not_null", 90, 100, "medium")
        assert result == "high"

    def test_confidence_score_range(self):
        from src.ai.severity_engine import SeverityEngine
        engine = SeverityEngine()
        score = engine.calculate_confidence("not_null", 2, 100)
        assert 0 <= score <= 100

    def test_confidence_with_llm(self):
        from src.ai.severity_engine import SeverityEngine
        engine = SeverityEngine()
        score_no_llm = engine.calculate_confidence("not_null", 2, 100, llm_available=False)
        score_with_llm = engine.calculate_confidence("not_null", 2, 100, llm_available=True)
        assert score_with_llm >= score_no_llm


# ═══════════════════════════════════════════════════════════════════════════
# CSV READER
# ═══════════════════════════════════════════════════════════════════════════

class TestCSVReader:
    def test_read_valid_csv(self):
        from src.readers.csv_reader import CSVReader
        reader = CSVReader()
        from config.settings import SAMPLE_DATA_DIR
        path = os.path.join(SAMPLE_DATA_DIR, "valid_customers.csv")
        if os.path.exists(path):
            df, info = reader.read(file_path=path)
            assert len(df) > 0
            assert info["rows"] > 0
            assert info["columns"] > 0
        else:
            pytest.skip("valid_customers.csv not found")

    def test_read_nonexistent_raises(self):
        from src.readers.csv_reader import CSVReader
        reader = CSVReader()
        with pytest.raises(FileNotFoundError):
            reader.read(file_path="/nonexistent/file.csv")

    def test_no_input_raises(self):
        from src.readers.csv_reader import CSVReader
        reader = CSVReader()
        with pytest.raises(ValueError):
            reader.read()
