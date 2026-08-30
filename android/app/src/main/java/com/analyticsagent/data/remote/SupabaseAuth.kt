package com.analyticsagent.data.remote

import com.analyticsagent.data.local.AppConfig
import com.analyticsagent.util.AppError
import com.analyticsagent.util.AppResult
import io.ktor.client.HttpClient
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/**
 * Minimal Supabase Auth client (email/password only). Only the publishable key
 * is used; the returned access token is stored locally so the backend can
 * validate it and enforce the admin role server-side.
 */
class SupabaseAuth {
    private val json = Json { ignoreUnknownKeys = true }

    private val client = HttpClient(Android) {
        install(HttpTimeout) {
            connectTimeoutMillis = 15_000
            requestTimeoutMillis = 30_000
        }
    }

    data class AuthSession(
        val accessToken: String,
        val refreshToken: String,
        val userId: String,
        val email: String,
        val expiresAt: Long? = null,
    )

    suspend fun signIn(email: String, password: String): AppResult<AuthSession> {
        val body = json.encodeToString(
            JsonObject.serializer(),
            JsonObject(
                mapOf(
                    "email" to JsonPrimitive(email),
                    "password" to JsonPrimitive(password),
                ),
            ),
        )
        return try {
            val resp = client.post("${AppConfig.supabaseUrl}/auth/v1/token?grant_type=password") {
                header("apikey", AppConfig.supabasePublishableKey)
                contentType(ContentType.Application.Json)
                setBody(body)
            }
            val text = resp.bodyAsText()
            if (!resp.status.isSuccess()) {
                AppResult.Error(
                    AppError(
                        code = if (resp.status.value == 400) "INVALID_CREDENTIALS" else "AUTH_${resp.status.value}",
                        message = "Sign in failed (HTTP ${resp.status.value}).",
                        userMessage = "Invalid email or password.",
                    ),
                )
            } else {
                val root = json.parseToJsonElement(text).jsonObject
                val session = root["session"]?.jsonObject ?: root
                val access = session["access_token"]?.jsonPrimitive?.content ?: ""
                val refresh = session["refresh_token"]?.jsonPrimitive?.content ?: ""
                val expiresIn = session["expires_in"]?.jsonPrimitive?.content?.toLongOrNull()
                if (access.isBlank()) {
                    AppResult.Error(AppError("AUTH", "Sign-in returned no token."))
                } else {
                    val userMeta = root["user"]?.jsonObject ?: session
                    val uid = userMeta["id"]?.jsonPrimitive?.content ?: ""
                    val emailVal = userMeta["email"]?.jsonPrimitive?.content ?: email
                    val expiresAt = expiresIn?.let { System.currentTimeMillis() / 1000 + it }
                    AppResult.Success(AuthSession(access, refresh, uid, emailVal, expiresAt))
                }
            }
        } catch (e: Exception) {
            AppResult.Error(AppError.from(e))
        }
    }

    suspend fun checkSession(token: String): Boolean {
        return try {
            val resp = client.get("${AppConfig.supabaseUrl}/auth/v1/user") {
                header("Authorization", "Bearer $token")
                header("apikey", AppConfig.supabasePublishableKey)
            }
            resp.status.isSuccess()
        } catch (e: Exception) {
            false
        }
    }

    }