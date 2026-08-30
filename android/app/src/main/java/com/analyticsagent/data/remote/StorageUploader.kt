package com.analyticsagent.data.remote

import com.analyticsagent.data.local.AppConfig
import com.analyticsagent.data.local.SessionStore
import com.analyticsagent.util.AppError
import com.analyticsagent.util.AppResult
import java.io.InputStream
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okio.BufferedSink

/**
 * Uploads a file directly to private Supabase Storage with real progress
 * reporting. Streams the source in chunks so we never load huge files fully
 * into Android memory.
 */
class StorageUploader(
    private val sessionStore: SessionStore,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    /**
     * @param openStream factory for a fresh InputStream (allows retries).
     * @param totalBytes known size used for progress (and Content-Length).
     */
    suspend fun upload(
        bucket: String,
        key: String,
        mime: String,
        totalBytes: Long,
        openStream: () -> InputStream,
        onProgress: (sentBytes: Long, totalBytes: Long) -> Unit = { _, _ -> },
    ): AppResult<Unit> {
        val token = sessionStore.session.first().accessToken
        if (token.isBlank()) return AppResult.Error(AppError("AUTH", "Not signed in."))

        return withContext(Dispatchers.IO) {
            try {
                val body = object : RequestBody() {
                    override fun contentType() = mimeType.let { it.toMediaType() }

                    override fun contentLength(): Long = totalBytes

                    override fun writeTo(sink: BufferedSink) {
                        openStream().use { ins ->
                            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                            var sent = 0L
                            while (true) {
                                val read = ins.read(buffer)
                                if (read == -1) break
                                sink.write(buffer, 0, read)
                                sent += read
                                onProgress(sent, totalBytes)
                            }
                        }
                    }
                }

                val request = Request.Builder()
                    .url("${AppConfig.supabaseUrl}/storage/v1/object/$bucket/$key")
                    .addHeader("Authorization", "Bearer $token")
                    .addHeader("apikey", AppConfig.supabasePublishableKey)
                    .post(body)
                    .build()

                val response = client.newCall(request).execute()
                response.use { resp ->
                    if (resp.isSuccessful) {
                        AppResult.Success(Unit)
                    } else {
                        AppResult.Error(
                            AppError("UPLOAD_${resp.code}", "Upload failed (HTTP ${resp.code})."),
                        )
                    }
                }
            } catch (e: Exception) {
                AppResult.Error(AppError.from(e))
            }
        }
    }
}