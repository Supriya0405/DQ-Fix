"""
Agent Loop — Autonomous Fix-Revalidate Cycle
=============================================
Implements the core agent loop: Validate → Fail → LLM Fix → Apply → Re-validate.
Maximum 3 iterations. Stops early if all validations pass.
"""

import pandas as pd
from typing import List, Optional
from datetime import datetime

from src.validators.validation_engine import ValidationEngine
from src.rules.rule_engine import ValidationRule
from src.validators.result_models import ValidationResult
from src.ai.llm_client import LLMClient
from src.ai.severity_engine import SeverityEngine
from src.fixer.auto_fixer import AutoFixer
from config.settings import MAX_AGENT_ITERATIONS


class AgentLoop:
    """
    Autonomous agent that validates data, identifies failures,
    gets AI fix suggestions, applies fixes, and re-validates.
    """

    def __init__(self, max_iterations: int = MAX_AGENT_ITERATIONS, llm=None):
        self.max_iterations = max_iterations
        self.validator = ValidationEngine()
        self.llm = llm or LLMClient()
        self.severity_engine = SeverityEngine()
        self.history: List[dict] = []
        self.current_iteration = 0
        self.status = "idle"  # idle, running, completed, failed

    def run(self, df: pd.DataFrame, rules: List[ValidationRule]) -> dict:
        """
        Execute the agent loop.

        Returns
        -------
        dict with:
            - iterations: list of iteration results
            - final_df: the cleaned DataFrame
            - total_iterations: number of iterations run
            - status: completed/failed/max_reached
            - history: full audit trail
        """
        self.history = []
        self.status = "running"
        current_df = df.copy()
        iterations = []

        for iteration in range(1, self.max_iterations + 1):
            self.current_iteration = iteration
            self.status = f"running_iteration_{iteration}"

            # Step 1: Validate
            result = self.validator.validate(current_df, rules)
            iteration_data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "total_rules": result.total_rules,
                "passed_rules": result.passed_rules,
                "failed_rules": result.failed_rules,
                "total_failures": result.total_failures,
                "all_passed": result.all_passed,
                "ai_analyses": [],
                "fixes_applied": [],
            }

            # Step 2: Check if all passed
            if result.all_passed:
                iteration_data["status"] = "all_passed"
                iterations.append(iteration_data)
                self.status = "completed"
                break

            # Step 3: Analyze failures with LLM (or fallback)
            failed_results = result.get_failed_results()
            llm_available = self.llm.is_available()
            for rule_result in failed_results:
                analysis = self.llm.analyze_failure(
                    rule_result,
                    sample_rows_df=rule_result.failed_samples,
                    column_info=str(current_df[rule_result.column].dtype) if rule_result.column in current_df.columns else None,
                )

                # Add severity and confidence
                analysis["severity"] = self.severity_engine.calculate_severity(
                    rule_result.rule_type, rule_result.failed_count,
                    rule_result.total_rows, rule_result.severity,
                )
                analysis["confidence"] = self.severity_engine.calculate_confidence(
                    rule_result.rule_type, rule_result.failed_count,
                    rule_result.total_rows, bool(rule_result.params if hasattr(rule_result, 'params') else True),
                    llm_available,
                )
                analysis["rule_id"] = rule_result.rule_id
                analysis["rule_type"] = rule_result.rule_type
                analysis["column"] = rule_result.column
                analysis["failed_count"] = rule_result.failed_count
                iteration_data["ai_analyses"].append(analysis)

            # Step 4: Apply fixes
            current_df, fixes_applied = self._apply_fixes(current_df, iteration_data["ai_analyses"])
            iteration_data["fixes_applied"] = fixes_applied
            iteration_data["status"] = "fixes_applied" if fixes_applied else "no_fixes"

            iterations.append(iteration_data)
            self.history.append(iteration_data)

        # Determine final status
        if self.status != "completed":
            self.status = "max_reached" if iterations else "failed"

        return {
            "iterations": iterations,
            "final_df": current_df,
            "total_iterations": len(iterations),
            "status": self.status,
            "history": self.history,
        }

    def _apply_fixes(self, df: pd.DataFrame, analyses: List[dict]):
        """Apply Pandas-based fixes from AI analyses and fallback typed fixes."""
        applied = []
        fixer = AutoFixer()
        current_df = df

        for analysis in analyses:
            pandas_fix = analysis.get("pandas_fix", "")
            rule_type = analysis.get("rule_type", "")
            column = analysis.get("column", "")

            if not pandas_fix or (column not in current_df.columns and column != "_all"):
                continue

            success = False
            fix_description = pandas_fix.strip()

            try:
                # Prefer AI-generated pandas fix code when available.
                if pandas_fix and "df" in pandas_fix:
                    updated_df = fixer.apply_pandas_fix(current_df, pandas_fix)
                    if not updated_df.equals(current_df):
                        current_df = updated_df
                        success = True
                # Fallback to typed fix if AI code did not modify the DataFrame.
                if not success:
                    typed_fix = self._apply_typed_fix(current_df, rule_type, column)
                    if typed_fix and "No automatic fix available" not in typed_fix:
                        success = True
                        fix_description = typed_fix
            except Exception as e:
                success = False
                fix_description = f"Fix failed: {e}"

            applied.append({
                "rule_id": analysis.get("rule_id"),
                "column": column,
                "rule_type": rule_type,
                "fix_description": fix_description,
                "success": success,
            })

        return current_df, applied

    def _apply_typed_fix(self, df: pd.DataFrame, rule_type: str, column: str) -> str:
        """Apply a typed fix based on the validation rule type."""
        if rule_type == "not_null":
            if df[column].dtype in ("int64", "float64"):
                median_val = df[column].median()
                df[column] = df[column].fillna(median_val)
                return f"Filled nulls with median ({median_val})"
            else:
                mode_val = df[column].mode().iloc[0] if not df[column].mode().empty else "Unknown"
                df[column] = df[column].fillna(mode_val)
                # Also fill empty strings
                empty_mask = df[column].astype(str).str.strip() == ""
                if empty_mask.any():
                    df.loc[empty_mask, column] = mode_val
                return f"Filled nulls/empty with mode ('{mode_val}')"

        elif rule_type == "unique":
            # Keep first occurrence, mark duplicates
            dup_mask = df[column].duplicated(keep="first")
            if dup_mask.any():
                df[column] = df[column].astype(object)
                df.loc[dup_mask, column] = df.loc[dup_mask, column].astype(str) + "_dup"
                return f"Appended '_dup' suffix to {dup_mask.sum()} duplicates"

        elif rule_type in ("range", "age", "salary", "transaction_amount"):
            col = pd.to_numeric(df[column], errors="coerce")
            outlier_mask = col.isna() & self._non_null_mask(df[column])
            if outlier_mask.any():
                df.loc[outlier_mask, column] = None
                return f"Set {outlier_mask.sum()} non-numeric values to null"

        elif rule_type in ("regex", "phone", "customer_id_pattern"):
            return "Flagged non-matching values for manual review"

        elif rule_type == "email":
            # Try to fix common email issues
            col = df[column].astype(str)
            invalid = ~col.str.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", na=False)
            df.loc[invalid & self._non_null_mask(df[column]), column] = None
            return f"Set {invalid.sum()} invalid emails to null"

        elif rule_type in ("date", "date_format", "future_date"):
            parsed = pd.to_datetime(df[column], errors="coerce")
            valid = parsed.notna()
            if valid.any():
                df.loc[valid, column] = parsed.loc[valid].dt.strftime("%Y-%m-%d")
            invalid = ~valid & self._non_null_mask(df[column])
            if invalid.any():
                df.loc[invalid, column] = None
                return f"Standardized {valid.sum()} dates and cleared {invalid.sum()} invalid ones"
            return "Standardized dates"

        elif rule_type == "placeholder":
            placeholders = {"N/A", "NA", "null", "none", "TODO", "TBD", "XXX", "test", "dummy", "placeholder", "-", "."}
            mask = df[column].astype(str).str.strip().str.lower().isin(
                set(p.lower() for p in placeholders)
            ) & self._non_null_mask(df[column])
            if mask.any():
                df.loc[mask, column] = None
                return f"Replaced {mask.sum()} placeholder values with null"

        elif rule_type == "duplicate_row":
            dup_mask = df.duplicated(keep="first")
            if dup_mask.any():
                count = dup_mask.sum()
                df.drop(df[dup_mask].index, inplace=True)
                df.reset_index(drop=True, inplace=True)
                return f"Removed {count} duplicate rows"

        return "No automatic fix available"

    def _non_null_mask(self, col):
        mask = col.notna()
        if col.dtype == object:
            mask = mask & (col.astype(str).str.strip() != "")
        return mask

    def get_status(self) -> dict:
        """Return current agent loop status."""
        return {
            "status": self.status,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "history_count": len(self.history),
        }
