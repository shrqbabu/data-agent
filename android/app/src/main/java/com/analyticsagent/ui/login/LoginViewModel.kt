package com.analyticsagent.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.AuthRepository
import com.analyticsagent.util.AppResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val showPassword: Boolean = false,
)

class LoginViewModel(private val auth: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(LoginUiState())
    val state = _state.asStateFlow()

    fun onEmailChange(v: String) {
        _state.value = _state.value.copy(email = v, error = null)
    }

    fun onPasswordChange(v: String) {
        _state.value = _state.value.copy(password = v, error = null)
    }

    fun togglePassword() {
        _state.value = _state.value.copy(showPassword = !_state.value.showPassword)
    }

    fun signIn() {
        val s = _state.value
        if (s.email.isBlank() || s.password.isBlank()) {
            _state.value = _state.value.copy(error = "Enter your email and password.")
            return
        }
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = auth.signIn(s.email, s.password)) {
                is AppResult.Success -> {
                    // Session stored; the auth gate will navigate to Projects.
                    _state.value = _state.value.copy(loading = false, error = null)
                }
                is AppResult.Error -> {
                    _state.value = _state.value.copy(loading = false, error = r.error.userMessage)
                }
            }
        }
    }
}
