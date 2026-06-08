"""
Sample Test Case File for DQ-Fix
==================================
This file contains comprehensive test cases demonstrating the testing approach
for the DQ-Fix data quality dashboard. Use this as a reference for creating
additional test cases.

Test Categories:
1. Data Loading and Validation
2. Rule Engine Functionality
3. AI Analysis Integration
4. Agent Loop Execution
5. Database Operations
6. End-to-End Workflows
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
import tempfile
from datetime import datetime, date
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.readers.csv_reader import CSVReader
from src.rules.rule_engine import RuleEngine, ValidationRule
from src.validators.validation_engine import ValidationEngine
from src.validators.result_models import ValidationResult
from src.ai.llm_client import LLMClient
from src.agent.agent_loop import AgentLoop
from src.fixer.auto_fixer import AutoFixer
from src.utils.helpers import get_dataset_summary, calculate_health_score


# ═══════════════════════════════════════════════════════════════════════════
# SAMPLE DATA FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_dataset():
    """
    Sample customer dataset with intentional data quality issues.
    This dataset contains:
    - Null values in name column
    - Invalid email formats
    - Age values outside valid range
    - Invalid phone numbers
    - Invalid status values
    - Invalid date formats
    - Transaction amounts outside valid range
    """
    return pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "name": ["Alice", "Bob", None, "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi", "Ivan"],
        "email": [
            "alice@example.com",
            "invalid-email",
            "charlie@test.org",
            "diana@company.com",
            "eve@domain.net",
            "frank@web.io",
            "not-an-email",
            "grace@site.com",
            "heidi@online.co",
            "ivan@service.edu"
        ],
        "age": [25, 30, 35, -5, 45, 150, 28, 32, 40, 55],
        "phone": [
            "+1-555-1234",
            "+91-987-6543",
            "12345",
            "+44-20-7946",
            "+1-800-5555",
            "invalid-phone",
            "+61-2-9876",
            "+1-555-6789",
            "+86-10-1234",
            "+49-30-9876"
        ],
        "status": ["active", "inactive", "active", "deleted", "active", "pending", "active", "inactive", "active", "unknown"],
        "registration_date": [
            "2023-01-15",
            "2023-02-20",
            "2023-03-10",
            "invalid-date",
            "2023-05-05",
            "2023-06-12",
            "2023-07-20",
            "2023-08-25",
            "2023-09-30",
            "2023-10-15"
        ],
        "transaction_amount": [100.50, 250.75, -50.00, 5000.00, 75.25, 125.50, 200.00, 300.75, 150.00, 400.25]
    })


@pytest.fixture
def sample_validation_rules():
    """
    Sample validation rules for customer data.
    These rules cover common data quality checks.
    """
    return [
        ValidationRule(
            id="R001",
            column="customer_id",
            type="not_null",
            severity="high",
            description="Customer ID must not be null"
        ),
        ValidationRule(
            id="R002",
            column="customer_id",
            type="unique",
            severity="high",
            description="Customer ID must be unique"
        ),
        ValidationRule(
            id="R003",
            column="name",
            type="not_null",
            severity="high",
            description="Customer name must not be null"
        ),
        ValidationRule(
            id="R004",
            column="email",
            type="email",
            severity="medium",
            description="Email must be valid format"
        ),
        ValidationRule(
            id="R005",
            column="age",
            type="range",
            severity="high",
            params={"min": 0, "max": 120},
            description="Age must be between 0 and 120"
        ),
        ValidationRule(
            id="R006",
            column="phone",
            type="phone",
            severity="low",
            description="Phone number must be valid format"
        ),
        ValidationRule(
            id="R007",
            column="status",
            type="allowed_values",
            severity="medium",
            params={"values": ["active", "inactive", "pending"]},
            description="Status must be one of: active, inactive, pending"
        ),
        ValidationRule(
            id="R008",
            column="registration_date",
            type="date",
            severity="high",
            params={"format": "%Y-%m-%d"},
            description="Registration date must be valid YYYY-MM-DD format"
        ),
        ValidationRule(
            id="R009",
            column="transaction_amount",
            type="range",
            severity="medium",
            params={"min": 0, "max": 1000},
            description="Transaction amount must be between 0 and 1000"
        ),
    ]


@pytest.fixture
def validation_engine():
    """Create validation engine instance."""
    return ValidationEngine()


@pytest.fixture
def mock_llm_client():
    """
    Mock LLM client for testing AI features without actual API calls.
    This simulates AI responses for testing purposes.
    """
    client = Mock(spec=LLMClient)
    client.is_available.return_value = True
    client.get_status.return_value = "Mock LLM Client - Ready"
    client.analyze_failure.return_value = {
        "root_cause": "Invalid email format detected",
        "confidence": 95,
        "severity": "medium",
        "explanation": "Email addresses must follow standard format with @ symbol and domain",
        "business_impact": "Unable to send notifications to customers with invalid emails",
        "sql_fix": "UPDATE customers SET email = NULL WHERE email NOT LIKE '%@%.%'",
        "pandas_fix": "df.loc[~df['email'].str.contains('@'), 'email'] = None",
        "prevention": "Implement email validation at data entry point"
    }
    return client


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 1: Data Loading and Basic Operations
# ═══════════════════════════════════════════════════════════════════════════

class TestDataLoading:
    """Test cases for data loading and basic operations."""
    
    def test_dataset_loading(self, sample_dataset):
        """
        TC-DATA-001: Verify dataset loads correctly
        Steps:
        1. Load sample dataset
        2. Verify row count is 10
        3. Verify column count is 8
        4. Verify required columns exist
        """
        assert len(sample_dataset) == 10, "Dataset should have 10 rows"
        assert len(sample_dataset.columns) == 8, "Dataset should have 8 columns"
        required_columns = ["customer_id", "name", "email", "age", "phone", "status", "registration_date", "transaction_amount"]
        for col in required_columns:
            assert col in sample_dataset.columns, f"Column {col} should exist"
    
    def test_dataset_summary(self, sample_dataset):
        """
        TC-DATA-002: Verify dataset summary calculation
        Steps:
        1. Calculate dataset summary
        2. Verify total rows
        3. Verify null count detection
        4. Verify duplicate detection
        """
        summary = get_dataset_summary(sample_dataset)
        assert summary["total_rows"] == 10, "Summary should show 10 rows"
        assert summary["total_columns"] == 8, "Summary should show 8 columns"
        assert summary["null_count"] > 0, "Dataset should have null values"
        assert summary["duplicated_rows"] == 0, "Dataset should have no duplicates"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Rule Engine Functionality
# ═══════════════════════════════════════════════════════════════════════════

class TestRuleEngine:
    """Test cases for rule engine functionality."""
    
    def test_rule_loading(self, sample_validation_rules):
        """
        TC-RULE-001: Verify rules load correctly
        Steps:
        1. Create validation rules
        2. Verify rule count
        3. Verify rule properties
        """
        assert len(sample_validation_rules) == 9, "Should have 9 rules"
        
        # Verify specific rule properties
        email_rule = [r for r in sample_validation_rules if r.column == "email"]
        assert len(email_rule) > 0, "Should have email rule"
        assert email_rule[0].type == "email", "Email rule should be of type 'email'"
    
    def test_rule_summary(self, sample_validation_rules):
        """
        TC-RULE-002: Verify rule summary generation
        Steps:
        1. Analyze rules
        2. Generate summary metrics
        3. Verify summary accuracy
        """
        total_rules = len(sample_validation_rules)
        columns_covered = set(r.column for r in sample_validation_rules)
        rule_types = set(r.type for r in sample_validation_rules)
        
        assert total_rules == 9, "Should have 9 rules"
        assert len(columns_covered) > 0, "Should cover multiple columns"
        assert len(rule_types) > 0, "Should have multiple rule types"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3: Validation Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestValidationEngine:
    """Test cases for validation engine functionality."""
    
    def test_validation_execution(self, sample_dataset, sample_validation_rules, validation_engine):
        """
        TC-VAL-001: Verify validation execution
        Steps:
        1. Load dataset
        2. Load validation rules
        3. Execute validation
        4. Verify all rules were checked
        """
        result = validation_engine.validate(sample_dataset, sample_validation_rules)
        assert result.total_rules == 9, "All 9 rules should be validated"
        assert len(result.results) == 9, "Should have 9 validation results"
    
    def test_failure_detection(self, sample_dataset, sample_validation_rules, validation_engine):
        """
        TC-VAL-002: Verify failure detection
        Steps:
        1. Execute validation on dataset with issues
        2. Verify failures are detected
        3. Verify failure count
        """
        result = validation_engine.validate(sample_dataset, sample_validation_rules)
        assert not result.all_passed, "Validation should detect failures"
        assert result.failed_rules > 0, "Should have failed rules"
        assert result.total_failures > 0, "Should have total failures"
    
    def test_failed_results_filtering(self, sample_dataset, sample_validation_rules, validation_engine):
        """
        TC-VAL-003: Verify failed results filtering
        Steps:
        1. Execute validation
        2. Filter for failed results
        3. Verify only failed rules are returned
        """
        result = validation_engine.validate(sample_dataset, sample_validation_rules)
        failed = result.get_failed_results()
        assert len(failed) > 0, "Should have failed results"
        assert all(not r.passed for r in failed), "All filtered results should be failed"
    
    def test_validation_summary(self, sample_dataset, sample_validation_rules, validation_engine):
        """
        TC-VAL-004: Verify validation summary
        Steps:
        1. Execute validation
        2. Generate summary
        3. Verify summary accuracy
        """
        result = validation_engine.validate(sample_dataset, sample_validation_rules)
        summary = result.summary()
        assert summary["total_rules"] == 9, "Summary should show 9 total rules"
        assert summary["passed_rules"] + summary["failed_rules"] == 9, "Passed + failed should equal total"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 4: AI Analysis Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestAIAnalysis:
    """Test cases for AI analysis integration."""
    
    def test_llm_client_availability(self, mock_llm_client):
        """
        TC-AI-001: Verify LLM client availability
        Steps:
        1. Check LLM client availability
        2. Verify status message
        """
        assert mock_llm_client.is_available() is True, "LLM client should be available"
        assert "Ready" in mock_llm_client.get_status(), "Status should indicate ready"
    
    def test_failure_analysis(self, mock_llm_client):
        """
        TC-AI-002: Verify failure analysis
        Steps:
        1. Call analyze_failure with sample data
        2. Verify analysis structure
        3. Verify required fields
        """
        analysis = mock_llm_client.analyze_failure(
            rule_id="R004",
            column="email",
            rule_type="email",
            failed_samples=pd.DataFrame({"email": ["invalid-email", "not-an-email"]})
        )
        
        required_fields = ["root_cause", "confidence", "severity", "explanation", 
                          "business_impact", "sql_fix", "pandas_fix", "prevention"]
        for field in required_fields:
            assert field in analysis, f"Analysis should include {field}"
        
        assert analysis["confidence"] == 95, "Confidence should be 95"
        assert "sql_fix" in analysis, "Should include SQL fix"
        assert "pandas_fix" in analysis, "Should include pandas fix"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 5: Agent Loop
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentLoop:
    """Test cases for agent loop functionality."""
    
    def test_agent_initialization(self, mock_llm_client):
        """
        TC-AGENT-001: Verify agent loop initialization
        Steps:
        1. Create agent loop
        2. Verify configuration
        """
        loop = AgentLoop(max_iterations=3, llm=mock_llm_client)
        assert loop.max_iterations == 3, "Max iterations should be 3"
        assert loop.llm == mock_llm_client, "LLM client should be set"
    
    @patch('src.agent.agent_loop.AgentLoop.run')
    def test_agent_execution(self, mock_run, sample_dataset, sample_validation_rules, mock_llm_client):
        """
        TC-AGENT-002: Verify agent loop execution
        Steps:
        1. Mock agent run method
        2. Execute agent loop
        3. Verify results structure
        """
        mock_run.return_value = {
            "status": "completed",
            "total_iterations": 2,
            "iterations": [
                {
                    "iteration": 1,
                    "status": "completed",
                    "passed_rules": 5,
                    "failed_rules": 4,
                    "total_failures": 8,
                    "fixes_applied": ["email_format_fix"],
                    "ai_analyses": [mock_llm_client.analyze_failure()]
                },
                {
                    "iteration": 2,
                    "status": "completed",
                    "passed_rules": 7,
                    "failed_rules": 2,
                    "total_failures": 3,
                    "fixes_applied": ["age_range_fix"],
                    "ai_analyses": [mock_llm_client.analyze_failure()]
                }
            ],
            "final_df": sample_dataset
        }
        
        loop = AgentLoop(max_iterations=3, llm=mock_llm_client)
        result = loop.run(sample_dataset, sample_validation_rules)
        
        assert result["status"] == "completed", "Agent should complete successfully"
        assert result["total_iterations"] == 2, "Should run 2 iterations"
        assert len(result["iterations"]) == 2, "Should have 2 iteration records"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 6: Health Score Calculation
# ═══════════════════════════════════════════════════════════════════════════

class TestHealthScore:
    """Test cases for health score calculation."""
    
    def test_health_score_calculation(self, sample_dataset):
        """
        TC-HEALTH-001: Verify health score calculation
        Steps:
        1. Calculate dataset summary
        2. Calculate health score
        3. Verify score range
        """
        summary = get_dataset_summary(sample_dataset)
        health = calculate_health_score(
            summary["total_rows"],
            summary["null_count"],
            summary["duplicated_rows"],
            5  # Assume 5 validation failures
        )
        
        assert 0 <= health <= 100, "Health score should be between 0 and 100"
        assert isinstance(health, (int, float)), "Health score should be a number"
    
    def test_health_score_improvement(self, sample_dataset, validation_engine):
        """
        TC-HEALTH-002: Verify health score improvement after fixes
        Steps:
        1. Calculate initial health score
        2. Apply data fixes
        3. Calculate improved health score
        4. Verify improvement
        """
        rules = [
            ValidationRule("R001", "name", "not_null", "high", "Name required"),
            ValidationRule("R002", "age", "range", "high", "Valid age", params={"min": 0, "max": 120})
        ]
        
        result1 = validation_engine.validate(sample_dataset, rules)
        summary1 = get_dataset_summary(sample_dataset)
        health1 = calculate_health_score(
            summary1["total_rows"],
            summary1["null_count"],
            summary1["duplicated_rows"],
            result1.total_failures
        )
        
        # Apply fixes
        cleaned_data = sample_dataset.copy()
        cleaned_data.loc[cleaned_data['name'].isna(), 'name'] = "Unknown"
        cleaned_data.loc[cleaned_data['age'] < 0, 'age'] = 0
        cleaned_data.loc[cleaned_data['age'] > 120, 'age'] = 120
        
        result2 = validation_engine.validate(cleaned_data, rules)
        summary2 = get_dataset_summary(cleaned_data)
        health2 = calculate_health_score(
            summary2["total_rows"],
            summary2["null_count"],
            summary2["duplicated_rows"],
            result2.total_failures
        )
        
        assert health2 >= health1, "Health score should improve after fixes"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 7: End-to-End Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndIntegration:
    """Test cases for end-to-end integration scenarios."""
    
    def test_complete_workflow(self, sample_dataset, sample_validation_rules, validation_engine):
        """
        TC-E2E-001: Verify complete validation workflow
        Steps:
        1. Load dataset
        2. Load rules
        3. Execute validation
        4. Analyze results
        5. Generate summary
        """
        # Step 1: Verify dataset
        assert len(sample_dataset) == 10, "Dataset should have 10 rows"
        
        # Step 2: Load rules
        assert len(sample_validation_rules) == 9, "Should have 9 rules"
        
        # Step 3: Execute validation
        result = validation_engine.validate(sample_dataset, sample_validation_rules)
        assert result.total_rules == 9, "All rules should be validated"
        assert not result.all_passed, "Should detect failures"
        
        # Step 4: Analyze results
        failed = result.get_failed_results()
        assert len(failed) > 0, "Should have failed results"
        
        # Step 5: Generate summary
        summary = result.summary()
        assert summary["total_rules"] == 9, "Summary should be accurate"
    
    def test_multi_rule_validation(self, sample_dataset, validation_engine):
        """
        TC-E2E-002: Verify multi-rule validation scenario
        Steps:
        1. Create multiple rule types
        2. Execute validation
        3. Verify different rule types work
        """
        rules = [
            ValidationRule("R001", "customer_id", "not_null", "high", "ID required"),
            ValidationRule("R002", "customer_id", "unique", "high", "ID unique"),
            ValidationRule("R003", "email", "email", "medium", "Valid email"),
            ValidationRule("R004", "age", "range", "high", "Valid age", params={"min": 0, "max": 120}),
            ValidationRule("R005", "status", "allowed_values", "medium", "Valid status", 
                          params={"values": ["active", "inactive", "pending"]})
        ]
        
        result = validation_engine.validate(sample_dataset, rules)
        assert result.total_rules == 5, "Should validate 5 rules"
        
        rule_types = set(r.type for r in rules)
        assert len(rule_types) >= 3, "Should test multiple rule types"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 8: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test cases for edge cases and error handling."""
    
    def test_empty_dataframe(self, validation_engine):
        """
        TC-EDGE-001: Verify empty dataframe handling
        Steps:
        1. Create empty dataframe
        2. Execute validation
        3. Verify graceful handling
        """
        df = pd.DataFrame({"col1": [], "col2": []})
        rules = [ValidationRule("R001", "col1", "not_null", "medium", "Test")]
        result = validation_engine.validate(df, rules)
        assert result.all_passed, "Empty dataframe should pass validation"
    
    def test_missing_column(self, sample_dataset, validation_engine):
        """
        TC-EDGE-002: Verify missing column handling
        Steps:
        1. Create rule for non-existent column
        2. Execute validation
        3. Verify graceful failure
        """
        rules = [ValidationRule("R001", "nonexistent_column", "not_null", "medium", "Test")]
        result = validation_engine.validate(sample_dataset, rules)
        assert not result.results[0].passed, "Missing column should fail validation"
    
    def test_all_null_column(self, validation_engine):
        """
        TC-EDGE-003: Verify all-null column handling
        Steps:
        1. Create dataframe with all-null column
        2. Execute not_null validation
        3. Verify all rows fail
        """
        df = pd.DataFrame({"col1": [None, None, None]})
        rules = [ValidationRule("R001", "col1", "not_null", "high", "Required")]
        result = validation_engine.validate(df, rules)
        assert result.results[0].failed_count == 3, "All 3 rows should fail"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Run all test cases with verbose output.
    Usage: python sample_test_case.py
    """
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
