package com.analyticsagent.ui.newproject

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.ProjectRepository
import com.analyticsagent.domain.model.Project
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class NewProjectUiState(
    val name: String = "",
    val description: String = "",
    val saving: Boolean = false,
    val error: String? = null,
)

class NewProjectViewModel(private val projects: ProjectRepository) : ViewModel() {
    private val _state = MutableStateFlow(NewProjectUiState())
    val state = _state.asStateFlow()

    private var _created = MutableStateFlow<Project?>(null)
    val created: kotlinx.coroutines.flow.StateFlow<Project?> = _created

    fun onName(v: String) = _state.value = _state.value.copy(name = v, error = null)
    fun onDescription(v: String) = _state.value = _state.value.copy(description = v, error = null)
    fun clearCreated() { _created.value = null }

    fun create(onDone: (Project) -> Unit) {
        if (_state.value.name.isBlank()) {
            _state.value = _state.value.copy(error = "Enter a project name.")
            return
        }
        _state.value = _state.value.copy(saving = true, error = null)
        viewModelScope.launch {
            when (val r = projects.create(_state.value.name.trim(), _state.value.description.trim())) {
                is AppResult.Success -> {
                    _state.value = _state.value.copy(saving = false)
                    _created.value = r.data
                    onDone(r.data)
                }
                is AppResult.Error -> _state.value = _state.value.copy(saving = false, error = r.error.userMessage)
            }
        }
    }
}