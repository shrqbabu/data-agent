package com.analyticsagent.data.repository

import com.analyticsagent.data.remote.BackendApi
import com.analyticsagent.domain.model.Artifact
import com.analyticsagent.domain.model.DaxMeasure
import com.analyticsagent.domain.model.Run
import com.analyticsagent.domain.model.RunDetail
import com.analyticsagent.domain.model.SignedUrlResponse
import com.analyticsagent.util.AppResult

class AnalysisRepository(private val api: BackendApi) {
    suspend fun createRun(projectId: String, datasetId: String?, prompt: String): AppResult<Run> =
        api.createRun(projectId, datasetId, prompt)

    suspend fun getRun(id: String): AppResult<Run> = api.getRun(id)

    suspend fun getRunDetail(id: String): AppResult<RunDetail> = api.getRunDetail(id)

    suspend fun listRuns(projectId: String): AppResult<List<Run>> = api.listRuns(projectId)
}

class ArtifactRepository(private val api: BackendApi) {
    suspend fun list(projectId: String): AppResult<List<Artifact>> = api.listArtifacts(projectId)

    suspend fun downloadUrl(artifactId: String): AppResult<SignedUrlResponse> =
        api.artifactDownloadUrl(artifactId)
}

fun RunDetail.daxToText(): String =
    daxMeasures.joinToString("\n\n\n") { "// ${it.name}\n${it.daxCode}" }