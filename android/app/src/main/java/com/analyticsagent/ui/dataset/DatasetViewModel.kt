package com.analyticsagent.ui.dataset

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.DatasetRepository
import com.analyticsagent.data.repository.ProjectRepository
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.domain.model.FileValidateResponse
import com.analyticsagent.domain.model.Project
import com.analyticsagent.util.AppResult
import com.analyticsagent.util.JsonFormat
import java.io.InputStream
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class UploadPhase { Idle, Validating, Uploading, Processing, Done, Error }

object DatasetInfo {
    fun qualityScore(d: Dataset): Double? {
        val q = JsonFormat.obj(d.profile, "quality") ?: return null
        return JsonFormat.number(q, "score")
    }
    fun dateRange(d: Dataset): String {
        val dr = JsonFormat.asText(d.profile?.let { JsonFormat.obj(it, "date_range") ?: it })
        return dr.replace("\"", "").ifBlank { "—" }
    }
    fun fileLabel(d: Dataset): String = d.name.ifBlank { "${d.sourceLabel} dataset" }
    fun dateColumns(d: Dataset): List<String> =
        (d.profile?.let { JsonFormat.textOf(it, "date_columns") } ?: "").split(",").map { it.trim() }
            .filter { it.isNotBlank() }
}

data class UploadState(
    val phase: UploadPhase = UploadPhase.Idle,
    val progress: Float = 0f,
    val fileName: String? = null,
    val error: String? = null,
)

data class DatasetUiState(
    val loading: Boolean = true,
    val project: Project? = null,
    val datasets: List<Dataset> = emptyList(),
    val error: String? = null,
    val upload: UploadState = UploadState(),
)

class DatasetViewModel(
    private val projects: ProjectRepository,
    private val datasetsRepo: DatasetRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DatasetUiState())
    val state = _state.asStateFlow()

    private var projectId: String = ""

    fun load(pid: String) {
        projectId = pid
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            val projectRes = projects.get(pid)
            val datasetsRes = datasetsRepo.list(pid)
            val project = (projectRes as? AppResult.Success)?.data
            val datasets = (datasetsRes as? AppResult.Success)?.data ?: emptyList()
            val error = when {
                projectRes is AppResult.Error -> projectRes.error.userMessage
                datasetsRes is AppResult.Error -> datasetsRes.error.userMessage
                else -> null
            }
            _state.value = DatasetUiState(loading = false, project = project, datasets = datasets, error = error)
        }
    }

    fun retry() = load(projectId)

    /** Full upload pipeline: validate → stream upload → register → process. */
    fun uploadFile(
        fileName: String,
        fileSize: Long,
        mimeType: String,
        openStream: () -> InputStream,
        onComplete: (Dataset) -> Unit,
    ) {
        val pid = projectId
        if (pid.isBlank()) return
        _state.value = _state.value.copy(
            upload = UploadState(phase = UploadPhase.Validating, fileName = fileName),
        )
        viewModelScope.launch {
            when (val v = datasetsRepo.validate(pid, fileName, fileSize, mimeType)) {
                is AppResult.Error -> fail(v.error.userMessage)
                is AppResult.Success -> uploadAfterValidate(v.data, openStream, onComplete)
            }
        }
    }

    private suspend fun uploadAfterValidate(
        response: FileValidateResponse,
        openStream: () -> InputStream,
        onComplete: (Dataset) -> Unit,
    ) {
        _state.value = _state.value.copy(
            upload = UploadState(UploadPhase.Uploading, 0f, response.fileName),
        )
        when (val up = datasetsRepo.upload(
            response,
            openStream,
            onProgress = { sent, total ->
                if (total > 0) {
                    _state.value = _state.value.copy(
                        upload = UploadState(UploadPhase.Uploading, sent.toFloat() / total, response.fileName),
                    )
                }
            },
        )) {
            is AppResult.Error -> _state.value = _state.value.copy(
                upload = UploadState(phase = UploadPhase.Error, error = up.error.userMessage),
            )
            is AppResult.Success -> {
                val name = response.fileName.substringBeforeLast(".").ifBlank { "dataset" }
                val source = if (response.extension.lowercase() == "xlsx" || response.extension.lowercase() == "xls") "excel" else "csv"
                when (val reg = datasetsRepo.register(
                    projectId, name, source, response.storagePath, response.fileSize, response.mimeType,
                )) {
                    is AppResult.Error -> _state.value = _state.value.copy(
                        upload = UploadState(phase = UploadPhase.Error, error = reg.error.userMessage),
                    )
                    is AppResult.Success -> {
                        datasetsRepo.process(reg.data.id)
                        _state.value = _state.value.copy(
                            upload = UploadState(phase = UploadPhase.Done, fileName = name),
                        )
                        onComplete(reg.data)
                        load(projectId)
                    }
                }
            }
        }
    }
}