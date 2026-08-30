package com.analyticsagent

import android.app.Application

class AnalyticsApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}

/** Convenience accessor for the app container. */
fun Application.container(): AppContainer =
    (this as? AnalyticsApplication)?.container ?: error("Application is not AnalyticsApplication")