-- 0005_results.sql
-- Metrics, insights, DAX measures — all bound to an immutable analysis run.

create table public.metrics (
  id                uuid primary key default gen_random_uuid(),
  analysis_run_id   uuid not null references public.analysis_runs (id) on delete cascade,
  metric_id         text not null,          -- canonical registry id, e.g. 'm_total_revenue'
  name              text not null,
  definition        text not null,
  formula           text not null,
  value             jsonb not null,         -- { value, unit, ... } from the deterministic engine
  source            jsonb not null default '{}'::jsonb,  -- { table, column, grain, filters, period }
  validation_status text not null default 'pending'
                      check (validation_status in ('validated', 'unvalidated', 'NOT_SUPPORTED', 'failed')),
  created_at        timestamptz not null default now(),
  unique (analysis_run_id, metric_id)
);

create table public.insights (
  id              uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs (id) on delete cascade,
  title           text not null,
  finding         text not null,
  evidence        jsonb not null default '[]'::jsonb,  -- metric ids + values that back the finding
  interpretation  text,
  business_impact text,
  recommendation  text,
  confidence      text check (confidence in ('high', 'medium', 'low')),
  priority        text check (priority in ('high', 'medium', 'low')),
  created_at      timestamptz not null default now()
);

create table public.dax_measures (
  id                uuid primary key default gen_random_uuid(),
  analysis_run_id   uuid not null references public.analysis_runs (id) on delete cascade,
  name              text not null,
  dax_code          text not null,
  purpose           text,
  dependencies      jsonb not null default '[]'::jsonb,  -- names of other measures this one depends on
  validation_status text not null default 'unvalidated'
                      check (validation_status in ('validated', 'unvalidated', 'failed')),
  created_at        timestamptz not null default now()
);

alter table public.metrics enable row level security;
alter table public.insights enable row level security;
alter table public.dax_measures enable row level security;

grant all on public.metrics to authenticated;
grant all on public.metrics to service_role;
grant all on public.insights to authenticated;
grant all on public.insights to service_role;
grant all on public.dax_measures to authenticated;
grant all on public.dax_measures to service_role;
