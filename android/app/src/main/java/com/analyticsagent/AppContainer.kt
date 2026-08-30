package com.analyticsagent

import android.content.Context
import com.analyticsagent.data.local.SessionStore
import com.analyticsagent.data.remote.BackendApi
import com.analyticsagent.data.remote.StorageUploader
import com.analyticsagent.data.remote.SupabaseAuth
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.data.repository.ArtifactRepository
import com.analyticsagent.data.repository.AuthRepository
import com.analyticsagent.data.repository.DatasetRepository
import com.analyticsagent.data.repository.ProjectRepository

/**
 * Manual dependency container (no DI framework, no KSP — keeps the build
 * robust while staying testable). All collaborators are constructed here.
 */
class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    val sessionStore = SessionStore(appContext)
    val supabaseAuth = SupabaseAuth()
    val backendApi = BackendApi(sessionStore)
    val storageUploader = StorageUploader(sessionStore)

    val authRepository = AuthRepository(sessionStore, supabaseAuth, backendApi)
    val projectRepository = ProjectRepository(backendApi)
    val datasetRepository = DatasetRepository(backendApi, storageUploader)
    val analysisRepository = AnalysisRepository(backendApi)
    val artifactRepository = ArtifactRepository(backendApi)
}