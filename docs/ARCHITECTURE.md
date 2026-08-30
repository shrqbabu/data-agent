# Architecture

This is an **admin-only enterprise analytics workspace** — a specialized data-analysis
product, **not a chatbot**. The product's single pipeline:

```
CSV / Excel / SQL  →  Data Analysis  →  User-Defined Report  →  Insights  →  DAX  →  Dashboard PNG
```

## High-level layers

```
┌─────────────────────────────────────────────────────────────┐
│  Android client (Kotlin / Jetpack Compose / Material 3)     │
│  UI → ViewModel → Repository → API/Supabase                 │
│  * only publishable Supabase key + backend URL live here    │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
   REST /api/v1 (JWT)               Supabase (PostgREST + Storage,
                │                   Auth, Realtime) — publishable key
┌───────────────▼──────────────┐   ┌───────────▼───────────────┐
│  Analytics backend (FastAPI) │   │  Supabase                │
│  - auth (JWT → admin role)   │   │  - projects/metadata      │
│  - file validation/processing│   │  - private storage        │
│  - SQL read-only connectors  │   │  - RLS ownership          │
│  - job queue + pipeline      │   │  - audit log              │
│  - deterministic engine      │   │  - Edge Functions         │
│  - metric registry           │   │                            │
│  - validator                 │   │                            │
│  - DAX generator + validator │   │                            │
│  - dashboard PNG renderer    │   │                            │
│  - LLM (evidence-bound only) │   │                            │
└──────────────────────────────┘   └────────────────────────────┘
```

**Ownership rule enforced in three independent layers:** Android never decides
authorization; Supabase RLS enforces it on every row and storage object; the
backend re-validates every JWT-derived owner against every `project_id`,
`dataset_id`, `run_id`, and `storage_path` it touches (service-role access is only
used after an ownership check).

## Secrets boundary

| Secret | Android | Backend | Supabase |
| --- | --- | --- | --- |
| `SUPABASE_URL` | ✅ (publishable) | ✅ | — |
| `SUPABASE_PUBLISHABLE_KEY` | ✅ | ✅ | — |
| `SUPABASE_SERVICE_ROLE_KEY` | ❌ | ✅ | — |
| `SUPABASE_JWT_SECRET` | ❌ | ✅ | — |
| `OPENAI_API_KEY` | ❌ | ✅ | — |
| `SQL_CONNECTION_SECRETS` (encryption key) | ❌ | ✅ | — |
| Database passwords | ❌ | ✅ (encrypted at rest) | — |

Nothing in `BuildConfig`, `strings.xml`, source, git, or the APK contains a secret.

## Determinism & single source of truth

- All arithmetic (totals, growth, % , rankings, distributions, correlations,
  forecasts, aggregations) is computed by pandas/NumPy/SciPy/statsmodels/sklearn
  — **never** by an LLM.
- Every numeric fact lives in the **metric registry** (`metric_id`, definition,
  formula, source, grain, filters, period, value, validation_status).
- The registry is the *single source* that feeds the **report**, the **DAX
  measures**, and the **dashboard PNG**. If a number is not in the registry, it
  cannot appear in a report or on a PNG.
- A dedicated **validator** stage independently checks data, metrics, insights,
  DAX, and PNG. Critical failure → `VALIDATION_FAILED`; nothing is delivered as
  validated.

## No-hallucination policy

The backend's LLM is allowed to *explain evidence* and *draft prose* only. It is
instructed (and structurally limited) to never invent data, metrics, columns,
benchmarks, competitors, or causation. Every insight must cite metric IDs from
the registry. Metrics the dataset cannot support are returned as `NOT_SUPPORTED`
with an explanation and an alternative when one exists.

## Analysis pipeline (one immutable run)

```
VALIDATING_INPUT → PROFILING → DATA_QUALITY → SCHEMA_MODELING → ANALYSIS_PLANNING
→ DETERMINISTIC_CALCULATIONS → BUSINESS_ANALYSIS → STATISTICS
→ FORECASTING_IF_SUPPORTED → INSIGHT_GENERATION → DAX_GENERATION → DAX_VALIDATION
→ DASHBOARD_PNG_GENERATION → FINAL_VALIDATION → COMPLETED
```

Stages stream status/progress to `analysis_runs` (the Android client polls; a
Realtime subscription is optional).

## Repo layout

```
analytics-agent/
├── android/    Android client (Kotlin, Compose, supabase-kt, Ktor)
├── supabase/   migrations (SQL + RLS + storage) and Edge Functions (Deno)
├── backend/    FastAPI analytics backend (Python) — the analytics engine
└── docs/       ARCHITECTURE.md, SECURITY.md, SETUP.md
```
