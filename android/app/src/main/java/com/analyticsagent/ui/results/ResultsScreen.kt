package com.analyticsagent.ui.results

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
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
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.DaxMeasure
import com.analyticsagent.domain.model.Insight
import com.analyticsagent.domain.model.Metric
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.StatusChip
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.JsonFormat

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(container: AppContainer, nav: NavController, projectId: String, runId: String) {
    val vm: ResultsViewModel = viewModel(factory = VmFactory.from {
        ResultsViewModel(container.analysisRepository)
    })
    val state by vm.state

    LaunchedEffect(runId) { vm.load(runId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Analysis Results") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading results…")
            state.error != null -> ErrorBox(state.error!!)
            else -> Column(Modifier.fillMaxSize().padding(padding)) {
                TabRow(selectedTabIndex = state.tab.ordinal) {
                    ResultsTab.entries.forEach { tab ->
                        Tab(
                            selected = state.tab == tab,
                            onClick = { vm.selectTab(tab) },
                            text = { Text(tab.label) },
                        )
                    }
                }
                val detail = state.detail
                if (detail == null) {
                    ErrorBox("No result data.")
                } else {
                    when (state.tab) {
                        ResultsTab.Overview -> OverviewTab(detail, projectId, runId, nav)
                        ResultsTab.Insights -> InsightsTab(detail.insights)
                        ResultsTab.Metrics -> MetricsTab(detail.metrics)
                        ResultsTab.Report -> ReportTab(detail)
                        ResultsTab.Dax -> DaxTab(detail.daxMeasures)
                        ResultsTab.Dashboard -> DashboardTab(detail, projectId, runId, nav)
                        ResultsTab.Quality -> QualityTab(detail.dataQuality?.score)
                    }
                }
            }
        }
    }
}

@Composable
private fun OverviewTab(detail: com.analyticsagent.domain.model.RunDetail, projectId: String, runId: String, nav: NavController) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(16.dp)) {
                    Text("Status", style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                    StatusChip(detail.status, MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(8.dp))
                    Text("Prompt", style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(detail.userPrompt, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { nav.navigate(Routes.dax(projectId, runId)) }, modifier = Modifier.weight(1f)) {
                    Text("Open DAX")
                }
                TextButton(onClick = { nav.navigate(Routes.dashboard(projectId, runId)) }, modifier = Modifier.weight(1f)) {
                    Text("Open Dashboard")
                }
            }
        }
        item {
            Text("Key Metrics", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
        items(detail.metrics.filter { !it.isNotSupported }.take(8)) { metric ->
            MetricRow(metric)
        }
    }
}

@Composable
internal fun MetricRow(metric: Metric) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.padding(14.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(metric.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(metric.metricId, style = MaterialTheme.typography.labelSmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(JsonFormat.metricDisplay(metric.value), style = MaterialTheme.typography.titleMedium,
                 fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun InsightsTab(insights: List<Insight>) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (insights.isEmpty()) {
            item { Text("No insights generated.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        items(insights.size) { i ->
            val ins = insights[i]
            Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(16.dp)) {
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Text(ins.title, style = MaterialTheme.typography.titleMedium,
                             fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                        StatusChip(ins.priority, MaterialTheme.colorScheme.secondary)
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(ins.finding, style = MaterialTheme.typography.bodyMedium)
                    if (!ins.recommendation.isNullOrBlank()) {
                        Spacer(Modifier.height(6.dp))
                        Text("Recommendation: ${ins.recommendation}", style = MaterialTheme.typography.bodySmall,
                             color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricsTab(metrics: List<Metric>) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (metrics.isEmpty()) {
            item { Text("No metrics computed.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        items(metrics.size) { i ->
            val m = metrics[i]
            MetricRow(m)
            if (m.isNotSupported) {
                Text(
                    "NOT SUPPORTED: ${m.definition}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
private fun ReportTab(detail: com.analyticsagent.domain.model.RunDetail) {
    val reportArtifact = detail.reportArtifact
    if (reportArtifact == null) {
        Text("No report artifact for this run.", Modifier.padding(16.dp),
             color = MaterialTheme.colorScheme.onSurfaceVariant)
        return
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Analysis Report", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            "The report was generated from the validated metric registry. Open the artifact to read it "
                + "or download it via the artifacts screen.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(12.dp))
        Text("Report sections: Executive Summary, Key Findings, KPIs, Analysis, Risks, Opportunities, "
            + "Recommendations, Data Quality, Methodology, Limitations.",
            style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun DaxTab(measures: List<DaxMeasure>) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (measures.isEmpty()) {
            item { Text("No DAX measures generated.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
        items(measures.size) { i ->
            val m = measures[i]
            Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(14.dp)) {
                    Text(m.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    Text(m.daxCode, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun DashboardTab(detail: com.analyticsagent.domain.model.RunDetail, projectId: String, runId: String, nav: NavController) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Dashboard PNG", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            if (detail.dashboardArtifact != null) {
                "A high-resolution dashboard PNG was generated from validated values."
            } else {
                "No dashboard PNG for this run."
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(12.dp))
        TextButton(onClick = { nav.navigate(Routes.dashboard(projectId, runId)) }) {
            Text(if (detail.dashboardArtifact != null) "Preview Dashboard" else "View Details")
        }
    }
}

@Composable
private fun QualityTab(score: Double?) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Data Quality", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            score?.let { "Overall data quality score: ${it} / 100" } ?: "No quality score for this run.",
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}