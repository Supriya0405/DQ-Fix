#!/usr/bin/env python3
"""
DQ-FIX Agent Loop Runner — Generate Solutions for Data Quality Problems
=========================================================================
Runs the autonomous agent loop on sample data and generates AI-powered fixes.

Usage:
    python run_agent_with_fixes.py

This script:
    1. Loads invalid customer data
    2. Loads validation rules
    3. Runs the agent loop (validate → analyze → fix → re-validate)
    4. Generates proper fixes for all identified problems
    5. Outputs a comprehensive report with solutions
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    SAMPLE_DATA_DIR, DEFAULT_RULES_PATH,
    GROQ_API_KEY, OPENAI_API_KEY, DEFAULT_PROVIDER
)
from src.readers.csv_reader import CSVReader
from src.rules.rule_engine import RuleEngine
from src.validators.validation_engine import ValidationEngine
from src.ai.llm_client import LLMClient
from src.ai.severity_engine import SeverityEngine
from src.agent.agent_loop import AgentLoop
from src.fixer.auto_fixer import AutoFixer


class AgentLoopRunner:
    """Run agent loop and generate comprehensive fix report."""
    
    def __init__(self):
        self.reader = CSVReader()
        self.rule_engine = RuleEngine(yaml_path=DEFAULT_RULES_PATH)
        self.validator = ValidationEngine()
        self.severity_engine = SeverityEngine()
        self.auto_fixer = AutoFixer()
        
        # Initialize LLM with available API keys
        self.llm = self._init_llm()
        self.agent_loop = AgentLoop(llm=self.llm)
        
    def _init_llm(self) -> LLMClient:
        """Initialize LLM client with configured provider."""
        provider = DEFAULT_PROVIDER
        api_key = ""
        
        # Try providers in order of preference
        if provider == "groq" and GROQ_API_KEY:
            api_key = GROQ_API_KEY
            print(f"✓ Using Groq LLM (Free API)")
        elif provider == "openai" and OPENAI_API_KEY:
            api_key = OPENAI_API_KEY
            print(f"✓ Using OpenAI LLM (Paid)")
        elif GROQ_API_KEY:  # Fallback to Groq if available
            provider = "groq"
            api_key = GROQ_API_KEY
            print(f"✓ Using Groq LLM (Free API)")
        elif OPENAI_API_KEY:  # Fallback to OpenAI
            provider = "openai"
            api_key = OPENAI_API_KEY
            print(f"✓ Using OpenAI LLM (Paid)")
        else:
            print("⚠ No API keys found, will use Ollama (requires local setup)")
            provider = "ollama"
        
        return LLMClient(provider=provider, api_key=api_key)
    
    def run(self):
        """Run the complete analysis and fix workflow."""
        print("=" * 80)
        print("DQ-FIX AGENT LOOP — ANALYZING DATA QUALITY ISSUES")
        print("=" * 80)
        
        # Step 1: Load data
        print("\n[1/5] Loading invalid customer data...")
        invalid_path = os.path.join(SAMPLE_DATA_DIR, "invalid_customers.csv")
        df, info = self.reader.read(invalid_path)
        print(f"    ✓ Loaded {info['rows']} rows × {info['columns']} columns")
        print(f"    File: {invalid_path}")
        
        # Step 2: Load rules
        print("\n[2/5] Loading validation rules...")
        rules = self.rule_engine.get_rules()
        print(f"    ✓ Loaded {len(rules)} validation rules")
        
        # Step 3: Initial validation
        print("\n[3/5] Running initial validation...")
        initial_result = self.validator.validate(df, rules)
        print(f"    • Total rules: {initial_result.total_rules}")
        print(f"    • Passed: {initial_result.passed_rules}")
        print(f"    • Failed: {initial_result.failed_rules}")
        print(f"    • Total failures: {initial_result.total_failures}")
        
        # Step 4: Run agent loop
        print("\n[4/5] Running autonomous agent loop (validate → analyze → fix → re-validate)...")
        agent_result = self.agent_loop.run(df, rules)
        
        print(f"    • Status: {agent_result['status']}")
        print(f"    • Iterations: {agent_result['total_iterations']}")
        
        for i, iteration in enumerate(agent_result['iterations'], 1):
            print(f"\n    Iteration {i}:")
            print(f"      - Passed rules: {iteration['passed_rules']}")
            print(f"      - Failed rules: {iteration['failed_rules']}")
            print(f"      - Total failures: {iteration['total_failures']}")
            print(f"      - Fixes applied: {len(iteration['fixes_applied'])}")
        
        # Step 5: Generate comprehensive report
        print("\n[5/5] Generating comprehensive fix report...")
        report = self._generate_report(df, agent_result, initial_result, rules)
        
        return report, df, agent_result
    
    def _generate_report(self, df, agent_result, initial_result, rules):
        """Generate comprehensive fix report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_rows": len(df),
                "initial_failures": initial_result.total_failures,
                "final_failures": agent_result['iterations'][-1]['total_failures'] if agent_result['iterations'] else 0,
                "agent_iterations": agent_result['total_iterations'],
                "status": agent_result['status'],
            },
            "problems": [],
            "solutions": [],
            "statistics": {}
        }
        
        # Analyze initial failures
        failed_results = initial_result.get_failed_results()
        
        print(f"\n{'='*80}")
        print("PROBLEMS IDENTIFIED:")
        print(f"{'='*80}\n")
        
        problem_index = 1
        for rule_result in failed_results:
            problem = {
                "id": f"P{problem_index:03d}",
                "rule_id": rule_result.rule_id,
                "rule_type": rule_result.rule_type,
                "column": rule_result.column,
                "severity": rule_result.severity,
                "failed_count": rule_result.failed_count,
                "total_rows": rule_result.total_rows,
                "affected_indices": list(rule_result.failed_row_indices)[:10] if hasattr(rule_result, 'failed_row_indices') else [],
            }
            
            # Get sample rows
            if rule_result.failed_samples is not None and len(rule_result.failed_samples) > 0:
                problem["sample_failures"] = rule_result.failed_samples.to_dict('records')[:3]
            
            report["problems"].append(problem)
            
            # Print problem
            print(f"PROBLEM {problem_index}: {rule_result.rule_type} validation on '{rule_result.column}'")
            print(f"  Rule ID: {rule_result.rule_id}")
            print(f"  Severity: {rule_result.severity.upper()}")
            print(f"  Failed rows: {rule_result.failed_count}/{rule_result.total_rows}")
            if hasattr(rule_result, 'failed_row_indices'):
                print(f"  Affected indices: {list(rule_result.failed_row_indices)[:5]}...")
            print()
            
            problem_index += 1
        
        # Generate solutions from agent analyses
        print(f"\n{'='*80}")
        print("SOLUTIONS GENERATED BY AI AGENT:")
        print(f"{'='*80}\n")
        
        solution_index = 1
        for iteration in agent_result['iterations']:
            for analysis in iteration.get('ai_analyses', []):
                solution = {
                    "id": f"S{solution_index:03d}",
                    "iteration": iteration['iteration'],
                    "rule_id": analysis.get('rule_id'),
                    "rule_type": analysis.get('rule_type'),
                    "column": analysis.get('column'),
                    "root_cause": analysis.get('root_cause', 'N/A'),
                    "explanation": analysis.get('explanation', 'N/A'),
                    "pandas_fix": analysis.get('pandas_fix', 'N/A'),
                    "confidence": analysis.get('confidence', 0),
                    "severity": analysis.get('severity', 'medium'),
                }
                
                report["solutions"].append(solution)
                
                # Print solution
                print(f"SOLUTION {solution_index}: {solution['rule_type']} on '{solution['column']}'")
                print(f"  Confidence: {solution['confidence']}%")
                print(f"  Root Cause: {solution['root_cause']}")
                print(f"  Explanation: {solution['explanation']}")
                if solution['pandas_fix'] != 'N/A':
                    print(f"  Fix: {solution['pandas_fix'][:100]}...")
                print()
                
                solution_index += 1
        
        # Calculate statistics
        report["statistics"] = {
            "total_problems": len(report["problems"]),
            "total_solutions": len(report["solutions"]),
            "high_severity": len([p for p in report["problems"] if p["severity"] == "high"]),
            "medium_severity": len([p for p in report["problems"] if p["severity"] == "medium"]),
            "low_severity": len([p for p in report["problems"] if p["severity"] == "low"]),
            "average_confidence": (
                sum(s["confidence"] for s in report["solutions"]) / len(report["solutions"])
                if report["solutions"] else 0
            ),
        }
        
        return report


def main():
    """Main entry point."""
    try:
        runner = AgentLoopRunner()
        report, df, agent_result = runner.run()
        
        # Save report
        report_path = os.path.join(
            os.path.dirname(__file__),
            f"agent_loop_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n{'='*80}")
        print("FINAL STATISTICS:")
        print(f"{'='*80}")
        print(f"  Total problems identified: {report['statistics']['total_problems']}")
        print(f"  Solutions generated: {report['statistics']['total_solutions']}")
        print(f"  High severity issues: {report['statistics']['high_severity']}")
        print(f"  Medium severity issues: {report['statistics']['medium_severity']}")
        print(f"  Low severity issues: {report['statistics']['low_severity']}")
        print(f"  Average AI confidence: {report['statistics']['average_confidence']:.1f}%")
        print(f"\n✓ Full report saved to: {report_path}")
        print(f"{'='*80}\n")
        
        # Save cleaned data
        cleaned_path = os.path.join(
            os.path.dirname(__file__),
            f"cleaned_customers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        final_df = agent_result['final_df']
        final_df.to_csv(cleaned_path, index=False)
        print(f"✓ Cleaned data saved to: {cleaned_path}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
