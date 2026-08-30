-- 0011_sql_connectors.sql
-- SQL connector registry. Connection secrets are stored ENCRYPTED (Fernet token
-- produced by the backend). The Android app never holds or sees these.

create table public.sql_connectors (
  id             uuid primary key default gen_random_uuid(),
  owner_id       uuid not null references auth.users (id) on delete cascade,
  name           text not null,
  engine         text not null default 'postgres',
  host           text not null,
  database       text not null,
  secrets_token  text not null,       -- Fernet-encrypted JSON, backend-only
  status         text not null default 'ready',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

drop trigger if exists set_sql_connectors_updated_at on public.sql_connectors;
create trigger set_sql_connectors_updated_at
  before update on public.sql_connectors
  for each row execute function public.set_updated_at();

alter table public.sql_connectors enable row level security;

-- Owner-scoped access only.
drop policy if exists "sql_connectors_select_own" on public.sql_connectors;
create policy "sql_connectors_select_own" on public.sql_connectors
  for select to authenticated using (owner_id = auth.uid());

drop policy if exists "sql_connectors_insert_own" on public.sql_connectors;
create policy "sql_connectors_insert_own" on public.sql_connectors
  for insert to authenticated with check (owner_id = auth.uid());

drop policy if exists "sql_connectors_delete_own" on public.sql_connectors;
create policy "sql_connectors_delete_own" on public.sql_connectors
  for delete to authenticated using (owner_id = auth.uid());

grant all on public.sql_connectors to authenticated;
grant all on public.sql_connectors to service_role;

create index if not exists sql_connectors_owner_id_idx on public.sql_connectors (owner_id);
