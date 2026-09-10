# Analytics Agent

**An admin-only enterprise data analytics workspace for Android.**

This is a specialized analytics product — **not a chatbot**. Its single purpose:

```
CSV / Excel / SQL → Data Analysis → User-Defined Report → Insights → DAX → Dashboard PNG
```

The administrator signs in, creates a project, uploads a CSV/Excel file (or
connects read-only SQL), inspects and quality-checks the dataset, writes a
report prompt, and generates: a validated analytical report, Power BI-ready DAX
measures, and a premium dashboard **PNG** — all saved as an immutable project
with full history.

Explicitly **out of scope**: creating PBIX/PBIT, interactive Power BI dashboards,
publishing to Power BI, general chat, and public user registration.

---

## Repo layout

| Path | What it is |
| --- | --- |
| `android/` | Kotlin / Jetpack Compose / Material 3 client (UI → ViewModel → Repository → API/Supabase) |
| `supabase/` | Postgres migrations (schema + RLS + storage policies) and Edge Functions |
| `backend/` | FastAPI analytics backend — deterministic engine, metric registry, validator, DAX + dashboard PNG generation, job worker |
| `docs/` | [ARCHITECTURE](docs/ARCHITECTURE.md), [SECURITY](docs/SECURITY.md), [SETUP](docs/SETUP.md) |
| `.github/workflows/` | CI: Android APK build + tests, backend lint/tests, Supabase migration check |

## Key properties

- **One login page** — email/password, admin only. No signup, social, or guest.
- **Server-controlled authorization** — `profiles.role = 'admin'`, enforced by
  RLS, storage policies, and the backend on every request. Role is not
  user-editable.
- **Deterministic analytics** — totals, growth, % , rankings, correlations,
  forecasts are pandas/NumPy/SciPy/statsmodels. The LLM only writes prose from
  evidence and never invents data, metrics, or columns.
- **Single source of truth** — the metric registry feeds report, DAX, and PNG.
  $2.48M in the report == $2.48M on the PNG == the DAX value.
- **Independent validator** — data, metrics, insights, DAX, and PNG are checked;
  critical failure → `VALIDATION_FAILED`, never delivered as validated.
- **No secrets in Android** — only publishable values live in the APK. Service
  key, JWT secret, AI keys, and SQL credentials stay server-side.
- **Read-only SQL** — the app never connects to company databases directly; the
  backend enforces SELECT-only via a statement guard + read-only transactions.

## Quick start

See the comprehensive [SETUP_README.md](SETUP_README.md) for full end-to-end setup and architecture, or [docs/SETUP.md](docs/SETUP.md):

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000

# Backend tests (offline)
pip install -r requirements-dev.txt && python -m pytest

# Android
cd android && ./gradlew :app:assembleDebug
```

Supabase: apply `supabase/migrations/*.sql`, deploy the Edge Functions, and
provision the first admin with the `invite-admin` function.

## License

Private / internal use.
