package com.analyticsagent.ui.dax

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.ArtifactRepository
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.domain.model.DaxMeasure
import com.analyticsagent.domain.model.SignedUrlResponse
import com.analyticsagent.util.AppResult
import com.analyticsagent.util.JsonFormat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DaxUiState(
    val loading: Boolean = true,
    val measures: List<DaxMeasure> = emptyList(),
    val error: String? = null,
    val downloadUrl: String? = null,
)

class DaxViewModel(
    private val analysis: AnalysisRepository,
    private val artifacts: ArtifactRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DaxUiState())
    val state = _state.asStateFlow()

    fun load(runId: String) {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = analysis.getRunDetail(runId)) {
                is AppResult.Success -> _state.value = DaxUiState(
                    loading = false,
                    measures = r.data.daxMeasures,
                )
                is AppResult.Error -> _state.value = DaxUiState(
                    loading = false,
                    error = r.error.userMessage,
                )
            }
        }
    }

    fun copyAllText(): String = _state.value.measures.joinToString("\n\n\n") { "// ${it.name}\n${it.daxCode}" }

    fun downloadAll(projectId: String, runId: String) {
        viewModelScope.launch {
            when (val r = analysis.getRunDetail(runId)) {
                is AppResult.Success -> {
                    val artifact = r.data.daxArtifact
                    if (artifact != null) {
                        when (val url = artifacts.downloadUrl(artifact.id)) {
                            is AppResult.Success -> _state.value = _state.value.copy(downloadUrl = url.data.signedUrl)
                            else -> {}
                        }
                    }
                }
                else -> {}
            }
        }
    }
}