package com.analyticsagent.data.remote

import com.analyticsagent.data.local.AppConfig
import com.analyticsagent.data.local.SessionStore
import com.analyticsagent.domain.model.Artifact
import com.analyticsagent.domain.model.CreateProjectRequest
import com.analyticsagent.domain.model.CreateRunRequest
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.domain.model.FileValidateResponse
import com.analyticsagent.domain.model.MeResponse
import com.analyticsagent.domain.model.Project
import com.analyticsagent.domain.model.RegisterDatasetRequest
import com.analyticsagent.domain.model.Run
import com.analyticsagent.domain.model.RunDetail
import com.analyticsagent.domain.model.SignedUrlResponse
import com.analyticsagent.util.AppError
import com.analyticsagent.util.AppResult
import io.ktor.client.HttpClient
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.flow.first
import kotlinx.serialization.KSerializer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject

/**
 * Typed client for the analytics backend. All analytics requests authenticate
 * with the admin's Supabase JWT (Bearer). On 401 the caller clears the session.
 *
 * This class only ever holds publishable config and the user's own token —
 * never server secrets.
 */
class BackendApi(
    private val sessionStore: SessionStore,
) {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val client = HttpClient(Android) {
        install(ContentNegotiation) { json(this@BackendApi.json) }
        install(HttpTimeout) {
            requestTimeoutMillis = 60_000
            connectTimeoutMillis = 15_000
            socketTimeoutMillis = 60_000
        }
    }

    private suspend fun bearer(): String? =
        sessionStore.session.first().accessToken.takeIf { it.isNotBlank() }

    private fun url(path: String): String = AppConfig.analyticsApiUrl + path

    // ------- Typed endpoints -------

    suspend fun me(): AppResult<MeResponse> =
        getJson(url("/api/v1/auth/me")).asData(MeResponse.serializer())

    suspend fun listProjects(): AppResult<List<Project>> =
        getJson(url("/api/v1/projects")).asList(Project.serializer())

    suspend fun createProject(name: String, description: String): AppResult<Project> =
        postJson(url("/api/v1/projects"), CreateProjectRequest(name, description))
            .asData(Project.serializer())

    suspend fun deleteProject(id: String): AppResult<Unit> =
        when (val r = executeJson { client.delete(url("/api/v1/projects/$id")) { auth() } }) {
            is AppResult.Success -> AppResult.Success(Unit)
            is AppResult.Error -> AppResult.Error(r.error)
        }

    suspend fun getProject(id: String): AppResult<Project> =
        getJson(url("/api/v1/projects/$id")).asData(Project.serializer())

    suspend fun getDataset(id: String): AppResult<Dataset> =
        getJson(url("/api/v1/datasets/$id")).asData(Dataset.serializer())

    suspend fun listDatasets(projectId: String): AppResult<List<Dataset>> =
        getJson(url("/api/v1/datasets?project_id=$projectId")).asList(Dataset.serializer())

    suspend fun registerDataset(req: RegisterDatasetRequest): AppResult<Dataset> =
        postJson(url("/api/v1/datasets"), req).asData(Dataset.serializer())

    suspend fun processDataset(id: String): AppResult<Unit> =
        postJson(url("/api/v1/datasets/$id/process"), emptyMap<String, String>()).unit()

    suspend fun validateFile(
        projectId: String, fileName: String, fileSize: Long, mimeType: String,
    ): AppResult<FileValidateResponse> = postJson(
        url("/api/v1/files/validate"),
        mapOf(
            "project_id" to projectId,
            "file_name" to fileName,
            "file_size" to fileSize,
            "mime_type" to mimeType,
        ),
    ).asData(FileValidateResponse.serializer())

    suspend fun createRun(projectId: String, datasetId: String?, prompt: String): AppResult<Run> =
        postJson(url("/api/v1/runs"), CreateRunRequest(projectId, datasetId, prompt))
            .asData(Run.serializer())

    suspend fun getRun(id: String): AppResult<Run> =
        getJson(url("/api/v1/runs/$id")).asData(Run.serializer())

    suspend fun getRunDetail(id: String): AppResult<RunDetail> =
        getJson(url("/api/v1/runs/$id/detail")).asData(RunDetail.serializer())

    suspend fun listRuns(projectId: String): AppResult<List<Run>> =
        getJson(url("/api/v1/projects/$projectId/runs")).asList(Run.serializer())

    suspend fun listArtifacts(projectId: String): AppResult<List<Artifact>> =
        getJson(url("/api/v1/projects/$projectId/artifacts")).asList(Artifact.serializer())

    suspend fun artifactDownloadUrl(artifactId: String): AppResult<SignedUrlResponse> =
        postJson(url("/api/v1/artifacts/$artifactId/download-url"), mapOf<String, String>())
            .asData(SignedUrlResponse.serializer())

    // ---------- Transport ----------

    private suspend fun getJson(path: String): Response =
        Response(executeJson { client.get(path) { auth() } })

    private suspend fun postJson(path: String, body: Any): Response =
        Response(executeJson {
            client.post(path) {
                auth()
                contentType(ContentType.Application.Json)
                setBody(body)
            }
        })

    private suspend fun executeJson(block: suspend () -> HttpResponse): AppResult<JsonElement> {
        if (bearer() == null) {
            return AppResult.Error(AppError("AUTH", "Not signed in."))
        }
        return try {
            val resp = block()
            val text = resp.bodyAsText()
            if (!resp.status.isSuccess()) {
                AppResult.Error(errorFromStatus(resp.status.value, text))
            } else if (text.isBlank()) {
                AppResult.Success(JsonNull)
            } else {
                AppResult.Success(
                    runCatching { json.parseToJsonElement(text) }
                        .getOrElse { JsonPrimitive(text) },
                )
            }
        } catch (e: Exception) {
            AppResult.Error(AppError.from(e))
        }
    }

    private suspend fun HttpRequestBuilder.auth() {
        val token = bearer() ?: return
        bearerAuth(token)
    }

    private fun errorFromStatus(status: Int, text: String): AppError {
        val detail = runCatching {
            json.parseToJsonElement(text).jsonObject["detail"]
                ?.let { if (it is JsonPrimitive) it.content else it.toString() }
        }.getOrNull()
        val message = detail ?: "Request failed (HTTP $status)."
        val code = when (status) {
            401 -> "AUTH_EXPIRED"
            403 -> "FORBIDDEN"
            404 -> "NOT_FOUND"
            else -> "HTTP_$status"
        }
        return AppError(
            code = code,
            message = message,
            userMessage = if (status == 401) {
                "Your session has expired. Please sign in again."
            } else message,
        )
    }

    /** Thin holder that turns a transport result into typed data. */
    private inner class Response(private val result: AppResult<JsonElement>) {
        fun <T> asData(serializer: KSerializer<T>): AppResult<T> = when (result) {
            is AppResult.Success -> runCatching {
                AppResult.Success(json.decodeFromJsonElement(serializer, result.data))
            }.getOrElse { AppResult.Error(AppError.from(it)) }
            is AppResult.Error -> AppResult.Error(result.error)
        }

        fun <T> asList(serializer: KSerializer<T>): AppResult<List<T>> = when (result) {
            is AppResult.Success -> runCatching {
                val arr = result.data as? JsonArray
                    ?: throw IllegalArgumentException("Expected a JSON array")
                AppResult.Success(arr.map { json.decodeFromJsonElement(serializer, it) })
            }.getOrElse { AppResult.Error(AppError.from(it)) }
            is AppResult.Error -> AppResult.Error(result.error)
        }

        fun unit(): AppResult<Unit> = when (result) {
            is AppResult.Success -> AppResult.Success(Unit)
            is AppResult.Error -> AppResult.Error(result.error)
        }
    }
}