# M17 — Dashboard — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M17 — Dashboard
IDENTIFIER: M17

PURPOSE:
  Provide the visual ECLAIR product for monitoring and verification.

RESPONSIBILITY:
  - Consume the REST API and present reliability information visually.
  - Views: Overview metrics, Verification workspace, Claim-level results, Evidence inspection,
    Calibration charts, Evaluation metrics, Audit trail.

NON-RESPONSIBILITY:
  - MUST NOT place reliability logic inside the UI (Spec §4.12). It consumes the API only.

LOCATION:
  dashboard/
EXISTING FOLDERS USED:
  dashboard/  (app.py, api_client.py, components/, pages/)
  pages: overview.py, verify.py, claims.py, evidence.py, evaluation.py, calibration.py, audit.py
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M15 REST API (via dashboard/api_client.py).
  External: Streamlit, Plotly or Matplotlib.
  Configuration: API base URL via configuration.

INPUTS:
  Source: user interactions + responses from the M15 REST API.
  Format: API responses (M15 schemas).
  Validation: display-time validation only; no reliability computation.

PROCESSING:
  New logic: presentation only — call the API and render results in components/pages.

OUTPUTS:
  Format: rendered Streamlit views.
  Destination: end users.

CONSUMERS:
  Module/service: end users (human).
  Expected contract: N/A (leaf consumer).

INTEGRATION POINTS:
  APIs used: M15 REST endpoints. APIs exposed: none.
  Database: none (only via API). Events/Queues: none.
  Configuration: API base URL. Auth: only if M15 requires it.

ERROR HANDLING: surface API errors to the user; do not invent local fallbacks or logic.
VALIDATION RULES: none beyond input formatting for API calls.
INTEGRATION REQUIREMENTS: all data comes from the API; UI stays thin.

DO NOT CHANGE: M15 API contract; server modules; any other folder.
REUSE RULES: reuse api_client + Streamlit; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only the seven views listed.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: visual presentation over the API.
  Does NOT handle: any reliability computation.

VERIFICATION BEFORE COMPLETE:
  - Dashboard renders ECS, claims, evidence, decisions, evaluation, calibration and audit
    entirely from API data.
  - Sample screenshots/flows provided as applicable.
```
