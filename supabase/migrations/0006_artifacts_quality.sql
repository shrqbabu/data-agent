-- 0006_artifacts_quality.sql
-- Generated artifacts (report / PNG / DAX downloads) and data-quality results.

create table public.artifacts (
  id               uuid primary key default gen_random_uuid(),
  project_id       uuid not null references public.projects (id) on delete cascade,
  analysis_run_id  uuid references public.analysis_runs (id) on delete cascade,
  artifact_type    text not null
                     check (artifact_type in ('report', 'dashboard_png', 'dax_file', 'data_quality')),
  storage_path     text not null,          -- owner_id/project_id/...
  file_name        text not null,
  mime_type        text,
  file_size        bigint default 0,
  checksum         text,                   -- sha256, for integrity verification on download
  created_at       timestamptz not null default now()
);

create table public.data_quality (
  id              uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs (id) on delete cascade,
  score           numeric(5,2),            -- 0..100
  completeness    jsonb not null default '{}'::jsonb,
  validity        jsonb not null default '{}'::jsonb,
  consistency     jsonb not null default '{}'::jsonb,
  uniqueness      jsonb not null default '{}'::jsonb,
  relationships   jsonb not null default '{}'::jsonb,
  issues          jsonb not null default '[]'::jsonb,
  created_at      timestamptz not null default now()
);

alter table public.artifacts enable row level security;
alter table public.data_quality enable row level security;

grant all on public.artifacts to authenticated;
grant all on public.artifacts to service_role;
grant all on public.data_quality to authenticated;
grant all on public.data_quality to service_role;
