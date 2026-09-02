package com.analyticsagent.ui.prompt

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
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.SectionHeader
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.Formatters

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportPromptScreen(container: AppContainer, nav: NavController, projectId: String) {
    val vm: ReportPromptViewModel = viewModel(factory = VmFactory.from {
        ReportPromptViewModel(container.analysisRepository, container.datasetRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(projectId) { vm.load(projectId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Report Prompt") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (state.loading) {
                item { LoadingBox("Loading…") }
            } else {
                item {
                    SectionHeader(
                        "What should I analyze?",
                        "Your prompt controls the report sections, KPIs, comparisons and visuals. "
                            + "Skills provide the analytical capability; your prompt is the specification.",
                    )
                }
                item {
                    OutlinedTextField(
                        value = state.prompt,
                        onValueChange = vm::onPromptChange,
                        placeholder = {
                            Text("Example: Analyze monthly revenue and growth. Segment by region and category. "
                                + "Show top 10 products, customer repeat rate, and forecast the next quarter. "
                                + "Highlight risks and give recommendations.")
                        },
                        minLines = 8,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                if (state.datasets.isEmpty()) {
                    item {
                        ErrorBox("No dataset uploaded yet. Go back and upload a CSV/Excel file first.")
                    }
                }
                if (state.error != null) {
                    item { ErrorBox(state.error!!) }
                }
                item {
                    Button(
                        onClick = {
                            vm.generate { run ->
                                nav.navigate(Routes.runProgress(projectId, run.id))
                            }
                        },
                        enabled = !state.submitting && state.prompt.isNotBlank() && state.datasets.isNotEmpty(),
                        modifier = Modifier.fillMaxWidth().height(50.dp),
                    ) {
                        if (state.submitting) {
                            CircularProgressIndicator(Modifier.padding(0.dp).height(20.dp),
                                strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                        } else {
                            Text("Generate Analysis")
                        }
                    }
                }
                if (state.promptHistory.isNotEmpty()) {
                    item {
                        Text("Prompt History", style = MaterialTheme.typography.titleLarge,
                             fontWeight = FontWeight.Bold)
                    }
                    items(state.promptHistory, key = { it.runId }) { item ->
                        Card(
                            onClick = { vm.usePrompt(item.prompt) },
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                Text("\"${item.prompt.take(90)}${if (item.prompt.length > 90) "…" else ""}\"",
                                     style = MaterialTheme.typography.bodyMedium)
                                Spacer(Modifier.height(4.dp))
                                Row {
                                    Text("Run: ${item.status} · ${Formatters.formatDate(item.createdAt)}",
                                         style = MaterialTheme.typography.labelSmall,
                                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
