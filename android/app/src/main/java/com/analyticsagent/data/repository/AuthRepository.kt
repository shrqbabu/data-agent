package com.analyticsagent.data.repository

import com.analyticsagent.data.local.SessionStore
import com.analyticsagent.data.remote.BackendApi
import com.analyticsagent.data.remote.SupabaseAuth
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.Flow

/** Single-page admin login. Orchestrates the Supabase auth token and session cache. */
class AuthRepository(
    private val sessionStore: SessionStore,
    private val supabaseAuth: SupabaseAuth,
    private val backendApi: BackendApi,
) {
    val session: Flow<SessionStore.Session> = sessionStore.session

    suspend fun signIn(email: String, password: String): AppResult<SessionStore.Session> {
        return when (val r = supabaseAuth.signIn(email.trim(), password)) {
            is AppResult.Error -> AppResult.Error(r.error)
            is AppResult.Success -> {
                val session = SessionStore.Session(
                    userId = r.data.userId,
                    email = r.data.email,
                    role = "admin", // nominal; the backend re-validates on every call
                    accessToken = r.data.accessToken,
                )
                sessionStore.save(session)
                // Verify admin access via backend (server-controlled).
                when (val me = backendApi.me()) {
                    is AppResult.Success -> AppResult.Success(session)
                    is AppResult.Error -> {
                        // If the backend rejects, sign out locally to avoid a false session.
                        sessionStore.clear()
                        AppResult.Error(me.error)
                    }
                }
            }
        }
    }

    suspend fun signOut() {
        sessionStore.clear()
    }

    suspend fun isValidSession(token: String): Boolean = supabaseAuth.checkSession(token)
}