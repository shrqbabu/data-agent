-- seed.sql
-- Provision the first admin. Run ONCE in the Supabase SQL editor (or via the
-- invite-admin Edge Function, which does the same with a service-role call).
--
-- NOTE: Use the Supabase dashboard "Authentication → Users → Invite user" and set
-- raw_user_meta_data {"role":"admin"}, OR run the block below with a real password.

-- select extensions.uuid_generate_v4();  -- no-op guard; this file is a template

-- CREATE USER via admin API (auth.users is managed by Supabase Auth — prefer the
-- dashboard invite or the invite-admin Edge Function over raw SQL inserts).
--
-- Example (replace email + password):
--   call auth.admin_create_user or use dashboard; then ensure:
--   update public.profiles set role = 'admin' where email = 'admin@company.com';
--   (service-role / dashboard only — the client can never change role.)

-- Sanity checks after setup:
--   1. select email, role from public.profiles;
--   2. select * from storage.buckets where public = false;
--   3. verify RLS: try reading another admin's project with your client key → 0 rows.
