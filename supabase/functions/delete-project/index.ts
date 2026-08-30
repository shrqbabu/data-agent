// delete-project — full cascade delete of a project, its storage objects, and all
// associated rows. Uses the service-role key so it can delete across buckets.
// The caller must be the project owner.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';
import { assertAdmin, EdgeError, errorResponse } from '../_shared/auth.ts';
import { corsHeaders, handleCors } from '../_shared/cors.ts';

interface DeleteRequest {
  project_id: string;
}

const BUCKETS = ['project-inputs', 'project-artifacts', 'dashboard-images', 'reports'];

Deno.serve(async (req) => {
  const cors = handleCors(req);
  if (cors) return cors;

  try {
    const { user } = await assertAdmin(req);
    const body: DeleteRequest = await req.json();

    if (!body.project_id) {
      throw new EdgeError('project_id is required');
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
      { auth: { persistSession: false } },
    );

    // Verify ownership.
    const { data: project, error: projError } = await supabase
      .from('projects')
      .select('id, owner_id')
      .eq('id', body.project_id)
      .single();

    if (projError || !project) {
      throw new EdgeError('Project not found', 404);
    }
    if (project.owner_id !== user.id) {
      throw new EdgeError('Forbidden: you do not own this project', 403);
    }

    // Delete storage objects across all buckets (prefix = owner_id/project_id/).
    const prefix = `${user.id}/${body.project_id}/`;
    for (const bucket of BUCKETS) {
      const { data: objects } = await supabase.storage
        .from(bucket)
        .list(prefix, { limit: 1000 });

      if (objects && objects.length > 0) {
        const paths = objects.map((o) => `${prefix}${o.name}`);
        await supabase.storage.from(bucket).remove(paths);
      }
    }

    // Delete rows — FK cascade handles the rest (datasets, runs, metrics, etc.).
    // artifacts and audit_log entries are handled by FK ON DELETE CASCADE or SET NULL.
    const { error: delError } = await supabase
      .from('projects')
      .delete()
      .eq('id', body.project_id);

    if (delError) {
      throw new EdgeError(`Failed to delete project: ${delError.message}`, 500);
    }

    // Append audit entry.
    await supabase.rpc('append_audit', {
      p_admin: user.id,
      p_action: 'PROJECT_DELETED',
      p_project: body.project_id,
      p_metadata: JSON.stringify({ deleted_by: 'edge-function' }),
    });

    return new Response(
      JSON.stringify({ ok: true, project_id: body.project_id }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (err) {
    return errorResponse(err);
  }
});