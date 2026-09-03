package com.analyticsagent.ui.dataset

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.Dataset
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.EmptyBox
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.SectionHeader
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.JsonFormat
import kotlin.math.roundToInt
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DatasetScreen(container: AppContainer, nav: NavController, projectId: String) {
    val vm: DatasetViewModel = viewModel(factory = VmFactory.from {
        DatasetViewModel(container.projectRepository, container.datasetRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()

    val context = LocalContext.current
    var schemaFor by remember { mutableStateOf<Dataset?>(null) }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) {
            val (name, size) = queryFileMeta(context, uri)
            val mime = context.contentResolver.getType(uri) ?: ""
            vm.uploadFile(
                fileName = name,
                fileSize = size,
                mimeType = mime,
                openStream = { context.contentResolver.openInputStream(uri)!! },
                onComplete = {},
            )
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.project?.name ?: "Dataset") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                actions = { TextButton(onClick = vm::retry) { Text("Refresh") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            when {
                state.loading && state.datasets.isEmpty() ->
                    item { LoadingBox("Loading project…") }

                state.error != null && state.datasets.isEmpty() ->
                    item { ErrorBox(state.error!!) }

                else -> {
                    item {
                        SectionHeader(
                            title = if (state.datasets.isEmpty()) "Dataset Overview"
                            else "Dataset Overview · ${state.datasets.size} dataset(s)",
                        )
                    }
                    if (state.datasets.isNotEmpty()) {
                        items(state.datasets, key = { it.id }) { dataset ->
                            DatasetCard(
                                dataset = dataset,
                                onViewSchema = { schemaFor = dataset },
                                onViewQuality = {
                                    nav.navigate(Routes.quality(projectId, dataset.id))
                                },
                            )
                        }
                    } else {
                        item {
                            EmptyBox(
                                "No data yet",
                                "Upload a CSV or Excel file, then run your analysis.",
                            )
                        }
                    }
                    item {
                        UploadPanel(
                            upload = state.upload,
                            onClick = {
                                if (state.upload.phase != UploadPhase.Uploading) {
                                    picker.launch(
                                        arrayOf(
                                            "text/csv",
                                            "application/vnd.ms-excel",
                                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            "*/*",
                                        ),
                                    )
                                }
                            },
                        )
                    }
                    item {
                        Button(
                            onClick = { nav.navigate(Routes.prompt(projectId)) },
                            enabled = state.datasets.isNotEmpty(),
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                        ) {
                            Text("Run Analysis")
                        }
                    }
                }
            }
        }
    }

    schemaFor?.let { ds ->
        SchemaDialog(dataset = ds, onDismiss = { schemaFor = null })
    }
}

private fun queryFileMeta(context: Context, uri: Uri): Pair<String, Long> {
    var name = "dataset-file"
    var size = 0L
    context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
        val nameIdx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        val sizeIdx = cursor.getColumnIndex(OpenableColumns.SIZE)
        if (cursor.moveToFirst()) {
            if (nameIdx >= 0) cursor.getString(nameIdx)?.let { name = it }
            if (sizeIdx >= 0) size = cursor.getLong(sizeIdx)
        }
    }
    return name to size
}

@Composable
private fun DatasetCard(dataset: Dataset, onViewSchema: () -> Unit, onViewQuality: () -> Unit) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    DatasetInfo.fileLabel(dataset),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = MaterialTheme.shapes.small) {
                    Text(
                        dataset.sourceLabel,
                        Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatBox("Rows", dataset.rowCount.toString())
                StatBox("Columns", dataset.columnCount.toString())
                StatBox("Date range", DatasetInfo.dateRange(dataset))
            }
            val score = DatasetInfo.qualityScore(dataset)
            if (score != null) {
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Data Quality", style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.width(8.dp))
                    LinearProgressIndicator(
                        progress = { (score / 100.0).toFloat() },
                        modifier = Modifier.weight(1f),
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("${score.roundToInt()}%", style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.primary)
                }
            }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onViewSchema, modifier = Modifier.weight(1f)) { Text("View Schema") }
                OutlinedButton(onClick = onViewQuality, modifier = Modifier.weight(1f)) { Text("View Quality") }
            }
        }
    }
}

@Composable
private fun RowScope.StatBox(label: String, value: String) {
    Surface(
        modifier = Modifier.weight(1f),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        shape = MaterialTheme.shapes.small,
    ) {
        Column(Modifier.padding(10.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium,
                 color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleMedium,
                 fontWeight = FontWeight.Bold, maxLines = 1)
        }
    }
}

@Composable
private fun UploadPanel(upload: UploadState, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            SectionHeader("Add Data", "Upload a CSV or Excel file to analyze.")
            Spacer(Modifier.height(10.dp))
            when (upload.phase) {
                UploadPhase.Idle -> OutlinedButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.FolderOpen, null)
                    Spacer(Modifier.width(6.dp))
                    Text("Upload CSV / Excel")
                }
                UploadPhase.Validating -> {
                    Text("Validating file…")
                    LinearProgressIndicator(progress = { 0f }, modifier = Modifier.fillMaxWidth())
                }
                UploadPhase.Uploading -> {
                    Text("Uploading ${upload.fileName ?: "file"}…")
                    Spacer(Modifier.height(6.dp))
                    LinearProgressIndicator(progress = { upload.progress }, modifier = Modifier.fillMaxWidth())
                    Text("${(upload.progress * 100).roundToInt()}%",
                         style = MaterialTheme.typography.labelMedium,
                         color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                UploadPhase.Error -> ErrorBox(upload.error ?: "Upload failed.")
                UploadPhase.Processing -> LoadingBox("Processing dataset…")
                UploadPhase.Done -> Text("Uploaded & processing", color = MaterialTheme.colorScheme.secondary)
            }
        }
    }
}

@Composable
private fun SchemaDialog(dataset: Dataset, onDismiss: () -> Unit) {
    val columns = schemaColumns(dataset.schema)
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
        title = { Text("Schema — ${DatasetInfo.fileLabel(dataset)}") },
        text = {
            if (columns.isEmpty()) {
                Text("No schema available yet. Dataset may still be processing.")
            } else {
                LazyColumn {
                    items(columns.size) { i ->
                        val c = columns[i]
                        Row(Modifier.padding(vertical = 4.dp)) {
                            Text(c["name"] ?: "", fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.width(8.dp))
                            Text(c["kind"] ?: "", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(Modifier.width(8.dp))
                            Text("missing ${c["missing_pct"] ?: "–"}%",
                                 style = MaterialTheme.typography.labelMedium,
                                 color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        },
    )
}

private fun schemaColumns(schema: JsonElement?): List<Map<String, String>> {
    return when (schema) {
        is JsonArray -> schema.mapNotNull { el ->
            val o = el as? JsonObject ?: return@mapNotNull null
            mapOf(
                "name" to JsonFormat.asText(o["name"]),
                "kind" to JsonFormat.asText(o["kind"]),
                "missing_pct" to JsonFormat.asText(o["missing_pct"]),
            )
        }
        else -> emptyList()
    }
}
