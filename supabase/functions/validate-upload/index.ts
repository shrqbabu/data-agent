// validate-upload — validates file metadata AND ownership before the client uploads.
// Android calls this first, then uses the returned path to upload to Supabase Storage.
// This prevents unauthorized uploads and ensures the path is server-constructed.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';
import { assertAdmin, EdgeError, errorResponse } from '../_shared/auth.ts';
import { corsHeaders, handleCors } from '../_shared/cors.ts';

const ALLOWED_EXTENSIONS = ['csv', 'xls', 'xlsx'];
const MAX_SIZE_MB = 100;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface ValidateRequest {
  project_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
}

Deno.serve(async (req) => {
  const cors = handleCors(req);
  if (cors) return cors;

  try {
    const { user } = await assertAdmin(req);
    const body: ValidateRequest = await req.json();

    if (!body.project_id || !body.file_name || body.file_size == null) {
      throw new EdgeError('project_id, file_name, and file_size are required');
    }

    // Verify project ownership server-side.
    const supabase = createAdminClient();
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

    // Validate file metadata.
    const ext = body.file_name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      throw new EdgeError(
        `Unsupported file extension ".${ext}". Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
      );
    }
    if (body.file_size > MAX_SIZE_BYTES) {
      throw new EdgeError(
        `File exceeds ${MAX_SIZE_MB} MB limit (${(body.file_size / 1048576).toFixed(1)} MB)`,
      );
    }

    // Server-construct the storage path. NEVER trust client-provided paths.
    const uuid = crypto.randomUUID();
    const storagePath = `${user.id}/${body.project_id}/${uuid}.${ext}`;

    return new Response(
      JSON.stringify({
        ok: true,
        storage_path: storagePath,
        bucket: 'project-inputs',
        file_name: body.file_name,
        file_size: body.file_size,
        mime_type: body.mime_type,
        max_size_bytes: MAX_SIZE_BYTES,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (err) {
    return errorResponse(err);
  }
});

// Helper — re-exported so the backend can also use it.
function createAdminClient() {
  return createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    { auth: { persistSession: false } },
  );
}