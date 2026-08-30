package com.analyticsagent.ui.projects

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AuthRepository
import com.analyticsagent.data.repository.ProjectRepository
import com.analyticsagent.domain.model.Project
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ProjectsUiState(
    val loading: Boolean = true,
    val projects: List<Project> = emptyList(),
    val error: String? = null,
)

class ProjectsViewModel(
    private val projects: ProjectRepository,
    private val auth: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ProjectsUiState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = projects.list()) {
                is AppResult.Success -> _state.value = ProjectsUiState(loading = false, projects = r.data)
                is AppResult.Error -> _state.value = ProjectsUiState(loading = false, error = r.error.userMessage)
            }
        }
    }

    fun signOut() {
        viewModelScope.launch { auth.signOut() }
    }
}