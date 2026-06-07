"""
Tests for SQLite Database Manager
===================================
Tests CRUD operations, schema creation, and data integrity for all 7 tables.
"""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.database.db_manager import DatabaseManager
from src.validators.result_models import RuleResult, ValidationResult
import pandas as pd


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Create a fresh temporary database for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = DatabaseManager(db_path=path)
    yield manager
    manager.close()
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def sample_validation_result():
    """Create a sample ValidationResult for testing."""
    results = [
        RuleResult(
            rule_id="R001", rule_type="not_null", column="name",
            severity="high", description="Name must not be null",
            passed=False, total_rows=10, passed_count=8, failed_count=2,
            failed_row_indices=[3, 7],
            failed_samples=pd.DataFrame({"name": [None, None]}, index=[3, 7]),
            error_details=["Row 3: name is null", "Row 7: name is null"],
        ),
        RuleResult(
            rule_id="R002", rule_type="unique", column="id",
            severity="high", description="ID must be unique",
            passed=True, total_rows=10, passed_count=10, failed_count=0,
        ),
    ]
    return ValidationResult(
        total_rules=2, passed_rules=1, failed_rules=1,
        total_failures=2, results=results,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA CREATION
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaCreation:
    def test_tables_exist(self, db):
        """All 7 tables should be created on init."""
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected = {
            "validation_runs", "validation_results", "failed_records",
            "ai_analysis", "remediation_suggestions",
            "agent_iterations", "api_validation_results",
        }
        assert expected.issubset(tables)

    def test_foreign_keys_enabled(self, db):
        result = db.conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION RUNS (Table 1)
# ═══════════════════════════════════════════════════════════════════════════

class TestValidationRuns:
    def test_save_validation_run(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        assert run_id > 0

    def test_save_and_retrieve_run(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result,
                                         total_columns=5)
        history = db.get_validation_history()
        assert len(history) == 1
        assert history[0]["dataset_name"] == "test.csv"
        assert history[0]["total_rows"] == 10
        assert history[0]["total_rules"] == 2

    def test_save_with_metadata(self, db, sample_validation_result):
        run_id = db.save_validation_run(
            "test.csv", 10, sample_validation_result,
            metadata={"source": "unit_test"}
        )
        details = db.get_run_details(run_id)
        assert details["run"]["metadata_json"] == '{"source": "unit_test"}'

    def test_update_run_status(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        db.update_run_status(run_id, "completed")
        details = db.get_run_details(run_id)
        assert details["run"]["overall_status"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION RESULTS (Table 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestValidationResults:
    def test_results_saved(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        details = db.get_run_details(run_id)
        assert len(details["results"]) == 2

    def test_result_fields(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        details = db.get_run_details(run_id)
        r001 = [r for r in details["results"] if r["rule_id"] == "R001"][0]
        assert r001["column_name"] == "name"
        assert r001["validation_type"] == "not_null"
        assert r001["passed"] == 0  # Failed


# ═══════════════════════════════════════════════════════════════════════════
# FAILED RECORDS (Table 3)
# ═══════════════════════════════════════════════════════════════════════════

class TestFailedRecords:
    def test_failed_records_saved(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        records = db.get_failed_records(run_id)
        assert len(records) == 2  # 2 failed rows for R001

    def test_failed_record_fields(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        records = db.get_failed_records(run_id)
        assert records[0]["column_name"] == "name"
        assert records[0]["row_index"] in [3, 7]


# ═══════════════════════════════════════════════════════════════════════════
# AI ANALYSIS (Table 4)
# ═══════════════════════════════════════════════════════════════════════════

class TestAIAnalysis:
    def test_save_ai_analysis(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        analysis = {
            "rule_id": "R001", "rule_type": "not_null", "column": "name",
            "root_cause": "Null values found", "explanation": "Missing data",
            "business_impact": "Downstream errors", "prevention": "Input validation",
            "severity": "high", "confidence": 85,
            "estimated_affected_rows": 2, "permanent_fix": "Automated checks",
            "provider": "groq", "sql_fix": "DELETE WHERE name IS NULL",
            "pandas_fix": "df.dropna(subset=['name'])",
        }
        db.save_ai_analysis(run_id, analysis)
        history = db.get_ai_analysis_history(run_id)
        assert len(history) == 1
        assert history[0]["root_cause"] == "Null values found"


# ═══════════════════════════════════════════════════════════════════════════
# REMEDIATION SUGGESTIONS (Table 5)
# ═══════════════════════════════════════════════════════════════════════════

class TestRemediationSuggestions:
    def test_remediation_saved_with_analysis(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        analysis = {
            "rule_id": "R001", "rule_type": "not_null", "column": "name",
            "root_cause": "Null values", "sql_fix": "DELETE WHERE null",
            "pandas_fix": "df.dropna()", "confidence": 85,
        }
        db.save_ai_analysis(run_id, analysis)
        remediations = db.get_remediation_history(run_id)
        assert len(remediations) == 1
        assert remediations[0]["sql_fix"] == "DELETE WHERE null"

    def test_mark_remediation_applied(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        analysis = {
            "rule_id": "R001", "sql_fix": "DELETE", "pandas_fix": "dropna",
        }
        db.save_ai_analysis(run_id, analysis)
        rem = db.get_remediation_history(run_id)
        db.mark_remediation_applied(rem[0]["remediation_id"])
        rem2 = db.get_remediation_history(run_id)
        assert rem2[0]["fix_applied"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# AGENT ITERATIONS (Table 6)
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentIterations:
    def test_save_agent_iteration(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        db.save_agent_iteration(
            run_id, iteration=1, status="fixes_applied",
            passed_rules=1, failed_rules=1, total_failures=2,
            fixes_applied=1, action_taken="Applied null fill"
        )
        iters = db.get_agent_iterations(run_id)
        assert len(iters) == 1
        assert iters[0]["iteration_number"] == 1
        assert iters[0]["validation_status"] == "fixes_applied"

    def test_multiple_iterations(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        for i in range(1, 4):
            db.save_agent_iteration(run_id, iteration=i, status=f"iter_{i}")
        iters = db.get_agent_iterations(run_id)
        assert len(iters) == 3


# ═══════════════════════════════════════════════════════════════════════════
# API VALIDATION RESULTS (Table 7)
# ═══════════════════════════════════════════════════════════════════════════

class TestAPIValidationResults:
    def test_save_api_validation(self, db):
        db.save_api_validation("test@example.com", {
            "api_status": "valid", "is_valid": True, "confidence": 95
        })
        history = db.get_api_validation_history()
        assert len(history) == 1
        assert history[0]["email"] == "test@example.com"
        assert history[0]["is_valid"] == 1

    def test_save_api_validation_with_run_id(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        db.save_api_validation("test@example.com", {
            "api_status": "invalid", "is_valid": False
        }, run_id=run_id)
        history = db.get_api_validation_history()
        assert history[0]["run_id"] == run_id


# ═══════════════════════════════════════════════════════════════════════════
# DELETE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

class TestDeleteOperations:
    def test_delete_run_cascade(self, db, sample_validation_result):
        run_id = db.save_validation_run("test.csv", 10, sample_validation_result)
        assert len(db.get_validation_history()) == 1
        db.delete_run(run_id)
        assert len(db.get_validation_history()) == 0
        assert len(db.get_failed_records(run_id)) == 0

    def test_clear_all_history(self, db, sample_validation_result):
        db.save_validation_run("test.csv", 10, sample_validation_result)
        db.save_api_validation("test@ex.com", {"api_status": "ok"})
        db.clear_all_history()
        stats = db.get_statistics()
        assert stats["validation_runs"] == 0
        assert stats["api_validation_results"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

class TestStatistics:
    def test_empty_statistics(self, db):
        stats = db.get_statistics()
        assert stats["validation_runs"] == 0
        assert stats["pass_rate"] == 0.0

    def test_statistics_after_runs(self, db, sample_validation_result):
        db.save_validation_run("test.csv", 10, sample_validation_result)
        stats = db.get_statistics()
        assert stats["validation_runs"] == 1
        assert stats["validation_results"] == 2
        assert stats["failed_records"] == 2
        assert stats["pass_rate"] == 50.0  # 1/2 rules passed
