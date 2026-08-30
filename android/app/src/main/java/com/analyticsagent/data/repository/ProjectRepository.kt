package com.analyticsagent.data.repository

import com.analyticsagent.data.remote.BackendApi
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.domain.model.Project
import com.analyticsagent.util.AppResult

class ProjectRepository(private val api: BackendApi) {
    suspend fun list(): AppResult<List<Project>> = api.listProjects()
    suspend fun get(id: String): AppResult<Project> = api.getProject(id)
    suspend fun create(name: String, description: String): AppResult<Project> =
        api.createProject(name, description)
    suspend fun delete(id: String): AppResult<Unit> = api.deleteProject(id)
}