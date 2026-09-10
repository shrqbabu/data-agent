package com.analyticsagent.ui.prompt

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.data.repository.DatasetRepository
import com.analyticsagent.domain.model.AnalysisMode
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.domain.model.Run
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PromptHistoryItem(val runId: String, val prompt: String, val createdAt: String?, val status: String)

data class ReportPromptUiState(
    val loading: Boolean = true,
    val selectedMode: AnalysisMode = AnalysisMode.POWER_BI,
    val datasets: List<Dataset> = emptyList(),
    val promptHistory: List<PromptHistoryItem> = emptyList(),
    val prompt: String = "",
    val submitting: Boolean = false,
    val error: String? = null,
)

class ReportPromptViewModel(
    private val analysis: AnalysisRepository,
    private val datasetsRepo: DatasetRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportPromptUiState())
    val state = _state.asStateFlow()

    private var projectId: String = ""
    private var _createdRun = MutableStateFlow<Run?>(null)
    val createdRun: kotlinx.coroutines.flow.StateFlow<Run?> = _createdRun

    fun load(pid: String) {
        projectId = pid
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            val dsRes = datasetsRepo.list(pid)
            val runsRes = analysis.listRuns(pid)
            val datasets = (dsRes as? AppResult.Success)?.data ?: emptyList()
            val history = ((runsRes as? AppResult.Success)?.data ?: emptyList()).map {
                PromptHistoryItem(it.id, it.userPrompt, it.createdAt, it.status)
            }
            _state.value = _state.value.copy(
                loading = false,
                datasets = datasets,
                promptHistory = history,
            )
        }
    }

    fun setMode(mode: AnalysisMode) {
        _state.value = _state.value.copy(selectedMode = mode)
    }

    fun setPromptAndMode(promptText: String, mode: AnalysisMode) {
        _state.value = _state.value.copy(prompt = promptText, selectedMode = mode, error = null)
    }

    fun onPromptChange(v: String) {
        _state.value = _state.value.copy(prompt = v, error = null)
    }

    fun usePrompt(p: String) {
        _state.value = _state.value.copy(prompt = p, error = null)
    }

    fun applyPromptTemplate(template: String) {
        val current = _state.value.prompt
        val newPrompt = if (current.isBlank()) template else "$current\n$template"
        _state.value = _state.value.copy(prompt = newPrompt, error = null)
    }

    fun generate(onCreated: (Run) -> Unit) {
        val s = _state.value
        if (s.prompt.isBlank()) {
            _state.value = s.copy(error = "Enter what you want to analyze.")
            return
        }
        val datasetId = s.datasets.firstOrNull()?.id
        _state.value = s.copy(submitting = true, error = null)

        val modePrefix = when (s.selectedMode) {
            AnalysisMode.EXCEL -> "[Mode: Excel] "
            AnalysisMode.POWER_BI -> "[Mode: PowerBI] "
            AnalysisMode.MYSQL -> "[Mode: MySQL] "
            AnalysisMode.PYTHON -> "[Mode: Python] "
            AnalysisMode.ALL -> "[Mode: All] "
        }
        val fullPrompt = if (s.prompt.startsWith("[Mode:")) s.prompt else "$modePrefix${s.prompt.trim()}"

        viewModelScope.launch {
            when (val r = analysis.createRun(projectId, datasetId, fullPrompt)) {
                is AppResult.Success -> {
                    _state.value = _state.value.copy(submitting = false)
                    _createdRun.value = r.data
                    onCreated(r.data)
                }
                is AppResult.Error -> _state.value = _state.value.copy(submitting = false, error = r.error.userMessage)
            }
        }
    }
}
