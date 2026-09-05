package com.analyticsagent.ui.results

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountTree
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.PrimaryScrollableTabRow
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.DaxMeasure
import com.analyticsagent.domain.model.ExcelFormula
import com.analyticsagent.domain.model.Insight
import com.analyticsagent.domain.model.Metric
import com.analyticsagent.domain.model.RunDetail
import com.analyticsagent.domain.model.SqlQuery
import com.analyticsagent.domain.model.StarSchemaModel
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
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(runId) { vm.load(runId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Analysis Intelligence Hub", fontWeight = FontWeight.Bold)
                        Text("Deterministic Analytics & Visuals", style = MaterialTheme.typography.labelSmall, color = Color(0xFF00F2FE))
                    }
                },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading verified analysis results…")
            state.error != null -> ErrorBox(state.error!!)
            else -> Column(Modifier.fillMaxSize().padding(padding)) {
                PrimaryScrollableTabRow(
                    selectedTabIndex = state.tab.ordinal,
                    containerColor = Color(0xFF131A29),
                    contentColor = Color(0xFF00F2FE),
                    edgePadding = 12.dp
                ) {
                    ResultsTab.entries.forEach { tab ->
                        Tab(
                            selected = state.tab == tab,
                            onClick = { vm.selectTab(tab) },
                            text = {
                                Text(
                                    tab.label,
                                    fontWeight = if (state.tab == tab) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 13.sp
                                )
                            },
                        )
                    }
                }
                val detail = state.detail
                if (detail == null) {
                    ErrorBox("No result data available for this run.")
                } else {
                    when (state.tab) {
                        ResultsTab.Overview -> OverviewTab(detail, projectId, runId, nav)
                        ResultsTab.Dashboard -> DashboardTab(detail, projectId, runId, nav)
                        ResultsTab.Dax -> DaxTab(detail.daxMeasures)
                        ResultsTab.StarSchema -> StarSchemaTab(detail.starSchema)
                        ResultsTab.ExcelFormulas -> ExcelTab(detail.excelFormulas)
                        ResultsTab.SqlQueries -> SqlTab(detail.sqlQueries)
                        ResultsTab.Insights -> InsightsTab(detail.insights)
                        ResultsTab.Metrics -> MetricsTab(detail.metrics)
                        ResultsTab.Report -> ReportTab(detail)
                        ResultsTab.Quality -> QualityTab(detail.dataQuality?.score)
                    }
                }
            }
        }
    }
}

@Composable
private fun OverviewTab(detail: RunDetail, projectId: String, runId: String, nav: NavController) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Execution Status", style = MaterialTheme.typography.labelMedium, color = Color(0xFF94A3B8))
                        StatusChip(detail.status, Color(0xFF10B981))
                    }
                    Spacer(Modifier.height(8.dp))
                    Text("Prompt Specification", style = MaterialTheme.typography.labelMedium, color = Color(0xFF94A3B8))
                    Text(detail.userPrompt, style = MaterialTheme.typography.bodyMedium, color = Color.White)
                }
            }
        }

        // Quick Mode Navigation Badges
        item {
            Text("Analytical Deliverables", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                DeliverableChip(
                    title = "Dashboard",
                    icon = Icons.Default.Dashboard,
                    color = Color(0xFF00F2FE),
                    onClick = { nav.navigate(Routes.dashboard(projectId, runId)) },
                    modifier = Modifier.weight(1f)
                )
                DeliverableChip(
                    title = "DAX Measures",
                    icon = Icons.Default.AutoGraph,
                    color = Color(0xFFF2C811),
                    onClick = { nav.navigate(Routes.dax(projectId, runId)) },
                    modifier = Modifier.weight(1f)
                )
            }
        }

        item {
            Text("Verified Executive Metrics", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }
        items(detail.metrics.filter { !it.isNotSupported }.take(8)) { metric ->
            MetricRow(metric)
        }
    }
}

@Composable
private fun DeliverableChip(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        onClick = onClick,
        modifier = modifier.border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.height(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(title, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
    }
}

@Composable
internal fun MetricRow(metric: Metric) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(metric.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, color = Color.White)
                Text(metric.metricId, style = MaterialTheme.typography.labelSmall, color = Color(0xFF94A3B8))
            }
            Text(
                JsonFormat.metricDisplay(metric.value),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF00F2FE)
            )
        }
    }
}

@Composable
private fun DaxTab(measures: List<DaxMeasure>) {
    val context = LocalContext.current
    fun copy(text: String, label: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied: $label", Toast.LENGTH_SHORT).show()
    }

    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (measures.isEmpty()) {
            item { Text("No DAX measures generated for this run.", color = Color(0xFF94A3B8)) }
        }
        items(measures, key = { it.name }) { m ->
            Card(
                Modifier.fillMaxWidth().border(1.dp, Color(0xFF1E293B), RoundedCornerShape(10.dp)),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                shape = RoundedCornerShape(10.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(m.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = Color.White)
                        OutlinedButton(onClick = { copy(m.daxCode, m.name) }) {
                            Text("Copy", fontSize = 11.sp)
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(Color(0xFF0A0E17))
                            .padding(8.dp)
                    ) {
                        Text(m.daxCode, fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = Color(0xFFF2C811))
                    }
                    if (!m.purpose.isNullOrBlank()) {
                        Spacer(Modifier.height(6.dp))
                        Text(m.purpose, style = MaterialTheme.typography.labelSmall, color = Color(0xFF94A3B8))
                    }
                }
            }
        }
    }
}

@Composable
private fun StarSchemaTab(model: StarSchemaModel?) {
    if (model == null) {
        Box(Modifier.fillMaxSize().padding(16.dp), contentAlignment = Alignment.Center) {
            Text("No Star Schema generated for this run. Switch to Power BI mode in the prompt screen.", color = Color(0xFF94A3B8))
        }
    } else {
        LazyColumn(
            Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("Fact & Dimension Entities", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color(0xFF00F2FE))
            }
            items(model.factTables) { t ->
                Card(
                    Modifier.fillMaxWidth().border(1.dp, Color(0xFF00F2FE).copy(alpha = 0.4f), RoundedCornerShape(10.dp)),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29))
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text("FACT: ${t.name}", fontWeight = FontWeight.Bold, color = Color(0xFF00F2FE))
                        Text(t.columns.joinToString(", "), fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = Color(0xFFE2E8F0))
                    }
                }
            }
            items(model.dimensionTables) { t ->
                Card(
                    Modifier.fillMaxWidth().border(1.dp, Color(0xFF10B981).copy(alpha = 0.4f), RoundedCornerShape(10.dp)),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29))
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text("DIMENSION: ${t.name}", fontWeight = FontWeight.Bold, color = Color(0xFF10B981))
                        Text(t.columns.joinToString(", "), fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = Color(0xFFE2E8F0))
                    }
                }
            }
        }
    }
}

@Composable
private fun ExcelTab(formulas: List<ExcelFormula>) {
    val context = LocalContext.current
    fun copy(text: String, label: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied: $label", Toast.LENGTH_SHORT).show()
    }

    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (formulas.isEmpty()) {
            item { Text("No Excel formulas generated for this run. Switch to Excel mode in prompt.", color = Color(0xFF94A3B8)) }
        }
        items(formulas, key = { it.name }) { f ->
            Card(
                Modifier.fillMaxWidth().border(1.dp, Color(0xFF1E293B), RoundedCornerShape(10.dp)),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29))
            ) {
                Column(Modifier.padding(14.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text(f.name, fontWeight = FontWeight.Bold, color = Color.White)
                        OutlinedButton(onClick = { copy(f.mCode ?: f.vbaCode ?: f.formula, f.name) }) {
                            Text("Copy", fontSize = 11.sp)
                        }
                    }
                    Spacer(Modifier.height(6.dp))
                    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp)).background(Color(0xFF0A0E17)).padding(8.dp)) {
                        Text(f.mCode ?: f.vbaCode ?: f.formula, fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = Color(0xFF107C41))
                    }
                }
            }
        }
    }
}

@Composable
private fun SqlTab(queries: List<SqlQuery>) {
    val context = LocalContext.current
    fun copy(text: String, label: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied: $label", Toast.LENGTH_SHORT).show()
    }

    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (queries.isEmpty()) {
            item { Text("No SQL queries generated for this run. Switch to SQL mode in prompt.", color = Color(0xFF94A3B8)) }
        }
        items(queries, key = { it.title }) { q ->
            Card(
                Modifier.fillMaxWidth().border(1.dp, Color(0xFF1E293B), RoundedCornerShape(10.dp)),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29))
            ) {
                Column(Modifier.padding(14.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text(q.title, fontWeight = FontWeight.Bold, color = Color.White)
                        OutlinedButton(onClick = { copy(q.sqlCode, q.title) }) {
                            Text("Copy SQL", fontSize = 11.sp)
                        }
                    }
                    Spacer(Modifier.height(6.dp))
                    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp)).background(Color(0xFF0A0E17)).padding(8.dp)) {
                        Text(q.sqlCode, fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = Color(0xFF38BDF8))
                    }
                }
            }
        }
    }
}

@Composable
private fun InsightsTab(insights: List<Insight>) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (insights.isEmpty()) {
            item { Text("No insights generated.", color = Color(0xFF94A3B8)) }
        }
        items(insights.size) { i ->
            val ins = insights[i]
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                shape = RoundedCornerShape(10.dp)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(ins.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White, modifier = Modifier.weight(1f))
                        StatusChip(ins.priority, Color(0xFF8B5CF6))
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(ins.finding, style = MaterialTheme.typography.bodyMedium, color = Color(0xFFE2E8F0))
                    if (!ins.recommendation.isNullOrBlank()) {
                        Spacer(Modifier.height(6.dp))
                        Text("Recommendation: ${ins.recommendation}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF00F2FE))
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
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (metrics.isEmpty()) {
            item { Text("No metrics computed.", color = Color(0xFF94A3B8)) }
        }
        items(metrics.size) { i ->
            val m = metrics[i]
            MetricRow(m)
        }
    }
}

@Composable
private fun ReportTab(detail: RunDetail) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Executive Data Analysis Report", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = Color.White)
        Spacer(Modifier.height(8.dp))
        Text(
            "The report was computed deterministically from the dataset schema and metric registry.",
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFF94A3B8),
        )
        Spacer(Modifier.height(12.dp))
        Text(
            "Includes: Executive Summary, Key Findings, KPI Metrics, Risk Assessment, and Strategic Recommendations.",
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFFE2E8F0)
        )
    }
}

@Composable
private fun DashboardTab(detail: RunDetail, projectId: String, runId: String, nav: NavController) {
    Column(Modifier.fillMaxSize().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text("Executive Dashboard Visual", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = Color.White)
        Spacer(Modifier.height(8.dp))
        Text(
            "High-resolution 220 DPI dashboard image rendered from verified metric registers.",
            style = MaterialTheme.typography.bodyMedium,
            color = Color(0xFF94A3B8),
        )
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { nav.navigate(Routes.dashboard(projectId, runId)) },
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00F2FE), contentColor = Color(0xFF0A0E17))
        ) {
            Text("Open Fullscreen Dashboard Preview", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun QualityTab(score: Double?) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Dataset Quality Score", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = Color.White)
        Spacer(Modifier.height(8.dp))
        Text(
            score?.let { "Overall Quality Rating: %.1f%%".format(it) } ?: "Quality score not available.",
            style = MaterialTheme.typography.bodyLarge,
            color = Color(0xFF10B981),
            fontWeight = FontWeight.Bold
        )
    }
}
