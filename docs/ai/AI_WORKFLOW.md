# AI Workflow Guardrails — TAB Energy Dashboard

This document defines behavioral expectations and guardrails for all AI agents working in this repository. Read this before making any code change.

---

## Core principle

> **Diagnose before you edit. Explain before you refactor. Minimize what you change.**

This codebase is a production dashboard used by Texas policymakers. Regressions affect real users. Speculation is not acceptable.

---

## Source of truth hierarchy

> **The repository is the primary source of truth.**

1. **Code and docs/ai/ files** — authoritative. Always verify claims against them.
2. **Chat history** — supplemental only. Use it to understand design intent or historical decisions that are not evident from the code. Never treat chat history as a substitute for reading the code.
3. **When they conflict** — do not resolve the conflict by assumption. Document it in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) with both the code-derived fact and the chat-stated claim, labeled with their respective evidence conventions (`*(verified: path)*` vs. `*(mentioned in chat context)*`). Ask for clarification before acting.

---

## Before making any change

### 1. Read the relevant `docs/ai/` files
- Check [`CURRENT_STATE.md`](CURRENT_STATE.md) for known debt and active signals.
- Check [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) for unresolved ambiguities.
- Check [`DECISIONS.md`](DECISIONS.md) to understand why the code is structured as it is.

### 2. Identify the minimal scope
Ask yourself:
- What is the smallest possible change that fully addresses the request?
- Which files are in scope? Which files must not be touched?
- Does this change affect any ETL script, parquet schema, or tab rendering?

### 3. Verify assumptions from code
- Never assume a function behaves a certain way — read it.
- Never assume a column exists in a parquet file — check `DATA_SOURCES.md` schemas.
- Never assume the README describes the current state — it is outdated (see `CURRENT_STATE.md`).

---

## Change discipline

### Minimize change scope
- Touch only the files required by the task.
- Do not "clean up" unrelated code in the same PR.
- Do not rename variables or functions unless directly required.
- Do not reformat code in files you are not otherwise modifying.

### Preserve architecture
- The tab-per-file architecture in `app/tabs/` must be maintained.
- Shared utilities belong in `app/utils/`, not inline in tab files.
- Schema contracts live in `app/utils/schema.py` — update them if you change ETL output columns.
- Do not introduce new global state beyond `st.session_state`.

### Preserve visual consistency
- All fuel-type colors must come from `app/utils/colors.py` (`FUEL_COLORS_HEX`).
- All tab layouts should follow the established pattern: header → KPI cards → chart/map → data table → footer.
- Do not introduce new CSS classes without a strong reason; reuse existing classes from `.streamlit/custom.css`.
- The TAB color palette (Navy `#1B365D`, Red `#C8102E`) must not be changed.

### Avoid speculative code
- Do not add features that were not requested.
- Do not add placeholder code, stub functions, or `# TODO: implement later` blocks.
- Do not add logging that was not requested.
- Do not add comments explaining what code does unless they are necessary for a complex algorithm.

### Policy language
- Advocacy messages in `app/utils/advocacy.py` reflect TAB's policy positions — do not modify their content without explicit instruction.
- Use neutral, factual language in any new UI text (data labels, tooltips, error messages).
- Do not introduce political or editorial commentary in non-advocacy code paths.

---

## ETL script rules

- ETL scripts must run independently from the repo root: `python etl/<script>.py`
- ETL scripts must not `import streamlit` at module level (they run in CI without Streamlit context).
- All ETL output must be written atomically (write to temp file, then rename) to prevent partial writes.
- Do not change a parquet schema (add/remove/rename columns) without also updating:
  1. `app/utils/schema.py` (`SCHEMAS` and/or `COLUMN_ALIASES`)
  2. The corresponding tab file (if the new/removed column is used in rendering)
  3. [`DATA_SOURCES.md`](DATA_SOURCES.md) (parquet schema table)
- Never remove an existing column without verifying no tab or utility references it.

---

## Streamlit rules

- Never call `st.stop()` — use `safe_render_tab()` pattern from `app/main.py` and graceful degradation in `load_parquet()`.
- All data loading must go through `load_parquet()` in `app/utils/loaders.py` — do not read parquet files directly in tabs.
- Do not add `@st.cache_data` or `@st.cache_resource` decorators outside of `app/utils/loaders.py` without documenting the reason.
- Do not use `st.experimental_*` APIs — they are deprecated in Streamlit 1.x.

---

## Dependency rules

- Do not add new dependencies unless absolutely necessary.
- If you must add a dependency, check the GitHub Advisory Database for vulnerabilities first.
- Do not change pinned core versions (`streamlit`, `pandas`, `pyarrow`, `numpy`) without understanding the parquet schema compatibility implications (see DR-002 in `DECISIONS.md`).

---

## Secret and credential rules

- Never commit secrets, API keys, or credentials to any file.
- Never hardcode an API key, even in a comment.
- Run secret scanning before every commit.
- `.streamlit/secrets.toml` must remain in `.gitignore`.

---

## Documentation update rule

When you make a structural change, update the relevant `docs/ai/` file **in the same PR**:

| Change type | Update |
|-------------|--------|
| New ETL script | `ARCHITECTURE.md`, `DATA_SOURCES.md`, `DATA_FLOW.md` |
| New tab | `ARCHITECTURE.md`, `DATA_FLOW.md` |
| Schema change | `DATA_SOURCES.md` (parquet schemas section) |
| New dependency | `PROJECT_CONTEXT.md` (tech stack) |
| New ETL data source | `DATA_SOURCES.md` |
| Architectural decision | `DECISIONS.md` (new DR entry) |
| Resolving a known issue | `CURRENT_STATE.md` (remove/update entry) |
| Answering an open question | `OPEN_QUESTIONS.md` → move answer to appropriate doc |
| Any structural change | `CHANGELOG_FOR_AI.md` (new entry) |

---

## Debugging workflow

### Tab not rendering / showing empty data
1. Check `data/<dataset>.parquet` exists and has rows.
2. Run `python scripts/validate_data.py`.
3. Check `app/utils/schema.py` — does the canonical schema match actual parquet columns?
4. Check `app/utils/schema.py` `COLUMN_ALIASES` — are all actual column names mapped?
5. Run the relevant ETL script directly: `python etl/<script>.py`.

### ETL failing in CI
1. Go to GitHub Actions → find the failed run.
2. Expand the failing ETL step log.
3. Check if `EIA_API_KEY` is present (diagnostic step in workflow).
4. If ERCOT HTML scrape fails, check if the URL/table format changed.
5. If CDR Excel parse fails, check if ERCOT updated the CDR file format.

### Streamlit crash on startup
1. Check `app/main.py` for syntax errors.
2. Run `streamlit run main.py` locally from `app/` directory.
3. Check if all `app/tabs/*.py` imports are resolvable.
4. Check if `app/utils/__init__.py` exports are consistent.

---

## What NOT to do

- ❌ Do not edit `app/main.py.backup`, `etl/ercot_lmp_etl.py.backup`, or any `.backup` file — they are artifacts, not active code.
- ❌ Do not enable the disabled legacy workflow `.github/workflows/etl-old.yml` without understanding why it was disabled.
- ❌ Do not delete backup files without first confirming the active file is correct.
- ❌ Do not change the `.streamlit_trigger` mechanism without understanding the Streamlit Cloud redeploy dependency.
- ❌ Do not modify `data/*.parquet` directly — always regenerate via ETL scripts.
