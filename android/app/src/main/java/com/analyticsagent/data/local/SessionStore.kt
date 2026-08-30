package com.analyticsagent.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "session")

/**
 * Local session cache (user id/email/token). Used only to restore UI state
 * between launch; authorization is always re-validated server-side.
 */
class SessionStore(context: Context) {
    private val store = context.dataStore

    private object Keys {
        val userId = stringPreferencesKey("user_id")
        val email = stringPreferencesKey("email")
        val role = stringPreferencesKey("role")
        val accessToken = stringPreferencesKey("access_token")
    }

    data class Session(
        val userId: String = "",
        val email: String = "",
        val role: String = "",
        val accessToken: String = "",
    ) {
        val isLoggedIn: Boolean get() = userId.isNotBlank() && accessToken.isNotBlank()
    }

    val session: Flow<Session> = store.data.map { p ->
        Session(
            userId = p[Keys.userId] ?: "",
            email = p[Keys.email] ?: "",
            role = p[Keys.role] ?: "",
            accessToken = p[Keys.accessToken] ?: "",
        )
    }

    suspend fun save(session: Session) {
        store.edit { p ->
            p[Keys.userId] = session.userId
            p[Keys.email] = session.email
            p[Keys.role] = session.role
            p[Keys.accessToken] = session.accessToken
        }
    }

    suspend fun clear() {
        store.edit { it.clear() }
    }
}