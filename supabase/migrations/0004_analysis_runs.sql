-- 0004_analysis_runs.sql
-- Every execution creates an immutable run. Runs are never overwritten.

create table public.analysis_runs (
  id           uuid primary key default gen_random_uuid(),
  project_id   uuid not null references public.projects (id) on delete cascade,
  owner_id     uuid not null references auth.users (id) on delete cascade,
  status       text not null default 'queued'
                 check (status in ('queued', 'running', 'completed', 'failed', 'cancelled', 'validation_failed')),
  stage        text not null default 'queued',
  progress     integer not null default 0 check (progress between 0 and 100),
  user_prompt  text not null,
  started_at   timestamptz,
  completed_at timestamptz,
  error        jsonb,                 -- { code, message, details? }
  created_at   timestamptz not null default now()
);

comment on column public.analysis_runs.owner_id is
  'Denormalized from projects for RLS + backend ownership checks without joins.';

alter table public.analysis_runs enable row level security;

grant all on public.analysis_runs to authenticated;
grant all on public.analysis_runs to service_role;
