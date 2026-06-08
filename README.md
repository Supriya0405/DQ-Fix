# 🚀 DQ-FIX: Data Quality Agent with Auto-Fix Suggestions

##  Team Information

### Team Name

SmartRemediate

### Team Number
Team27

### Team Members

* Supriya DV
* SURIYA A
* SUJAN ST
* SUMITHA R

---

# 🌐 Deliverable Links

## 🎥 Demo Video

https://www.loom.com/share/f3ac41243f184808b31a1ec2fa0d22f4

## 💻 GitHub Repository

https://github.com/Supriya0405/DQ-Fix

---

# 📌 Overview

DQ-FIX is an AI-powered Data Quality Agent designed to automatically detect, analyze, prioritize, and remediate data quality issues in enterprise datasets.

Traditional validation tools stop after identifying failures. DQ-FIX goes beyond validation by using Large Language Models (LLMs) to explain issues, generate remediation suggestions, apply fixes, and revalidate datasets through an autonomous Agent Loop.

The platform supports both CSV and Parquet datasets and provides a complete end-to-end workflow from dataset ingestion to cleaned dataset generation.

---

#  Problem Statement

Organizations frequently struggle with poor data quality caused by:

* Missing values
* Duplicate records
* Invalid email addresses
* Incorrect phone numbers
* Invalid dates
* Placeholder values
* Business rule violations
* Inconsistent formatting

Traditional validation frameworks identify errors but fail to answer critical questions:

* Why did the issue occur?
* What business impact does it create?
* How can it be fixed?
* How severe is the issue?
* Which records are affected?

DQ-FIX addresses these challenges using AI-powered reasoning, automated remediation, and iterative validation.

---

# 🎯 Features

## 📂 Dataset Processing

* CSV Reader
* Parquet Reader
* Dataset Preview
* Automatic Schema Detection
* Dataset Statistics

## 📋 AI-Generated YAML Rule Engine

The system automatically generates validation rules by analyzing:

* Column names
* Data types
* Sample values
* Data distributions
* Business context

Generated rules are stored in YAML format and can be edited without modifying application code.

---

## ✅ Advanced Data Quality Validation

Supports 30+ validation types:

### Core Validation Rules

* Not Null Validation
* Unique Validation
* Range Validation
* Regex Validation
* Email Validation
* Date Validation
* Phone Validation

### Advanced Validation Rules

* Allowed Values Validation
* Duplicate Row Detection
* Future Date Validation
* Age Validation
* Salary Validation
* Currency Validation
* Country Validation
* Placeholder Detection
* Missing Value Threshold Validation
* Outlier Detection
* Cross Field Validation
* Business Rule Validation
* Data Freshness Validation

---

## 🤖 AI-Powered Remediation Engine

Powered by:

* Ollama
* Groq
* OpenAI

The AI generates:

* Root Cause Analysis
* Human Readable Explanations
* Business Impact Analysis
* SQL Fix Suggestions
* Pandas Fix Suggestions
* Prevention Recommendations

---

## 🚨 Severity & Confidence Engine

Every failure is automatically prioritized using:

Severity Levels:

* Low
* Medium
* High

Confidence Score:

* 0–100%

This helps users focus on the most critical issues first.

---

## 🔄 Autonomous Agent Loop

The system implements a complete Agent Workflow:

Validation
↓
Failure Detection
↓
AI Analysis
↓
Generate Fix
↓
Apply Fix
↓
Revalidate
↓
Health Score Improvement

Maximum Iterations: 3

This transforms the application from a validation tool into an intelligent Data Quality Agent.

---

## 🌐 External API Integration

Email Verification API

Provides:

* Email Deliverability Validation
* Domain Verification
* Additional Confidence Assessment
* Enhanced Data Quality Checks

---

## 💾 Validation History & Audit Trail

All activities are stored in SQLite:

* Validation Runs
* Validation Results
* AI Analysis
* Generated Rules
* Agent Iterations
* Severity Scores
* Confidence Scores

This creates a complete audit trail for every dataset processed.

---

## 📊 Enterprise Dashboard

Built using Streamlit.

Features:

* Dataset Upload
* Dataset Preview
* Validation Results
* Failed Record Viewer
* AI Insights Panel
* Root Cause Analysis
* Severity Dashboard
* Confidence Dashboard
* Agent Loop Status
* Validation History
* Download Cleaned CSV

---

# 🏗 System Architecture

Dataset Upload
↓
CSV / Parquet Reader
↓
AI Rule Generation
↓
YAML Rule Engine
↓
Validation Engine
↓
Failed Record Detection
↓
LLM Analysis
↓
Severity & Confidence Engine
↓
Agent Loop
↓
Auto Fix Engine
↓
Revalidation
↓
SQLite Storage
↓
Dashboard Visualization
↓
Download Cleaned Dataset

---

# 🛠 Technology Stack

| Category        | Technology             |
| --------------- | ---------------------- |
| Frontend        | Streamlit              |
| Backend         | Python                 |
| Data Processing | Pandas                 |
| Configuration   | PyYAML                 |
| AI Models       | Ollama, Groq, OpenAI   |
| Database        | SQLite                 |
| API Integration | Email Verification API |
| Testing         | Pytest                 |
| Version Control | GitHub                 |

---

# 🏆 Key Innovations

* AI-Generated Validation Rules
* LLM-Based Root Cause Analysis
* SQL & Pandas Remediation Generation
* Autonomous Agent Loop
* Severity & Confidence Scoring
* Email Verification API Integration
* Health Score Calculation
* Downloadable Cleaned Dataset
* SQLite-Based Audit History
* Enterprise Dashboard Experience

---

# 🎯 Project Outcome

DQ-FIX successfully transforms traditional data validation into an AI-powered remediation platform by combining:

* Data Quality Validation
* AI Reasoning
* Automated Remediation
* Agentic Workflows
* Historical Tracking
* Interactive Analytics

The result is a smarter, faster, and more scalable approach to managing enterprise data quality.
