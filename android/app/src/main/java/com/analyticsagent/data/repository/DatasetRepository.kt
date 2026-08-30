package com.analyticsagent.data.repository

import com.analyticsagent.data.remote.BackendApi
import com.analyticsagent.data.remote.StorageUploader
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.domain.model.FileValidateResponse
import com.analyticsagent.domain.model.RegisterDatasetRequest
import com.analyticsagent.util.AppError
import com.analyticsagent.util.AppResult
import java.io.InputStream

/**
 * Upload + register + process a dataset. The flow is:
 *   validate → (client uploads directly to private storage) → register → process
 *
 * The storage path is server-constructed and returned by validate; the client
 * never invents it. Large files stream to storage (they are not loaded entirely
 * into Android memory).
 */
class DatasetRepository(
    private val api: BackendApi,
    private val uploader: StorageUploader,
) {
    suspend fun validate(
        projectId: String,
        fileName: String,
        fileSize: Long,
        mimeType: String,
    ): AppResult<FileValidateResponse> = api.validateFile(projectId, fileName, fileSize, mimeType)

    suspend fun upload(
        response: FileValidateResponse,
        openStream: () -> InputStream,
        onProgress: (Long, Long) -> Unit = { _, _ -> },
    ): AppResult<Unit> = uploader.upload(
        bucket = response.bucket,
        key = response.storagePath,
        mime = response.mimeType.ifBlank { "application/octet-stream" },
        totalBytes = response.fileSize,
        openStream = openStream,
        onProgress = onProgress,
    )

    suspend fun register(
        projectId: String,
        name: String,
        sourceType: String,
        storagePath: String?,
        fileSize: Long,
        mimeType: String?,
    ): AppResult<Dataset> {
        if (storagePath.isNullOrBlank()) {
            return AppResult.Error(AppError("UPLOAD", "File must be uploaded before registering."))
        }
        return api.registerDataset(
            RegisterDatasetRequest(
                projectId = projectId,
                name = name,
                sourceType = sourceType,
                storagePath = storagePath,
                fileSize = fileSize,
                mimeType = mimeType,
            ),
        )
    }

    suspend fun process(datasetId: String): AppResult<Unit> = api.processDataset(datasetId)

    suspend fun get(datasetId: String): AppResult<Dataset> = api.getDataset(datasetId)

    suspend fun list(projectId: String): AppResult<List<Dataset>> = api.listDatasets(projectId)
}