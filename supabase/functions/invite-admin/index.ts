// invite-admin — provisions a new admin user via the Supabase Admin Auth API.
// CALLER: provisioning script / Supabase dashboard (not the Android app).
// Requires Authorization header with SUPABASE_SERVICE_ROLE_KEY.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';
import { corsHeaders, handleCors } from '../_shared/cors.ts';

interface InviteRequest {
  email: string;
  password: string;
}

Deno.serve(async (req) => {
  const cors = handleCors(req);
  if (cors) return cors;

  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
    }

    // Authorization: service-role key required.
    const token = authHeader.slice(7);
    if (token !== Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')) {
      return new Response(JSON.stringify({ error: 'Forbidden' }), { status: 403 });
    }

    const body: InviteRequest = await req.json();
    if (!body.email || !body.password) {
      return new Response(
        JSON.stringify({ error: 'email and password are required' }),
        { status: 400 },
      );
    }

    if (body.password.length < 8) {
      return new Response(
        JSON.stringify({ error: 'Password must be at least 8 characters' }),
        { status: 400 },
      );
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
      { auth: { persistSession: false } },
    );

    // Create user via admin API — sets role='admin' in raw_user_meta_data.
    // The handle_new_user trigger copies role into public.profiles.
    const { data: user, error: createError } = await supabase.auth.admin.createUser({
      email: body.email,
      password: body.password,
      email_confirm: true,
      user_metadata: { role: 'admin' },
    });

    if (createError) {
      return new Response(
        JSON.stringify({ error: createError.message }),
        { status: 400 },
      );
    }

    // Ensure profile is set to admin (trigger should have done this, but be safe).
    const { error: profileError } = await supabase
      .from('profiles')
      .update({ role: 'admin' })
      .eq('id', user.user.id);

    if (profileError) {
      console.error('Failed to update profile role:', profileError);
    }

    return new Response(
      JSON.stringify({ ok: true, user_id: user.user.id, email: body.email }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  } catch (err) {
    console.error(err);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500 },
    );
  }
});