package com.analyticsagent.ui.progress

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.Formatters

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisProgressScreen(container: AppContainer, nav: NavController, projectId: String, runId: String) {
    val vm: AnalysisProgressViewModel = viewModel(factory = VmFactory.from {
        AnalysisProgressViewModel(container.analysisRepository)
    })
    val state by vm.state

    LaunchedEffect(runId) { vm.startPolling(runId) }

    // Navigate to results when done.
    LaunchedEffect(state.done) {
        if (state.done && state.run?.isSuccess == true) {
            nav.navigate(Routes.runResults(projectId, runId)) {
                popUpTo(Routes.project(projectId)) { inclusive = false }
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Analysis") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            val run = state.run
            if (run != null) {
                if (run.isSuccess) {
                    CircularProgressIndicator(Modifier.size(48.dp))
                    Spacer(Modifier.height(16.dp))
                    Text("Analysis complete!", style = MaterialTheme.typography.titleLarge,
                         fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.secondary)
                    Spacer(Modifier.height(8.dp))
                    Text("Opening results…", style = MaterialTheme.typography.bodyMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else if (run.status == "failed" || run.status == "validation_failed") {
                    ErrorBox(state.error ?: "Analysis did not complete successfully.")
                    Spacer(Modifier.height(16.dp))
                    TextButton(onClick = { nav.popBackStack() }) { Text("Go back") }
                } else {
                    CircularProgressIndicator(Modifier.size(48.dp))
                    Spacer(Modifier.height(16.dp))
                    Text("Analyzing dataset…", style = MaterialTheme.typography.titleLarge,
                         fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(progress = { run.progress / 100.0f },
                        modifier = Modifier.fillMaxWidth(0.8f))
                    Spacer(Modifier.height(8.dp))
                    Text("${run.progress}% · ${Formatters.humanReadableStage(run.stage)}",
                         style = MaterialTheme.typography.bodyMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                Text("Starting analysis…", style = MaterialTheme.typography.bodyLarge)
            }
        }
    }
}