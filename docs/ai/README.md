# AI Documentation Index — TAB Energy Dashboard

This directory is the **single source of truth** for AI agents and human contributors who need to understand the TAB Energy Dashboard repository without relying on long chat histories.

> **Scope note:** All documents in this directory are documentation only. They do not modify application behavior. Facts are cited with file paths; assumptions are labeled explicitly.

---

## Read this before you do anything else

> **The repository is the primary source of truth. Chat history is supplemental.**
>
> Read the files below before responding to any request. If something stated in chat conflicts with what you find in the code, do not resolve the conflict by assumption — document it in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) and ask for clarification.

---

## Quick-start for a new AI session

1. Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — who owns the project, what it does, and why it exists.
2. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) — entry point, module layout, rendering pipeline.
3. Read [`DATA_FLOW.md`](DATA_FLOW.md) — verified end-to-end pipeline from external API to dashboard tab.
4. Read [`CURRENT_STATE.md`](CURRENT_STATE.md) — active development signals, TODOs, backup files, technical debt.
5. Skim [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) — unresolved ambiguities that affect correctness.
6. Follow [`AI_WORKFLOW.md`](AI_WORKFLOW.md) before making any code change.

---

## Document Map

| File | Purpose |
|------|---------|
| [`README.md`](README.md) | This index |
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | Project identity, stakeholders, goals |
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | Active dev, TODOs, backup artifacts, debt |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Entry point, modules, Streamlit patterns |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | External APIs, update cadence, credentials |
| [`DATA_FLOW.md`](DATA_FLOW.md) | Verified ETL → Parquet → rendering pipeline |
| [`DECISIONS.md`](DECISIONS.md) | Engineering decision records with rationale |
| [`OPERATIONS.md`](OPERATIONS.md) | Local setup, CI/CD, deployment |
| [`AI_WORKFLOW.md`](AI_WORKFLOW.md) | Guardrails for future AI agents |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | Unresolved ambiguities |
| [`CHANGELOG_FOR_AI.md`](CHANGELOG_FOR_AI.md) | Architecture-level change log for AI context |

---

## Evidence conventions used in this documentation

| Label | Meaning |
|-------|---------|
| *(verified: `path/to/file`)* | Fact confirmed directly from the cited file |
| *(mentioned in chat context)* | Stated in the originating chat conversation; not independently verified from code |
| *(inferred)* | Logical inference from verified facts; stated explicitly as inference |
| *(assumption)* | Reasonable assumption; should be verified before acting |
| *(unknown)* | Not determinable from available information |

---

## Maintenance policy

- When any architecture, data source, schema, or deployment pattern changes, the relevant `docs/ai/` file **must** be updated in the same PR.
- When a question in `OPEN_QUESTIONS.md` is resolved, move the answer to the appropriate file and remove it from `OPEN_QUESTIONS.md`.
- Append a new entry to `CHANGELOG_FOR_AI.md` for every structural change.
