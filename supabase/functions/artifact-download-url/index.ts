// artifact-download-url — returns a signed URL for a stored artifact after
// verifying the requestor owns the project the artifact belongs to.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.48.1';
import { assertAdmin, EdgeError, errorResponse } from '../_shared/auth.ts';
import { corsHeaders, handleCors } from '../_shared/cors.ts';

interface SignedUrlRequest {
  artifact_id: string;
  expires_in_seconds?: number; // default 300 (5 min)
}

Deno.serve(async (req) => {
  const cors = handleCors(req);
  if (cors) return cors;

  try {
    const { user } = await assertAdmin(req);
    const body: SignedUrlRequest = await req.json();

    if (!body.artifact_id) {
      throw new EdgeError('artifact_id is required');
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
      { auth: { persistSession: false } },
    );

    // Fetch artifact + verify ownership via project.
    const { data: artifact, error: artError } = await supabase
      .from('artifacts')
      .select('*')
      .eq('id', body.artifact_id)
      .single();

    if (artError || !artifact) {
      throw new EdgeError('Artifact not found', 404);
    }

    const { data: project, error: projError } = await supabase
      .from('projects')
      .select('owner_id')
      .eq('id', artifact.project_id)
      .single();

    if (projError || project?.owner_id !== user.id) {
      throw new EdgeError('Forbidden: you do not own this project', 403);
    }

    // Determine which bucket contains the artifact.
    const bucketMap: Record<string, string> = {
      report: 'reports',
      dashboard_png: 'dashboard-images',
      dax_file: 'project-artifacts',
      data_quality: 'project-artifacts',
    };

    const bucket = bucketMap[artifact.artifact_type] ?? 'project-artifacts';
    const expiresIn = Math.min(body.expires_in_seconds ?? 300, 3600);

    const { data: signedUrl, error: urlError } = await supabase.storage
      .from(bucket)
      .createSignedUrl(artifact.storage_path, expiresIn);

    if (urlError || !signedUrl) {
      throw new EdgeError('Failed to generate signed URL', 500);
    }

    return new Response(
      JSON.stringify({
        signed_url: signedUrl.signedUrl,
        expires_in_seconds: expiresIn,
        file_name: artifact.file_name,
        mime_type: artifact.mime_type,
        file_size: artifact.file_size,
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