"""
SQLite Database Manager
=======================
Stores validation history, results, and agent loop audit trails.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional

from config.settings import DATABASE_PATH


class DatabaseManager:
    """Manages SQLite database for validation history and audit trails."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                dataset_name TEXT,
                total_rows INTEGER,
                total_rules INTEGER,
                passed_rules INTEGER,
                failed_rules INTEGER,
                total_failures INTEGER,
                status TEXT,
                metadata_json TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rule_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                rule_id TEXT,
                rule_type TEXT,
                column_name TEXT,
                severity TEXT,
                passed INTEGER,
                total_rows INTEGER,
                passed_count INTEGER,
                failed_count INTEGER,
                failed_indices_json TEXT,
                error_details_json TEXT,
                FOREIGN KEY (run_id) REFERENCES validation_runs(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                rule_id TEXT,
                root_cause TEXT,
                explanation TEXT,
                business_impact TEXT,
                sql_fix TEXT,
                pandas_fix TEXT,
                prevention TEXT,
                severity TEXT,
                confidence INTEGER,
                estimated_affected_rows INTEGER,
                permanent_fix TEXT,
                timestamp TEXT,
                FOREIGN KEY (run_id) REFERENCES validation_runs(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                iteration INTEGER,
                status TEXT,
                total_failures INTEGER,
                fixes_applied INTEGER,
                timestamp TEXT,
                details_json TEXT,
                FOREIGN KEY (run_id) REFERENCES validation_runs(id)
            )
        """)

        conn.commit()
        conn.close()

    def save_validation_run(self, dataset_name: str, total_rows: int,
                            validation_result, metadata: dict = None) -> int:
        """Save a validation run and return its ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO validation_runs
            (timestamp, dataset_name, total_rows, total_rules, passed_rules,
             failed_rules, total_failures, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            dataset_name,
            total_rows,
            validation_result.total_rules,
            validation_result.passed_rules,
            validation_result.failed_rules,
            validation_result.total_failures,
            "passed" if validation_result.all_passed else "failed",
            json.dumps(metadata or {}),
        ))

        run_id = cursor.lastrowid

        # Save individual rule results
        for r in validation_result.results:
            cursor.execute("""
                INSERT INTO rule_results
                (run_id, rule_id, rule_type, column_name, severity, passed,
                 total_rows, passed_count, failed_count, failed_indices_json, error_details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, r.rule_id, r.rule_type, r.column, r.severity,
                1 if r.passed else 0, r.total_rows, r.passed_count, r.failed_count,
                json.dumps(r.failed_row_indices), json.dumps(r.error_details[:20]),
            ))

        conn.commit()
        conn.close()
        return run_id

    def save_ai_analysis(self, run_id: int, analysis: dict):
        """Save an AI analysis result."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_analyses
            (run_id, rule_id, root_cause, explanation, business_impact,
             sql_fix, pandas_fix, prevention, severity, confidence,
             estimated_affected_rows, permanent_fix, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, analysis.get("rule_id", ""),
            analysis.get("root_cause", ""), analysis.get("explanation", ""),
            analysis.get("business_impact", ""), analysis.get("sql_fix", ""),
            analysis.get("pandas_fix", ""), analysis.get("prevention", ""),
            analysis.get("severity", ""), analysis.get("confidence", 0),
            analysis.get("estimated_affected_rows", 0),
            analysis.get("permanent_fix", ""), datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()

    def save_agent_iteration(self, run_id: int, iteration: int, status: str,
                             total_failures: int, fixes_applied: int, details: dict = None):
        """Save an agent loop iteration."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_iterations
            (run_id, iteration, status, total_failures, fixes_applied, timestamp, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, iteration, status, total_failures, fixes_applied,
            datetime.now().isoformat(), json.dumps(details or {}),
        ))
        conn.commit()
        conn.close()

    def get_validation_history(self, limit: int = 20) -> List[dict]:
        """Get recent validation runs."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, dataset_name, total_rows, total_rules,
                   passed_rules, failed_rules, total_failures, status
            FROM validation_runs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": r[0], "timestamp": r[1], "dataset_name": r[2],
                "total_rows": r[3], "total_rules": r[4], "passed_rules": r[5],
                "failed_rules": r[6], "total_failures": r[7], "status": r[8],
            }
            for r in rows
        ]

    def get_run_details(self, run_id: int) -> dict:
        """Get full details of a validation run."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM validation_runs WHERE id = ?", (run_id,))
        run = cursor.fetchone()
        if not run:
            conn.close()
            return {}

        cursor.execute("SELECT * FROM rule_results WHERE run_id = ?", (run_id,))
        rules = cursor.fetchall()

        cursor.execute("SELECT * FROM ai_analyses WHERE run_id = ?", (run_id,))
        analyses = cursor.fetchall()

        conn.close()

        return {
            "run": {
                "id": run[0], "timestamp": run[1], "dataset_name": run[2],
                "total_rows": run[3], "total_rules": run[4],
            },
            "rules": [
                {"rule_id": r[2], "type": r[3], "column": r[4], "severity": r[5],
                 "passed": bool(r[6]), "failed_count": r[9]}
                for r in rules
            ],
            "analyses": [
                {"rule_id": a[2], "root_cause": a[3], "sql_fix": a[6],
                 "pandas_fix": a[7], "severity": a[9], "confidence": a[10]}
                for a in analyses
            ],
        }
