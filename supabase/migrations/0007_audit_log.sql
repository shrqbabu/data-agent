-- 0007_audit_log.sql
-- Append-only audit trail. Client-facing roles get NO access (service-role only).

create table public.audit_log (
  id         uuid primary key default gen_random_uuid(),
  admin_id   uuid references auth.users (id) on delete set null,
  action     text not null,
  project_id uuid references public.projects (id) on delete set null,
  metadata   jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

comment on table public.audit_log is
  'PROJECT_CREATED, FILE_UPLOADED, ANALYSIS_STARTED, ANALYSIS_COMPLETED, '
  'ANALYSIS_FAILED, DAX_GENERATED, DASHBOARD_GENERATED, ARTIFACT_DOWNLOADED, '
  'PROJECT_DELETED, ... — never store secrets or raw PII here.';

create index audit_log_created_at_idx on public.audit_log (created_at desc);
create index audit_log_admin_id_idx on public.audit_log (admin_id);

-- A convenience append function for the backend (service role).
create or replace function public.append_audit(p_admin uuid, p_action text, p_project uuid, p_metadata jsonb default '{}'::jsonb)
returns void
language sql
security definer
set search_path = public
as $$
  insert into public.audit_log (admin_id, action, project_id, metadata)
  values (p_admin, p_action, p_project, p_metadata);
$$;

alter table public.audit_log enable row level security;
-- Intentionally NO grants to anon/authenticated: the audit log is read only by
-- the backend using the service role.
grant all on public.audit_log to service_role;
