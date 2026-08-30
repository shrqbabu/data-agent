package com.analyticsagent.ui.dax

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.DaxMeasure
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.VmFactory

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DaxScreen(container: AppContainer, nav: NavController, projectId: String, runId: String) {
    val vm: DaxViewModel = viewModel(factory = VmFactory.from {
        DaxViewModel(container.analysisRepository, container.artifactRepository)
    })
    val state by vm.state
    val context = LocalContext.current

    LaunchedEffect(runId) { vm.load(runId) }

    fun copy(text: String, label: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied: $label", Toast.LENGTH_SHORT).show()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("DAX Measures") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                actions = {
                    TextButton(onClick = { copy(vm.copyAllText(), "All DAX Measures") }) { Text("Copy All") }
                    TextButton(onClick = { vm.downloadAll(projectId, runId) }) { Text("Download") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading DAX…")
            state.error != null -> ErrorBox(state.error!!)
            state.measures.isEmpty() -> ErrorBox("No DAX measures generated for this run.")
            else -> LazyColumn(
                Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(state.measures, key = { it.name }) { measure ->
                    DaxCard(measure, onCopy = { copy(measure.daxCode, measure.name) })
                }
            }
        }
    }
}

@Composable
private fun DaxCard(measure: DaxMeasure, onCopy: () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text(measure.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                OutlinedButton(onClick = onCopy) { Text("Copy") }
            }
            Spacer(Modifier.height(8.dp))
            Text(measure.daxCode, style = MaterialTheme.typography.bodySmall)
            if (measure.purpose != null) {
                Spacer(Modifier.height(4.dp))
                Text(measure.purpose, style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}