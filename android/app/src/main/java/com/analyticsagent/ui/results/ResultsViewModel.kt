package com.analyticsagent.ui.results

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.domain.model.RunDetail
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class ResultsTab(val label: String) {
    Overview("Overview"),
    Dashboard("Dashboard"),
    Dax("DAX (PowerBI)"),
    StarSchema("Data Model"),
    ExcelFormulas("Excel"),
    SqlQueries("MySQL"),
    Python("Python"),
    Insights("Insights"),
    Metrics("KPIs"),
    Report("Report"),
    Quality("Quality"),
}

data class ResultsUiState(
    val loading: Boolean = true,
    val detail: RunDetail? = null,
    val error: String? = null,
    val tab: ResultsTab = ResultsTab.Overview,
)

class ResultsViewModel(private val analysis: AnalysisRepository) : ViewModel() {
    private val _state = MutableStateFlow(ResultsUiState())
    val state = _state.asStateFlow()

    fun load(runId: String) {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = analysis.getRunDetail(runId)) {
                is AppResult.Success ->
                    _state.value = ResultsUiState(loading = false, detail = r.data)
                is AppResult.Error ->
                    _state.value = ResultsUiState(loading = false, error = r.error.userMessage)
            }
        }
    }

    fun selectTab(tab: ResultsTab) {
        _state.value = _state.value.copy(tab = tab)
    }
}
