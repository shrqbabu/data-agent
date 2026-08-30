package com.analyticsagent.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AnalysisRepository
import com.analyticsagent.data.repository.ProjectRepository
import com.analyticsagent.domain.model.Project
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ProjectSettingsUiState(
    val loading: Boolean = true,
    val project: Project? = null,
    val error: String? = null,
    val deleting: Boolean = false,
    val deleted: Boolean = false,
)

class ProjectSettingsViewModel(
    private val projects: ProjectRepository,
    private val analysis: AnalysisRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ProjectSettingsUiState())
    val state = _state.asStateFlow()

    fun load(projectId: String) {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = projects.get(projectId)) {
                is AppResult.Success -> _state.value = ProjectSettingsUiState(loading = false, project = r.data)
                is AppResult.Error -> _state.value = ProjectSettingsUiState(loading = false, error = r.error.userMessage)
            }
        }
    }

    fun deleteProject(projectId: String) {
        _state.value = _state.value.copy(deleting = true, error = null)
        viewModelScope.launch {
            when (val r = projects.delete(projectId)) {
                is AppResult.Success -> _state.value = _state.value.copy(deleting = false, deleted = true)
                is AppResult.Error -> _state.value = _state.value.copy(deleting = false, error = r.error.userMessage)
            }
        }
    }
}