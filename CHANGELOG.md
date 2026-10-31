# Changelog

All notable changes to the Prompt Royale Backend Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- [#3] Implemented Grounded Academic Q&A RAG Engine with document chunk retrieval, verified citations, Gemini API integration, and automatic Insufficient Evidence fallback (closes #3).
- [#3] Implemented 10-Question Solo Quiz Battle Engine (`/api/quiz/start`, `/api/quiz/submit`) with timed countdown, instant scoring, question reviews with citations, and daily battle limit tracking.
- [#1] Implemented Subject-Based Access Control (SBAC) evaluator gating cross-subject retrieval with HTTP 403 (closes #1).
- [#1] Implemented JWT authentication endpoints (`/api/auth/login`, `/api/auth/me`) with role-based session tokens for student, department user, and college admin.
- [#1] Implemented automatic startup SQLite database initialization and seeding for Vaigai College tenant, CSE department, subjects (CS101, CS202), and student Adhithiyan.
- [#1] Added comprehensive unit and integration test suite in `tests/test_auth.py` and `tests/test_sbac.py`.
