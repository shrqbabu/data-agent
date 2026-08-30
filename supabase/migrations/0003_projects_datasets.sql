-- 0003_projects_datasets.sql
-- Projects + datasets + dataset tables (the project-management metadata layer).

create table public.projects (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references auth.users (id) on delete cascade,
  name        text not null check (char_length(name) between 1 and 200),
  description text not null default '',
  status      text not null default 'active'
                check (status in ('active', 'archived')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  last_run_at timestamptz
);

create table public.datasets (
  id           uuid primary key default gen_random_uuid(),
  project_id   uuid not null references public.projects (id) on delete cascade,
  name         text not null,
  source_type  text not null check (source_type in ('csv', 'excel', 'sql')),
  storage_path text,                 -- owner_id/project_id/<uuid>.<ext> for file sources
  file_size    bigint default 0,
  mime_type    text,
  row_count    bigint default 0,
  column_count integer default 0,
  schema       jsonb not null default '[]'::jsonb,
  profile      jsonb not null default '{}'::jsonb,  -- profiling summary from the engine
  created_at   timestamptz not null default now()
);

create table public.dataset_tables (
  id         uuid primary key default gen_random_uuid(),
  dataset_id uuid not null references public.datasets (id) on delete cascade,
  table_name text not null,
  grain      text,                    -- e.g. 'order_line', 'transaction', 'customer'
  row_count  bigint default 0,
  schema     jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

drop trigger if exists set_projects_updated_at on public.projects;
create trigger set_projects_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();

-- RLS (policies live in 0009_rls.sql; enable + grants here).
alter table public.projects enable row level security;
alter table public.datasets enable row level security;
alter table public.dataset_tables enable row level security;

grant all on public.projects to authenticated;
grant all on public.projects to service_role;
grant all on public.datasets to authenticated;
grant all on public.datasets to service_role;
grant all on public.dataset_tables to authenticated;
grant all on public.dataset_tables to service_role;
