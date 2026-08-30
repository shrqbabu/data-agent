-- 0002_profiles.sql
-- Server-controlled authorization record. role is NOT user-editable.

create table public.profiles (
  id         uuid primary key references auth.users (id) on delete cascade,
  email      text not null,
  role       text not null default 'member' check (role in ('admin', 'member')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.profiles is
  'Server-controlled admin authorization. Never derive authorization from editable user metadata.';

-- Keep updated_at fresh.
drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Automatically create a profile row when a user is provisioned server-side.
-- The provisioning flow (invite-admin Edge Function) passes role via raw_user_meta_data.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, role)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'role', 'member')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Belt-and-suspenders: a user can never change their own role, even via a
-- compromised client path. Only a security-definer path (service role / Edge
-- Function) can promote an account.
create or replace function public.prevent_role_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if old.role is distinct from new.role then
    raise exception 'role is server-controlled and cannot be changed';
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_prevent_role_change on public.profiles;
create trigger profiles_prevent_role_change
  before update on public.profiles
  for each row execute function public.prevent_role_change();

-- Emails stay unique per user by construction (auth.users.email is unique).
grant select on public.profiles to authenticated;
grant select on public.profiles to service_role;
grant update (email) on public.profiles to authenticated;
