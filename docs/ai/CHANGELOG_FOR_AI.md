# Changelog for AI — TAB Energy Dashboard

> This file records architecture-level changes to the TAB Energy Dashboard for the benefit of future AI agents. It supplements, not replaces, git history.
>
> **Format:** Each entry should include the date, a summary, changed files, and what docs need to be re-read.
>
> **Maintenance policy:** Add a new entry whenever a structural change is made (new tab, new ETL script, schema change, new data source, deployment change, major refactoring).

---

## 2026-07-28 — Initial AI documentation system created

**Type:** Documentation  
**Author:** Copilot (AI coding agent)

### Summary
Created `docs/ai/` directory with 12 documentation files covering project context, architecture, data sources, data flow, engineering decisions, operations, AI workflow guardrails, prompt templates, open questions, and this changelog.

Also created root-level `AGENTS.md` and `CLAUDE.md` instruction files.

### Files created
- `docs/ai/README.md` — Index and navigation guide
- `docs/ai/PROJECT_CONTEXT.md` — Project identity, stakeholders, tech stack
- `docs/ai/CURRENT_STATE.md` — Active development signals, backup files, TODOs, debt
- `docs/ai/ARCHITECTURE.md` — Entry point, module layout, Streamlit patterns, ETL reference
- `docs/ai/DATA_SOURCES.md` — External APIs, parquet schemas (verified from actual files), credentials
- `docs/ai/DATA_FLOW.md` — Verified end-to-end pipeline from API to rendered tab
- `docs/ai/DECISIONS.md` — 10 engineering decision records with rationale, tradeoffs, risks
- `docs/ai/OPERATIONS.md` — Local setup, CI/CD, deployment, monitoring
- `docs/ai/AI_WORKFLOW.md` — Guardrails and behavioral expectations for AI agents
- `docs/ai/PROMPT_TEMPLATES.md` — 12 reusable prompts for common tasks
- `docs/ai/OPEN_QUESTIONS.md` — 12 unresolved ambiguities (including one security concern)
- `docs/ai/CHANGELOG_FOR_AI.md` — This file
- `AGENTS.md` — Root-level instructions for AI agents
- `CLAUDE.md` — Root-level instructions for Claude

### Repository state at documentation time
- 5 datasets in production: fuelmix, price_map, generation, queue, minerals
- 5 ETL scripts in production + 2 stubs + 1 fallback
- GitHub Actions ETL runs every 6 hours
- Deployment: Streamlit Cloud (inferred)
- Parquet file shapes: fuelmix (1384, 4), generation (850, 7), price_map (15, 11), queue (281, 11), minerals_deposits (1, 13)

### What to re-read after this change
This is the initial creation — no existing docs/ai files exist to be stale.

---

## 2026-08-18 — ETL CI fix + measured generation validation

**Type:** ETL change | Bugfix | Deployment  
**Author:** Cursor agent (Charlie9170 repo)

### Summary
Fixed GitHub Actions ETL workflow git strategy so bot commits no longer fail on binary parquet conflicts. Plants ETL failures are now visible (removed `continue-on-error`). Added `scripts/validate_generation_parquet.py` to block committing legacy 70%-fabricated `generation.parquet`. EIA plants ETL now uses rolling date windows for capacity and facility-fuel; Generation tab subtitle shows the active period when present in parquet.

P0 generation integrity code (`72dacd8`) was already on `main`; this change unblocks CI from shipping fresh measured data. **Green CI run [32095361711](https://github.com/Charlie9170/TABEnergyDashboard/actions/runs/32095361711) (2026-08-18) committed measured `generation.parquet` (415 rows, no 70% fabrication).** Follow-up commit `3e4d0da` added month walk-back when EIA has not published the preferred rolling window.

### Files changed
- `.github/workflows/etl.yml` — concurrency, pull-before-ETL, push retry, plants ETL hard-fail, validation step
- `scripts/validate_generation_parquet.py` — new pre-commit validation for measured generation
- `etl/eia_plants_etl.py` — rolling capacity/generation API date windows; period columns on output
- `app/tabs/generation_tab.py` — dynamic generation period subtitle

### Schema changes (if any)
| Dataset | Column | Change |
|---------|--------|--------|
| generation | `generation_is_estimated` | Required by ETL (all `False`); absent in committed parquet until CI runs |
| generation | `generation_period_start`, `generation_period_end` | Added optional metadata columns from ETL |

### What to re-read
- `docs/ai/CURRENT_STATE.md` — audit task table, generation data gap
- `docs/ai/DATA_FLOW.md` — ETL → parquet → Generation tab
- `.github/workflows/etl.yml` — CI behavior

---

## Template for future entries

```markdown
## YYYY-MM-DD — Brief title of change

**Type:** [Feature | Bugfix | Refactoring | Schema change | ETL change | Deployment | Documentation]
**Author:** [GitHub username or "Copilot"]

### Summary
[1–3 sentences describing what changed and why]

### Files changed
- `path/to/file.py` — what changed
- `path/to/other.py` — what changed

### Schema changes (if any)
| Dataset | Column | Change |
|---------|--------|--------|
| fuelmix | new_col | Added: description |

### What to re-read
- `docs/ai/ARCHITECTURE.md` — [specific section]
- `docs/ai/DATA_SOURCES.md` — [parquet schema for X]
```
