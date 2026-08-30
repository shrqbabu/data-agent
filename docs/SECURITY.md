# Security model

## Threat model
- Attacker: an authenticated (or unauthenticated) actor who is **not the project
  owner**. The client is treated as untrusted: everything it sends (`role`,
  `project_id`, `storage_path`, file metadata) is re-validated server-side.

## Authentication
- **Single admin login.** Email + password. No signup, no public registration,
  no social, no guest.
- Authorization uses a **server-controlled `profiles.role`** record, not editable
  user metadata. `profiles.role` cannot be updated by the user (RLS + trigger).
- Admin provisioning is done only through the `invite-admin` Edge Function or a
  service-role script (never from the app).

## Row Level Security
- RLS is enabled on every table. Policies implement **owner isolation**:
  `admin A` can only see A's projects, datasets, runs, metrics, insights, DAX,
  artifacts, and data-quality results. See `supabase/migrations/0009_rls.sql`.

## Storage
- Buckets `project-inputs`, `project-artifacts`, `dashboard-images`, `reports`
  are **private**.
- Object paths are `owner_id/project_id/...`; storage policies only allow access
  when `(storage.foldername(name))[1] = auth.uid()::text`.
- Downloads and previews use **signed URLs**; objects are never world-readable.

## Backend authorization
- Every request requires a valid Supabase JWT (`Authorization: Bearer`).
- The backend resolves the JWT to a user, loads `profiles.role`, and **requires
  `role = admin`**.
- For every resource ID in the request, the backend re-checks `owner_id`
  ownership through PostgREST before touching data (including via the
  service-role client). Client-supplied `project_id`/`storage_path` are never
  trusted.

## SQL connectors (read-only)
- The Android app never connects to company databases. It registers a connector
  through the backend; secrets are encrypted at rest (Fernet, key in env).
- The backend enforces **read-only**: a statement-level guard rejects
  `DROP DELETE UPDATE INSERT TRUNCATE ALTER CREATE` (and their comment/whitespace
  obfuscations), opens connections with `default_transaction_read_only=on` and a
  read-only role, and runs introspection queries only. No destructive SQL is ever
  executed.

## Secrets
- Android contains only `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` +
  `ANALYTICS_API_URL` (all injectable via `BuildConfig` / Gradle properties).
- Service-role key, JWT secret, AI keys, and SQL credentials exist only in the
  backend environment / Supabase.

## Audit
- `audit_log` records `PROJECT_CREATED, FILE_UPLOADED, ANALYSIS_STARTED,
  ANALYSIS_COMPLETED, ANALYSIS_FAILED, DAX_GENERATED, DASHBOARD_GENERATED,
  ARTIFACT_DOWNLOADED, PROJECT_DELETED`, etc., with admin ID + timestamp.
- Never log secrets or raw PII. `audit_log` has no client-facing RLS policies
  (service-role only).

## Input validation
- Files: extension, MIME sniff, size (configurable limit), encoding, delimiter,
  header, malformed rows are all validated before and during processing.
- Upload authorization is checked before accepting a file; `storage_path` is
  server-constructed as `owner_id/project_id/<uuid>.<ext>`.
