package com.analyticsagent.ui.quality

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.analyticsagent.data.repository.DatasetRepository
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.util.AppResult
import com.analyticsagent.util.JsonFormat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject

data class DataQualityUiState(
    val loading: Boolean = true,
    val dataset: Dataset? = null,
    val quality: JsonObject? = null,
    val error: String? = null,
)

class DataQualityViewModel(private val datasets: DatasetRepository) : ViewModel() {
    private val _state = MutableStateFlow(DataQualityUiState())
    val state = _state.asStateFlow()

    fun load(datasetId: String) {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            when (val r = datasets.get(datasetId)) {
                is AppResult.Success -> {
                    val q = JsonFormat.obj(r.data.profile, "quality")
                    _state.value = DataQualityUiState(loading = false, dataset = r.data, quality = q)
                }
                is AppResult.Error -> _state.value = DataQualityUiState(loading = false, error = r.error.userMessage)
            }
        }
    }
}