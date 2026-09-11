# Project GitHub Repository Connection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let authorized project users independently connect and edit one GitHub repository per project.

**Architecture:** integrations owns persisted GitHub connection and audit rows; its service validates, authorizes, persists, and invalidates the adapter cache. The existing GitHub adapter resolves the per-project value before legacy environment fallback.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-10-project-github-repository-design.md`

## Global Constraints

- GitHub token remains environment-only; never return or log it.
- One GitHub repository per project; no automatic repository writes.
- Server authorization, optimistic versioning, audit, and forward-safe schema creation are required.

### Task 1: Persisted connection contract

**Files:** integrations infrastructure models/services/routes/tests.

- [ ] Write failing service and API tests for create, update, authorization, validation, version conflict, audit, and legacy fallback.
- [ ] Add integration-owned connection/audit rows and create-only schema registration.
- [ ] Add versioned GET/PUT API and validate repository availability via the existing GitHub adapter.
- [ ] Run focused backend tests.

### Task 2: Adapter resolution and UI

**Files:** GitHub adapter, integration service, GitHub project page, data actions, widget tests.

- [ ] Write failing adapter/UI tests for project override, cache invalidation, editable form, and error state.
- [ ] Resolve persisted repository before environment fallback; invalidate only that project cache after save.
- [ ] Add administrator/project-creator connection form and revalidate GitHub page after save.
- [ ] Run focused frontend tests, typecheck, lint, production build.

### Task 3: Documentation and release verification

- [ ] Record API, migration, permissions, audit, and rollback notes in the mail handoff/work package documents.
- [ ] Run backend integration tests and frontend relevant suite.
