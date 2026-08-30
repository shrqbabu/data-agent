-- 0008_storage.sql
-- Private storage buckets + ownership-isolated policies.
-- Path convention: owner_id/project_id/<artifact>.ext

insert into storage.buckets (id, name, public, file_size_limit)
values
  ('project-inputs',     'project-inputs',     false, 104857600),  -- 100 MB
  ('project-artifacts',  'project-artifacts',  false, 209715200),  -- 200 MB
  ('dashboard-images',   'dashboard-images',   false, 209715200),
  ('reports',            'reports',            false, 104857600)
on conflict (id) do nothing;

-- Helper: bucket path must be owner-scoped: <uid>/<project>/...
create or replace function public.storage_path_is_owner_owned(bucket text, pname text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select bucket in ('project-inputs', 'project-artifacts', 'dashboard-images', 'reports')
     and (storage.foldername(pname))[1] = auth.uid()::text;
$$;

-- --- project-inputs (uploaded CSV / Excel) ---
drop policy if exists "project_inputs_owner_insert" on storage.objects;
create policy "project_inputs_owner_insert"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'project-inputs'
    and public.storage_path_is_owner_owned(bucket_id, name)
    and (storage.extension(name) in ('csv', 'xls', 'xlsx')));

drop policy if exists "project_inputs_owner_select" on storage.objects;
create policy "project_inputs_owner_select"
  on storage.objects for select to authenticated
  using (bucket_id = 'project-inputs'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "project_inputs_owner_delete" on storage.objects;
create policy "project_inputs_owner_delete"
  on storage.objects for delete to authenticated
  using (bucket_id = 'project-inputs'
    and public.storage_path_is_owner_owned(bucket_id, name));

-- --- project-artifacts (reports, DAX files, quality reports) ---
drop policy if exists "project_artifacts_owner_insert" on storage.objects;
create policy "project_artifacts_owner_insert"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'project-artifacts'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "project_artifacts_owner_select" on storage.objects;
create policy "project_artifacts_owner_select"
  on storage.objects for select to authenticated
  using (bucket_id = 'project-artifacts'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "project_artifacts_owner_delete" on storage.objects;
create policy "project_artifacts_owner_delete"
  on storage.objects for delete to authenticated
  using (bucket_id = 'project-artifacts'
    and public.storage_path_is_owner_owned(bucket_id, name));

-- --- dashboard-images ---
drop policy if exists "dashboard_images_owner_insert" on storage.objects;
create policy "dashboard_images_owner_insert"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'dashboard-images'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "dashboard_images_owner_select" on storage.objects;
create policy "dashboard_images_owner_select"
  on storage.objects for select to authenticated
  using (bucket_id = 'dashboard-images'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "dashboard_images_owner_delete" on storage.objects;
create policy "dashboard_images_owner_delete"
  on storage.objects for delete to authenticated
  using (bucket_id = 'dashboard-images'
    and public.storage_path_is_owner_owned(bucket_id, name));

-- --- reports ---
drop policy if exists "reports_owner_insert" on storage.objects;
create policy "reports_owner_insert"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'reports'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "reports_owner_select" on storage.objects;
create policy "reports_owner_select"
  on storage.objects for select to authenticated
  using (bucket_id = 'reports'
    and public.storage_path_is_owner_owned(bucket_id, name));

drop policy if exists "reports_owner_delete" on storage.objects;
create policy "reports_owner_delete"
  on storage.objects for delete to authenticated
  using (bucket_id = 'reports'
    and public.storage_path_is_owner_owned(bucket_id, name));

-- Downloads/previews go through signed URLs created by the backend (no public reads).
