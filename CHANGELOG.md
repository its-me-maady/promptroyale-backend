# Changelog

All notable changes to the Prompt Royale Backend Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- [#13] Enriched academic curriculum seeding (`seed_academic_subjects`) across CSE, ECE, MECH, and IT departments with vetted lecture materials and retrieval chunks (Operating Systems, Computer Networks, AI & Machine Learning, Digital Electronics, Thermodynamics, Cloud Architectures) (closes #13).
- [#11] Implemented student BYOK multi-provider credential management endpoints (`GET`, `POST`, `DELETE /api/students/credentials`) supporting Gemini, OpenAI, Anthropic, DeepSeek, and OpenRouter with encryption at rest, masked key display, and revocation control (closes #11).
- [#9] Added dedicated staff management endpoints (`GET /api/admin/staff`, `POST /api/admin/staff`, `DELETE /api/admin/staff/{id}`) for College Administrators (closes #9).
- [#9] Supported multi-select staff member assignment in department creation (`POST /api/admin/departments`) and department editing (`PUT /api/admin/departments/{id}`).
- [#9] Implemented student deletion endpoint (`DELETE /api/students/{id}`) scoped for department faculty and administrators, cleaning up dependent usage counters, usage records, and subject memberships.
- [#9] Implemented general institutional user deletion endpoint (`DELETE /api/admin/users/{id}`) for College Administrators.
- [#7] Implemented Department Edit endpoint (`PUT /api/admin/departments/{id}`) allowing College Administrators to update department code and name (closes #7).
- [#7] Upgraded Department Provisioning endpoint (`POST /api/admin/departments`) to require faculty email and password, atomically creating both the Department and its primary `department_user` (Faculty) account.
- [#7] Added `lead_faculty_email` to `DepartmentOut` schema and department directory listings.
- [#5] Implemented dedicated College Administrator endpoints (`/api/admin/overview`, `/api/admin/departments`, `/api/admin/users`, `/api/admin/users/{id}/status`) for institutional KPIs, department provisioning, and account lifecycle management (closes #5).
- [#5] Implemented Department Student Management endpoints (`/api/students`) with search, creation, and Subject Membership enrollment/unenrollment audit lifecycle tracking.
- [#5] Enhanced Subject Management endpoints (`/api/subjects`) with creation, editing, and student enrollment roster management.
- [#5] Expanded database models in `app/models.py` covering all 14 SRS Section 3 entities (College, Department, Subject, Document, DocumentChunk, User, SubjectMembership, Conversation, ConversationMessage, Feedback, AIProviderCredential, UsageRecord, BillingSnapshot, BattleUsageCounter).
- [#5] Enforced strict environment-driven `DATABASE_URL` validation in `app/config.py` halting server execution if missing from `.env` or system environment, with documented SQLite and online PostgreSQL/Supabase configuration.
- [#3] Implemented Grounded Academic Q&A RAG Engine with document chunk retrieval, verified citations, Gemini API integration, and automatic Insufficient Evidence fallback (closes #3).
- [#3] Implemented 10-Question Solo Quiz Battle Engine (`/api/quiz/start`, `/api/quiz/submit`) with timed countdown, instant scoring, question reviews with citations, and daily battle limit tracking.
- [#1] Implemented Subject-Based Access Control (SBAC) evaluator gating cross-subject retrieval with HTTP 403 (closes #1).
- [#1] Implemented JWT authentication endpoints (`/api/auth/login`, `/api/auth/me`) with role-based session tokens for student, department user, and college admin.
- [#1] Implemented automatic startup SQLite database initialization and seeding for Vaigai College tenant, CSE department, subjects (CS101, CS202), and student Adhithiyan.
- [#1] Added comprehensive unit and integration test suite in `tests/test_auth.py` and `tests/test_sbac.py`.
