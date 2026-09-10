# Setup

> **Note**: For the complete, end-to-end guide covering the multi-stack engine (Excel, PowerBI, MySQL, Python, All) and executive PDF generation, please refer to [SETUP_README.md](../SETUP_README.md).

## 1. Supabase project
1. Create a project at https://supabase.com (or `supabase init` this repo).
2. Apply migrations (`supabase/migrations/*.sql`) — `supabase db push` or via the
   SQL editor in order.
3. Create the storage buckets (included in `0008_storage.sql`) — or via dashboard.
4. Provision the first admin:
   - Deploy Edge Functions (`supabase functions deploy invite-admin ...`) and
     call it with the service-role key, or
   - Run the SQL in `supabase/seed.sql` with your chosen admin email/password.

## 2. Analytics backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Env vars (see `backend/.env.example`):
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PUBLISHABLE_KEY`,
`SUPABASE_JWT_SECRET`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_ENABLED`,
`SQL_SECRETS_KEY` (Fernet key), `MAX_UPLOAD_MB`, `JOB_CONCURRENCY`.

## 3. Android app
```bash
cd android
# Provide config via gradle.properties (or CI secrets / local.properties):
#   ANALYTICS_AGENT_SUPABASE_URL=https://<ref>.supabase.co
#   ANALYTICS_AGENT_SUPABASE_KEY=<publishable anon key>
#   ANALYTICS_AGENT_API_URL=https://<backend-host>
./gradlew :app:assembleDebug
```
Only publishable values are used; the app reads them into `BuildConfig`.

## 4. Local backend tests
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```
Engine, DAX, dashboard, and validator tests run offline with `LLM_ENABLED=false`.
Integration tests (auth/RLS) are tagged `integration` and skipped without a live
Supabase instance.

## 5. CI
`.github/workflows/` runs:
- `android-build.yml` — assemble APK, unit tests, lint
- `backend-tests.yml` — lint + engine/DAX/dashboard/validator tests
- `supabase-ci.yml` — `supabase db reset` + `db lint` + Deno type-check of Edge
  Functions
