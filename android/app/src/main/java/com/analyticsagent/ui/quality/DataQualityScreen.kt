package com.analyticsagent.ui.quality

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.JsonFormat
import kotlin.math.roundToInt
import kotlinx.serialization.json.JsonObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DataQualityScreen(container: AppContainer, nav: NavController, projectId: String, datasetId: String) {
    val vm: DataQualityViewModel = viewModel(factory = VmFactory.from {
        DataQualityViewModel(container.datasetRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(datasetId) { vm.load(datasetId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Data Quality") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading quality…")
            state.error != null -> ErrorBox(state.error!!)
            else -> LazyColumn(
                Modifier.fillMaxSize().padding(padding),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    val score = JsonFormat.number(state.quality, "score") ?: 0.0
                    Card(Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(Modifier.padding(16.dp)) {
                            Text("Overall Quality", style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(8.dp))
                            LinearProgressIndicator(
                                progress = { (score / 100.0).toFloat() },
                                modifier = Modifier.fillMaxWidth(),
                            )
                            Spacer(Modifier.height(6.dp))
                            Text("${score.roundToInt()} / 100",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
                if (state.quality != null) {
                    val q = state.quality!!
                    item {
                        val completeness = JsonFormat.number(q["completeness"], "pct")
                        val validity = JsonFormat.number(q["validity"], "pct")
                        val uniqueness = JsonFormat.number(q["uniqueness"], "score")
                        val dup = JsonFormat.long(q["consistency"], "duplicate_rows")
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Tile("Completeness", completeness?.let { "${it.roundToInt()}%" } ?: "—")
                            Tile("Validity", validity?.let { "${it.roundToInt()}%" } ?: "—")
                        }
                        Spacer(Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Tile("Uniqueness", uniqueness?.let { "${it.roundToInt()}%" } ?: "—")
                            Tile("Duplicate rows", dup?.toString() ?: "—")
                        }
                    }
                    item {
                        IssuesList(q)
                    }
                }
            }
        }
    }
}

@Composable
private fun RowScope.Tile(label: String, value: String) {
    Card(
        modifier = Modifier.weight(1f),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)),
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun IssuesList(q: JsonObject) {
    val issues = JsonFormat.listOfObjects(q["issues"])
    Column {
        Text("Issues", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        if (issues.isEmpty()) {
            Text("No issues detected.", style = MaterialTheme.typography.bodyMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            issues.forEach { issue ->
                Card(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.25f)),
                ) {
                    Row(Modifier.padding(12.dp)) {
                        Icon(Icons.Filled.Warning, null, tint = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "[${JsonFormat.textOf(issue, "severity")}] ${JsonFormat.textOf(issue, "message")}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }
            }
        }
    }
}
