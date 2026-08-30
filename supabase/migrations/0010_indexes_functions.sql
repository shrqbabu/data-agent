-- 0010_indexes_functions.sql
-- Shared functions + query performance indexes.

-- updated_at maintenance for tables that have the column.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- --- Projects ---
create index if not exists projects_owner_id_idx on public.projects (owner_id);
create index if not exists projects_owner_updated_idx on public.projects (owner_id, updated_at desc);

-- --- Datasets ---
create index if not exists datasets_project_id_idx on public.datasets (project_id);
create index if not exists datasets_source_type_idx on public.datasets (project_id, source_type);

-- --- dataset_tables ---
create index if not exists dataset_tables_dataset_id_idx on public.dataset_tables (dataset_id);

-- --- analysis_runs ---
create index if not exists analysis_runs_project_id_idx on public.analysis_runs (project_id);
create index if not exists analysis_runs_project_created_idx
  on public.analysis_runs (project_id, created_at desc);
create index if not exists analysis_runs_owner_status_idx
  on public.analysis_runs (owner_id, status);

-- --- results ---
create index if not exists metrics_run_id_idx on public.metrics (analysis_run_id);
create index if not exists insights_run_id_idx on public.insights (analysis_run_id);
create index if not exists dax_measures_run_id_idx on public.dax_measures (analysis_run_id);
create index if not exists artifacts_project_id_idx on public.artifacts (project_id);
create index if not exists data_quality_run_id_idx on public.data_quality (analysis_run_id);
