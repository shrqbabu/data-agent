package com.analyticsagent.data.local

import com.analyticsagent.BuildConfig

/**
 * Publishable-only configuration injected via Gradle properties / CI secrets.
 * Secrets never appear here. The service-role key, JWT secret and AI keys live
 * only on the backend.
 */
object AppConfig {
    val supabaseUrl: String = BuildConfig.SUPABASE_URL
    val supabasePublishableKey: String = BuildConfig.SUPABASE_PUBLISHABLE_KEY
    val analyticsApiUrl: String = BuildConfig.ANALYTICS_API_URL

    fun isConfigured(): Boolean =
        supabaseUrl.isNotBlank() && supabasePublishableKey.isNotBlank() && analyticsApiUrl.isNotBlank()
}