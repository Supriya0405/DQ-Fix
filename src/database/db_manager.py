"""
SQLite Database Manager — Persistence & Audit Layer
====================================================
Stores validation history, AI analysis, remediation suggestions,
API validation results, and Agent Loop execution details.

Tables (7):
    1. validation_runs       — Track every validation execution
    2. validation_results    — Track individual rule pass/fail
    3. failed_records        — Store sample failed rows
    4. ai_analysis           — AI-generated root cause & explanations
    5. remediation_suggestions — AI-generated SQL/Pandas fixes
    6. agent_iterations      — Agent Loop execution audit trail
    7. api_validation_results — External API (email) validation results

Usage:
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager()
    run_id = db.save_validation_run("data.csv", 1000, result)
    history = db.get_validation_history(limit=10)
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from config.settings import DATABASE_PATH

# ─── Logging Configuration ───────────────────────────────────────────────
logger = logging.getLogger("dq_database")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s DB: %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)


class DatabaseManager:
    """Manages SQLite database for validation history and audit trails."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.conn = self._get_conn()
        self._init_db()
        logger.info(f"Database initialized at {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ═══════════════════════════════════════════════════════════════════════
    # SCHEMA CREATION (7 Tables)
    # ═══════════════════════════════════════════════════════════════════════

    def _init_db(self):
        """Create all 7 tables if they don't exist."""
        try:
            cursor = self.conn.cursor()

            # Table 1: validation_runs — Track every validation execution
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_name TEXT NOT NULL,
                    total_rows INTEGER NOT NULL,
                    total_columns INTEGER DEFAULT 0,
                    total_rules INTEGER DEFAULT 0,
                    passed_rules INTEGER DEFAULT 0,
                    failed_rules INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    overall_status TEXT DEFAULT 'pending',
                    validation_timestamp TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                )
            """)

            # Table 2: validation_results — Track individual rule pass/fail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    rule_id TEXT,
                    column_name TEXT,
                    validation_type TEXT,
                    severity TEXT DEFAULT 'medium',
                    confidence_score INTEGER DEFAULT 0,
                    passed INTEGER DEFAULT 0,
                    total_rows INTEGER DEFAULT 0,
                    passed_count INTEGER DEFAULT 0,
                    failed_rows INTEGER DEFAULT 0,
                    failed_indices_json TEXT DEFAULT '[]',
                    error_details_json TEXT DEFAULT '[]',
                    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
                        ON DELETE CASCADE
                )
            """)

            # Table 3: failed_records — Store sample failed rows
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    result_id INTEGER,
                    column_name TEXT,
                    row_index INTEGER,
                    invalid_value TEXT,
                    failure_reason TEXT,
                    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
                        ON DELETE CASCADE
                )
            """)

            # Table 4: ai_analysis — AI-generated explanations & root cause
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    result_id INTEGER,
                    rule_id TEXT,
                    validation_type TEXT,
                    column_name TEXT,
                    root_cause TEXT,
                    explanation TEXT,
                    business_impact TEXT,
                    recommendation TEXT,
                    severity TEXT DEFAULT 'medium',
                    confidence_score INTEGER DEFAULT 0,
                    estimated_affected_rows INTEGER DEFAULT 0,
                    permanent_fix TEXT,
                    provider TEXT DEFAULT 'fallback',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
                        ON DELETE CASCADE
                )
            """)

            # Table 5: remediation_suggestions — AI-generated fixes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remediation_suggestions (
                    remediation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    result_id INTEGER,
                    rule_id TEXT,
                    validation_type TEXT,
                    column_name TEXT,
                    sql_fix TEXT,
                    pandas_fix TEXT,
                    confidence_score INTEGER DEFAULT 0,
                    fix_applied INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
                        ON DELETE CASCADE
                )
            """)

            # Table 6: agent_iterations — Agent Loop execution audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_iterations (
                    iteration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    iteration_number INTEGER NOT NULL,
                    action_taken TEXT,
                    passed_rules INTEGER DEFAULT 0,
                    failed_rules INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    fixes_applied INTEGER DEFAULT 0,
                    validation_status TEXT DEFAULT 'pending',
                    timestamp TEXT NOT NULL,
                    details_json TEXT DEFAULT '{}',
                    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
                        ON DELETE CASCADE
                )
            """)

            # Table 7: api_validation_results — External API results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_validation_results (
                    api_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    email TEXT NOT NULL,
                    api_status TEXT,
                    is_valid INTEGER DEFAULT 0,
                    confidence_score INTEGER DEFAULT 0,
                    response_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)

            self.conn.commit()
            logger.info("All 7 tables verified/created successfully")

        except sqlite3.Error as e:
            logger.error(f"Schema creation failed: {e}")
            raise

    # ═══════════════════════════════════════════════════════════════════════
    # INSERT OPERATIONS (CREATE)
    # ═══════════════════════════════════════════════════════════════════════

    def save_validation_run(self, dataset_name: str, total_rows: int,
                            validation_result, total_columns: int = 0,
                            metadata: dict = None) -> int:
        """Save a validation run + individual results + failed records. Returns run_id."""
        try:
            cursor = self.conn.cursor()

            # Insert validation run
            cursor.execute("""
                INSERT INTO validation_runs
                (dataset_name, total_rows, total_columns, total_rules, passed_rules,
                 failed_rules, total_failures, overall_status, validation_timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_name, total_rows, total_columns,
                validation_result.total_rules, validation_result.passed_rules,
                validation_result.failed_rules, validation_result.total_failures,
                "passed" if validation_result.all_passed else "failed",
                datetime.now().isoformat(), json.dumps(metadata or {}),
            ))
            run_id = cursor.lastrowid

            # Insert individual rule results
            for r in validation_result.results:
                cursor.execute("""
                    INSERT INTO validation_results
                    (run_id, rule_id, column_name, validation_type, severity,
                     confidence_score, passed, total_rows, passed_count, failed_rows,
                     failed_indices_json, error_details_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, r.rule_id, r.column, r.rule_type, r.severity, 0,
                    1 if r.passed else 0, r.total_rows, r.passed_count, r.failed_count,
                    json.dumps(r.failed_row_indices[:50]), json.dumps(r.error_details[:20]),
                ))

                # Insert failed records (sample up to 10 per rule)
                if not r.passed and r.failed_samples is not None:
                    for idx, (row_idx, row) in enumerate(r.failed_samples.head(10).iterrows()):
                        invalid_val = str(row.get(r.column, ""))[:200]
                        reason = r.error_details[idx] if idx < len(r.error_details) else r.rule_type
                        cursor.execute("""
                            INSERT INTO failed_records
                            (run_id, result_id, column_name, row_index, invalid_value, failure_reason)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (run_id, cursor.lastrowid, r.column, int(row_idx),
                              invalid_val, reason))

            self.conn.commit()
            logger.info(f"Saved validation run #{run_id}: {dataset_name} ({total_rows} rows, "
                       f"{validation_result.passed_rules}/{validation_result.total_rules} passed)")
            return run_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save validation run: {e}")
            self.conn.rollback()
            return -1

    def save_ai_analysis(self, run_id: int, analysis: dict):
        """Save an AI analysis result."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO ai_analysis
                (run_id, rule_id, validation_type, column_name, root_cause, explanation,
                 business_impact, recommendation, severity, confidence_score,
                 estimated_affected_rows, permanent_fix, provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, analysis.get("rule_id", ""),
                analysis.get("rule_type", ""), analysis.get("column", ""),
                analysis.get("root_cause", ""), analysis.get("explanation", ""),
                analysis.get("business_impact", ""), analysis.get("prevention", ""),
                analysis.get("severity", "medium"), analysis.get("confidence", 0),
                analysis.get("estimated_affected_rows", 0),
                analysis.get("permanent_fix", ""),
                analysis.get("provider", "fallback"),
                datetime.now().isoformat(),
            ))

            # Also save remediation suggestion
            if analysis.get("sql_fix") or analysis.get("pandas_fix"):
                cursor.execute("""
                    INSERT INTO remediation_suggestions
                    (run_id, rule_id, validation_type, column_name,
                     sql_fix, pandas_fix, confidence_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, analysis.get("rule_id", ""),
                    analysis.get("rule_type", ""), analysis.get("column", ""),
                    analysis.get("sql_fix", ""), analysis.get("pandas_fix", ""),
                    analysis.get("confidence", 0), datetime.now().isoformat(),
                ))

            self.conn.commit()
            logger.info(f"Saved AI analysis for run #{run_id}, rule {analysis.get('rule_id', '')}")

        except sqlite3.Error as e:
            logger.error(f"Failed to save AI analysis: {e}")
            self.conn.rollback()

    def save_agent_iteration(self, run_id: int, iteration: int, status: str,
                             passed_rules: int = 0, failed_rules: int = 0,
                             total_failures: int = 0, fixes_applied: int = 0,
                             action_taken: str = "", details: dict = None):
        """Save an agent loop iteration."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO agent_iterations
                (run_id, iteration_number, action_taken, passed_rules, failed_rules,
                 total_failures, fixes_applied, validation_status, timestamp, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, iteration, action_taken or f"Iteration {iteration}: {status}",
                passed_rules, failed_rules, total_failures, fixes_applied,
                status, datetime.now().isoformat(), json.dumps(details or {}),
            ))
            self.conn.commit()
            logger.info(f"Saved agent iteration #{iteration} for run #{run_id}: {status}")

        except sqlite3.Error as e:
            logger.error(f"Failed to save agent iteration: {e}")
            self.conn.rollback()

    def save_api_validation(self, email: str, result: dict, run_id: int = None):
        """Save an external API validation result."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO api_validation_results
                (run_id, email, api_status, is_valid, confidence_score, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, email, result.get("api_status", "unknown"),
                1 if result.get("is_valid") else 0,
                result.get("confidence", 0),
                json.dumps(result), datetime.now().isoformat(),
            ))
            self.conn.commit()
            logger.info(f"Saved API validation for {email}: {result.get('api_status', 'unknown')}")

        except sqlite3.Error as e:
            logger.error(f"Failed to save API validation: {e}")
            self.conn.rollback()

    # ═══════════════════════════════════════════════════════════════════════
    # UPDATE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def update_run_status(self, run_id: int, status: str):
        """Update the overall status of a validation run."""
        try:
            self.conn.execute(
                "UPDATE validation_runs SET overall_status = ? WHERE run_id = ?",
                (status, run_id)
            )
            self.conn.commit()
            logger.info(f"Updated run #{run_id} status to {status}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update run status: {e}")
            self.conn.rollback()

    def mark_remediation_applied(self, remediation_id: int):
        """Mark a remediation suggestion as applied."""
        try:
            self.conn.execute(
                "UPDATE remediation_suggestions SET fix_applied = 1 WHERE remediation_id = ?",
                (remediation_id,)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to mark remediation: {e}")
            self.conn.rollback()

    # ═══════════════════════════════════════════════════════════════════════
    # QUERY OPERATIONS (READ)
    # ═══════════════════════════════════════════════════════════════════════

    def get_validation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent validation runs."""
        try:
            cursor = self.conn.execute("""
                SELECT run_id, validation_timestamp, dataset_name, total_rows,
                       total_columns, total_rules, passed_rules, failed_rules,
                       total_failures, overall_status
                FROM validation_runs
                ORDER BY validation_timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get validation history: {e}")
            return []

    def get_run_details(self, run_id: int) -> Dict:
        """Get full details of a validation run (results + analyses + remediations)."""
        try:
            run = self.conn.execute(
                "SELECT * FROM validation_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not run:
                return {}

            results = self.conn.execute(
                "SELECT * FROM validation_results WHERE run_id = ?", (run_id,)
            ).fetchall()

            analyses = self.conn.execute(
                "SELECT * FROM ai_analysis WHERE run_id = ?", (run_id,)
            ).fetchall()

            remediations = self.conn.execute(
                "SELECT * FROM remediation_suggestions WHERE run_id = ?", (run_id,)
            ).fetchall()

            iterations = self.conn.execute(
                "SELECT * FROM agent_iterations WHERE run_id = ?", (run_id,)
            ).fetchall()

            failed = self.conn.execute(
                "SELECT * FROM failed_records WHERE run_id = ? LIMIT 100", (run_id,)
            ).fetchall()

            return {
                "run": dict(run),
                "results": [dict(r) for r in results],
                "analyses": [dict(a) for a in analyses],
                "remediations": [dict(r) for r in remediations],
                "iterations": [dict(i) for i in iterations],
                "failed_records": [dict(f) for f in failed],
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get run details: {e}")
            return {}

    def get_ai_analysis_history(self, run_id: int = None, limit: int = 50) -> List[Dict]:
        """Get AI analysis history, optionally filtered by run_id."""
        try:
            if run_id:
                cursor = self.conn.execute(
                    "SELECT * FROM ai_analysis WHERE run_id = ? ORDER BY created_at DESC",
                    (run_id,)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM ai_analysis ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get AI history: {e}")
            return []

    def get_remediation_history(self, run_id: int = None, limit: int = 50) -> List[Dict]:
        """Get remediation suggestions history."""
        try:
            if run_id:
                cursor = self.conn.execute(
                    "SELECT * FROM remediation_suggestions WHERE run_id = ? ORDER BY created_at DESC",
                    (run_id,)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM remediation_suggestions ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get remediation history: {e}")
            return []

    def get_agent_iterations(self, run_id: int = None, limit: int = 50) -> List[Dict]:
        """Get agent loop iteration history."""
        try:
            if run_id:
                cursor = self.conn.execute(
                    "SELECT * FROM agent_iterations WHERE run_id = ? ORDER BY iteration_number",
                    (run_id,)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM agent_iterations ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get agent iterations: {e}")
            return []

    def get_api_validation_history(self, limit: int = 50) -> List[Dict]:
        """Get external API validation history."""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM api_validation_results
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get API history: {e}")
            return []

    def get_failed_records(self, run_id: int, limit: int = 100) -> List[Dict]:
        """Get failed records for a specific run."""
        try:
            cursor = self.conn.execute("""
                SELECT * FROM failed_records
                WHERE run_id = ? LIMIT ?
            """, (run_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get failed records: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # DELETE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def delete_run(self, run_id: int):
        """Delete a validation run and all related data (CASCADE)."""
        try:
            self.conn.execute("DELETE FROM validation_runs WHERE run_id = ?", (run_id,))
            self.conn.commit()
            logger.info(f"Deleted run #{run_id} and all related data")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete run: {e}")
            self.conn.rollback()

    def clear_all_history(self):
        """Delete all data from all tables."""
        try:
            for table in ["api_validation_results", "agent_iterations",
                          "remediation_suggestions", "ai_analysis",
                          "failed_records", "validation_results", "validation_runs"]:
                self.conn.execute(f"DELETE FROM {table}")
            self.conn.commit()
            logger.info("Cleared all database history")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear history: {e}")
            self.conn.rollback()

    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS / SUMMARY
    # ═══════════════════════════════════════════════════════════════════════

    def get_statistics(self) -> Dict:
        """Get overall database statistics."""
        try:
            stats = {}
            for table in ["validation_runs", "validation_results", "failed_records",
                          "ai_analysis", "remediation_suggestions",
                          "agent_iterations", "api_validation_results"]:
                count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count

            # Aggregate stats
            total_passed = self.conn.execute(
                "SELECT SUM(passed_rules) FROM validation_runs"
            ).fetchone()[0] or 0
            total_failed = self.conn.execute(
                "SELECT SUM(failed_rules) FROM validation_runs"
            ).fetchone()[0] or 0
            stats["total_rules_checked"] = total_passed + total_failed
            stats["pass_rate"] = round(total_passed / max(1, total_passed + total_failed) * 100, 1)

            return stats
        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
