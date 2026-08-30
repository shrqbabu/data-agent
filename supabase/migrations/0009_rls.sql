-- 0009_rls.sql
-- Explicit ownership policies. `admin A` can only access A's projects,
-- datasets, runs, metrics, insights, DAX, artifacts and quality results.

-- --- projects ---
drop policy if exists "projects_select_own" on public.projects;
create policy "projects_select_own" on public.projects
  for select to authenticated using (owner_id = auth.uid());

drop policy if exists "projects_insert_own" on public.projects;
create policy "projects_insert_own" on public.projects
  for insert to authenticated with check (owner_id = auth.uid());

drop policy if exists "projects_update_own" on public.projects;
create policy "projects_update_own" on public.projects
  for update to authenticated using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

drop policy if exists "projects_delete_own" on public.projects;
create policy "projects_delete_own" on public.projects
  for delete to authenticated using (owner_id = auth.uid());

-- --- datasets ---
drop policy if exists "datasets_select_own" on public.datasets;
create policy "datasets_select_own" on public.datasets
  for select to authenticated using (public.can_access_project(project_id));

drop policy if exists "datasets_insert_own" on public.datasets;
create policy "datasets_insert_own" on public.datasets
  for insert to authenticated with check (public.can_access_project(project_id));

drop policy if exists "datasets_update_own" on public.datasets;
create policy "datasets_update_own" on public.datasets
  for update to authenticated using (public.can_access_project(project_id))
  with check (public.can_access_project(project_id));

drop policy if exists "datasets_delete_own" on public.datasets;
create policy "datasets_delete_own" on public.datasets
  for delete to authenticated using (public.can_access_project(project_id));

-- --- dataset_tables ---
drop policy if exists "dataset_tables_select_own" on public.dataset_tables;
create policy "dataset_tables_select_own" on public.dataset_tables
  for select to authenticated using (public.can_access_dataset(dataset_id));

drop policy if exists "dataset_tables_insert_own" on public.dataset_tables;
create policy "dataset_tables_insert_own" on public.dataset_tables
  for insert to authenticated with check (public.can_access_dataset(dataset_id));

drop policy if exists "dataset_tables_update_own" on public.dataset_tables;
create policy "dataset_tables_update_own" on public.dataset_tables
  for update to authenticated using (public.can_access_dataset(dataset_id))
  with check (public.can_access_dataset(dataset_id));

drop policy if exists "dataset_tables_delete_own" on public.dataset_tables;
create policy "dataset_tables_delete_own" on public.dataset_tables
  for delete to authenticated using (public.can_access_dataset(dataset_id));

-- --- analysis_runs ---
drop policy if exists "analysis_runs_select_own" on public.analysis_runs;
create policy "analysis_runs_select_own" on public.analysis_runs
  for select to authenticated using (owner_id = auth.uid());

drop policy if exists "analysis_runs_insert_own" on public.analysis_runs;
create policy "analysis_runs_insert_own" on public.analysis_runs
  for insert to authenticated with check (owner_id = auth.uid());

drop policy if exists "analysis_runs_update_own" on public.analysis_runs;
create policy "analysis_runs_update_own" on public.analysis_runs
  for update to authenticated using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

drop policy if exists "analysis_runs_delete_own" on public.analysis_runs;
create policy "analysis_runs_delete_own" on public.analysis_runs
  for delete to authenticated using (owner_id = auth.uid());

-- --- metrics / insights / dax_measures (2-level join: run -> project) ---
drop policy if exists "metrics_select_own" on public.metrics;
create policy "metrics_select_own" on public.metrics
  for select to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "metrics_insert_own" on public.metrics;
create policy "metrics_insert_own" on public.metrics
  for insert to authenticated with check (public.can_access_run(analysis_run_id));

drop policy if exists "metrics_update_own" on public.metrics;
create policy "metrics_update_own" on public.metrics
  for update to authenticated using (public.can_access_run(analysis_run_id))
  with check (public.can_access_run(analysis_run_id));

drop policy if exists "metrics_delete_own" on public.metrics;
create policy "metrics_delete_own" on public.metrics
  for delete to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "insights_select_own" on public.insights;
create policy "insights_select_own" on public.insights
  for select to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "insights_insert_own" on public.insights;
create policy "insights_insert_own" on public.insights
  for insert to authenticated with check (public.can_access_run(analysis_run_id));

drop policy if exists "insights_delete_own" on public.insights;
create policy "insights_delete_own" on public.insights
  for delete to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "dax_measures_select_own" on public.dax_measures;
create policy "dax_measures_select_own" on public.dax_measures
  for select to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "dax_measures_insert_own" on public.dax_measures;
create policy "dax_measures_insert_own" on public.dax_measures
  for insert to authenticated with check (public.can_access_run(analysis_run_id));

drop policy if exists "dax_measures_update_own" on public.dax_measures;
create policy "dax_measures_update_own" on public.dax_measures
  for update to authenticated using (public.can_access_run(analysis_run_id))
  with check (public.can_access_run(analysis_run_id));

drop policy if exists "dax_measures_delete_own" on public.dax_measures;
create policy "dax_measures_delete_own" on public.dax_measures
  for delete to authenticated using (public.can_access_run(analysis_run_id));

-- --- artifacts (via project) ---
drop policy if exists "artifacts_select_own" on public.artifacts;
create policy "artifacts_select_own" on public.artifacts
  for select to authenticated using (public.can_access_project(project_id));

drop policy if exists "artifacts_insert_own" on public.artifacts;
create policy "artifacts_insert_own" on public.artifacts
  for insert to authenticated with check (public.can_access_project(project_id));

drop policy if exists "artifacts_delete_own" on public.artifacts;
create policy "artifacts_delete_own" on public.artifacts
  for delete to authenticated using (public.can_access_project(project_id));

-- --- data_quality (via run) ---
drop policy if exists "data_quality_select_own" on public.data_quality;
create policy "data_quality_select_own" on public.data_quality
  for select to authenticated using (public.can_access_run(analysis_run_id));

drop policy if exists "data_quality_insert_own" on public.data_quality;
create policy "data_quality_insert_own" on public.data_quality
  for insert to authenticated with check (public.can_access_run(analysis_run_id));

-- --- profiles ---
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select to authenticated using (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id and role = public.auth_role());
