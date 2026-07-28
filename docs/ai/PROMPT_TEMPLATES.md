# Prompt Templates — TAB Energy Dashboard

Reusable prompts for common AI-assisted tasks. Copy and customize as needed. Always read [`AI_WORKFLOW.md`](AI_WORKFLOW.md) before acting on any prompt response.

---

## 1. Repository orientation

```
I am starting a new session on the TAB Energy Dashboard repository (Charlie9170/TABEnergyDashboard).

Before I make any changes, please:
1. Read docs/ai/README.md to orient yourself.
2. Read docs/ai/PROJECT_CONTEXT.md for project identity and goals.
3. Read docs/ai/ARCHITECTURE.md for the entry point, tab structure, and utility modules.
4. Read docs/ai/CURRENT_STATE.md for active development signals and known issues.
5. Read docs/ai/OPEN_QUESTIONS.md for unresolved ambiguities.

Important: Treat the repository as the primary source of truth.
Use chat history only to explain design intent or historical decisions when they are not evident from the code.
If the repository and chat conflict, document the conflict in OPEN_QUESTIONS.md instead of resolving it by assumption.

Then summarize:
- What the project does
- How data flows from ETL to the dashboard
- What the current known issues are
- What I should be careful about when making changes

Do not make any code changes yet.
```

---

## 2. Bug diagnosis

```
There is a bug in the TAB Energy Dashboard. Here is what I observe:

[DESCRIBE SYMPTOM — e.g., "The Fuel Mix tab shows 'No data available' after a successful ETL run."]

Before proposing a fix:
1. Read docs/ai/DATA_FLOW.md to understand the full pipeline.
2. Read app/utils/loaders.py to understand how data is loaded and what errors look like.
3. Read app/utils/schema.py to check if the canonical schema matches the actual parquet column names.
4. Read the relevant ETL script (etl/eia_fuelmix_etl.py for fuel mix, etc.) to understand what it writes.
5. Inspect the relevant parquet file schema using the tables in docs/ai/DATA_SOURCES.md.

Diagnose the root cause, citing specific files and line numbers.
Do not propose a fix until you have identified the cause with evidence.
Do not speculate — if you cannot determine the cause, say so.
```

---

## 3. Implementation planning

```
I want to implement the following change in the TAB Energy Dashboard:

[DESCRIBE CHANGE — e.g., "Add a new tab that shows historical electricity prices by month."]

Before planning:
1. Read docs/ai/ARCHITECTURE.md to understand how existing tabs are structured.
2. Read docs/ai/DATA_SOURCES.md to understand what data is currently available.
3. Read docs/ai/DECISIONS.md to understand architectural constraints.
4. Read docs/ai/AI_WORKFLOW.md for change discipline rules.

Then produce:
- A minimal implementation plan with specific files to create or modify
- What new data (if any) is needed and which ETL script would produce it
- Any schema changes needed in app/utils/schema.py
- Risks and dependencies
- What docs/ai/ files need to be updated

Do not write any code yet. Wait for approval of the plan.
```

---

## 4. UI review

```
Review the visual design and user experience of [TAB NAME] tab in the TAB Energy Dashboard.

Files to examine:
- app/tabs/[tab]_tab.py
- app/utils/colors.py (fuel color palette)
- .streamlit/custom.css (base CSS)
- app/main.py (inline CSS and layout)

Evaluate:
1. Does the tab follow the established layout pattern (header → KPIs → chart/map → table → footer)?
2. Are all fuel-type colors sourced from app/utils/colors.py?
3. Are light/near-white fuel colors (SOLAR #E8EAED, HYDRO #F0F1F3) visible against the white background?
4. Is spacing consistent with other tabs?
5. Are error states (empty data, missing file) handled gracefully?

Report issues only — do not suggest stylistic improvements unrelated to the review criteria.
```

---

## 5. Architecture review

```
Review the overall architecture of the TAB Energy Dashboard for the following concern:

[DESCRIBE CONCERN — e.g., "We want to add real-time streaming updates without breaking the existing tab structure."]

Read:
- docs/ai/ARCHITECTURE.md
- docs/ai/DECISIONS.md
- docs/ai/DATA_FLOW.md

For each architectural decision that is relevant to this concern:
1. State the current implementation (with file citations).
2. Identify what would need to change.
3. Identify risks and constraints.
4. Recommend an approach that minimizes change scope.

Do not propose a full rewrite. Propose the smallest viable change.
```

---

## 6. Deployment debugging

```
The TAB Energy Dashboard is not showing updated data on Streamlit Cloud, even though GitHub Actions completed successfully.

Diagnose the issue by checking:
1. docs/ai/OPERATIONS.md — how does the Streamlit Cloud redeploy mechanism work?
2. docs/ai/DATA_FLOW.md — what is the caching behavior (st.cache_data TTL)?
3. .github/workflows/etl.yml — did the ETL actually commit and push data files?
4. .streamlit_trigger — was this file updated in the latest commit?

Possible causes to check:
- ETL ran but no parquet files changed (no commit made, no redeploy triggered)
- .streamlit_trigger was not updated
- st.cache_data TTL has not expired (up to 1 hour delay)
- GitHub Actions did not have write permissions
- EIA_API_KEY was missing, causing demo data fallback with no file diff

For each possible cause, tell me how to verify it.
```

---

## 7. ETL debugging

```
The [DATASET] ETL script (etl/[script].py) is failing or producing incorrect data.

Before investigating:
1. Read docs/ai/DATA_SOURCES.md to understand the expected data source and schema.
2. Read docs/ai/DATA_FLOW.md for the transformation steps.
3. Read the full ETL script (etl/[script].py).

Check:
- Is the external source (API/URL/file) reachable and returning the expected format?
- Are all required columns present in the output?
- Does the output schema match docs/ai/DATA_SOURCES.md?
- Does the output schema match app/utils/schema.py SCHEMAS for this dataset?
- Are there any COLUMN_ALIASES that bridge schema differences?

Report findings with file and line citations. Do not fix without diagnosing first.
```

---

## 8. Data validation

```
Validate the data quality of [DATASET] in the TAB Energy Dashboard.

Steps:
1. Read the expected schema from docs/ai/DATA_SOURCES.md.
2. Inspect the actual parquet file schema using the information in DATA_SOURCES.md.
3. Check for:
   - Missing required columns
   - Unexpected null rates (>10% nulls in non-nullable columns)
   - Out-of-range values (coordinates outside Texas bounds: lat 25.84–36.50, lon -106.65 to -93.51)
   - Duplicate rows
   - Stale last_updated timestamps (older than 24 hours for hourly/6h data)
   - Row count that seems implausible (e.g., 0 rows, or >10x expected)

Report findings as a structured table. Suggest which ETL step to investigate for each issue.
```

---

## 9. Performance optimization

```
The [TAB NAME] tab in the TAB Energy Dashboard is loading slowly.

Before investigating:
1. Read app/utils/loaders.py — is the data correctly cached with @st.cache_data?
2. Read the tab file (app/tabs/[tab]_tab.py) — are there any uncached operations in the render() function?
3. Check if pydeck maps are rendering large datasets (>10,000 points).
4. Check if Plotly charts are re-rendered on every user interaction.

Identify:
- What operations run on every Streamlit re-render?
- What operations are correctly cached?
- What is the likely performance bottleneck?

Propose only changes that directly address the identified bottleneck.
Do not refactor for style; minimize change scope.
```

---

## 10. Code review

```
Review the following code change in the TAB Energy Dashboard for correctness and adherence to project conventions:

[PASTE DIFF OR DESCRIBE CHANGE]

Check:
1. Does it follow the architecture described in docs/ai/ARCHITECTURE.md?
2. Does it use app/utils/loaders.py for data loading (not direct pd.read_parquet)?
3. Does it use app/utils/colors.py for fuel colors (not hardcoded hex values)?
4. Does it respect the canonical schema in app/utils/schema.py?
5. Does it handle the case of empty/missing data gracefully (no st.stop())?
6. Does it avoid introducing new dependencies?
7. Does it update docs/ai/ where required (schema changes, new data sources, etc.)?
8. Does it introduce any security risks (secrets in code, XSS via unsafe_allow_html)?

Report issues only; ignore style preferences.
```

---

## 11. Refactoring

```
I want to refactor [DESCRIBE TARGET — e.g., "the ETL scripts to share a common retry utility"].

Before planning:
1. Read docs/ai/ARCHITECTURE.md to understand current module boundaries.
2. Read docs/ai/DECISIONS.md (DR-007) for the rationale behind independent ETL scripts.
3. Read docs/ai/AI_WORKFLOW.md for change discipline rules.

Requirements for this refactoring:
- No change to external behavior (same parquet output schemas)
- No change to ETL script invocation (`python etl/<script>.py` must still work)
- No change to CI workflow unless strictly necessary
- Minimize the number of files touched

Produce a minimal refactoring plan. Do not write code yet.
```

---

## 12. Adding a new dashboard tab

```
I want to add a new dashboard tab to the TAB Energy Dashboard for [DESCRIBE TAB — e.g., "electricity demand forecasts"].

Before planning:
1. Read docs/ai/ARCHITECTURE.md — how are tabs structured?
2. Read docs/ai/DATA_FLOW.md — how do tabs load data?
3. Read an existing tab (e.g., app/tabs/fuelmix_tab.py) as a reference.
4. Read docs/ai/DATA_SOURCES.md — what data is available?

Produce a checklist of all required changes:
- New ETL script (if needed): etl/<name>_etl.py
- New data schema entry in app/utils/schema.py
- New parquet file in data/
- New tab file: app/tabs/<name>_tab.py with a render() function
- Update app/tabs/__init__.py (if applicable)
- Import and add tab to app/main.py st.tabs() list
- Add data source entry to app/utils/data_sources.py
- Add advocacy message to app/utils/advocacy.py
- Update .github/workflows/etl.yml to include new ETL script
- Update docs/ai/ARCHITECTURE.md, DATA_SOURCES.md, DATA_FLOW.md, CHANGELOG_FOR_AI.md

Do not write code until the plan is approved.
```
