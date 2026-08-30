-- 0001_extensions.sql
-- Core extensions used by the analytics product.

create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists "pg_trgm";    -- fuzzy search on project names (optional)

-- A helper that returns the current caller's role (admin/member), using
-- security definer so that RLS policy checks can consult it without recursion.
create or replace function public.auth_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role from public.profiles where id = auth.uid()
$$;

-- Only ever used inside RLS: answers "is this project owned by the caller?".
create or replace function public.can_access_project(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.projects p
    where p.id = p_id
      and p.owner_id = auth.uid()
  );
$$;

-- Only ever used inside RLS: "is this dataset owned by the caller?".
create or replace function public.can_access_dataset(d_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.datasets d
    join public.projects p on p.id = d.project_id
    where d.id = d_id
      and p.owner_id = auth.uid()
  );
$$;

-- Only ever used inside RLS: "is this analysis run owned by the caller?".
create or replace function public.can_access_run(r_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.analysis_runs r
    where r.id = r_id
      and r.owner_id = auth.uid()
  );
$$;
