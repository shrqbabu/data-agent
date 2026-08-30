package com.analyticsagent.ui.progress

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.domain.model.Run
import com.analyticsagent.util.AppResult
import com.analyticsagent.util.Formatters
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class ProgressUiState(
    val loading: Boolean = true,
    val run: Run? = null,
    val error: String? = null,
    val done: Boolean = false,
)

class AnalysisProgressViewModel(
    private val analysis: AnalysisRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ProgressUiState())
    val state = _state.asStateFlow()

    private var pollJob: Job? = null

    fun startPolling(runId: String) {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (isActive) {
                when (val r = analysis.getRun(runId)) {
                    is AppResult.Success -> {
                        val run = r.data
                        _state.value = ProgressUiState(
                            loading = false,
                            run = run,
                            done = run.isDone,
                            error = if (run.status == "failed") {
                                "Analysis failed. ${run.error?.let { "Error details available." } ?: ""}"
                            } else if (run.status == "validation_failed") {
                                "Analysis completed but validation failed. Results may be incomplete."
                            } else null,
                        )
                        if (run.isDone) break
                    }
                    is AppResult.Error -> {
                        _state.value = ProgressUiState(loading = false, error = r.error.userMessage, done = true)
                        break
                    }
                }
                delay(2500)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        pollJob?.cancel()
    }
}