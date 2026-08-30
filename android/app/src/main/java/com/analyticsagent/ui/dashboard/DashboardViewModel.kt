package com.analyticsagent.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.ArtifactRepository
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.domain.model.Artifact
import com.analyticsagent.domain.model.SignedUrlResponse
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(
    val loading: Boolean = true,
    val imageUrl: String? = null,
    val artifact: Artifact? = null,
    val error: String? = null,
    val fullUrl: String? = null,
)

class DashboardViewModel(
    private val analysis: AnalysisRepository,
    private val artifacts: ArtifactRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state = _state.asStateFlow()

    fun load(runId: String) {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = analysis.getRunDetail(runId)) {
                is AppResult.Success -> {
                    val art = r.data.dashboardArtifact
                    if (art != null) {
                        when (val url = artifacts.downloadUrl(art.id)) {
                            is AppResult.Success -> _state.value = DashboardUiState(
                                loading = false,
                                imageUrl = url.data.signedUrl,
                                artifact = art,
                                fullUrl = url.data.signedUrl,
                            )
                            is AppResult.Error -> _state.value = DashboardUiState(
                                loading = false, error = url.error.userMessage,
                            )
                        }
                    } else {
                        _state.value = DashboardUiState(loading = false, error = "No dashboard image for this run.")
                    }
                }
                is AppResult.Error -> _state.value = DashboardUiState(loading = false, error = r.error.userMessage)
            }
        }
    }
}