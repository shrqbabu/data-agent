package com.analyticsagent.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import com.analyticsagent.ui.components.VmFactory

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectSettingsScreen(container: AppContainer, nav: NavController, projectId: String) {
    val vm: ProjectSettingsViewModel = viewModel(factory = VmFactory.from {
        ProjectSettingsViewModel(container.projectRepository, container.analysisRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()
    var showDeleteConfirm by remember { mutableStateOf(false) }

    LaunchedEffect(projectId) { vm.load(projectId) }

    // Navigate to projects when deleted.
    LaunchedEffect(state.deleted) {
        if (state.deleted) {
            nav.navigate(Routes.PROJECTS) {
                popUpTo(Routes.PROJECTS) { inclusive = true }
            }
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            confirmButton = {
                TextButton(onClick = {
                    showDeleteConfirm = false
                    vm.deleteProject(projectId)
                }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { showDeleteConfirm = false }) { Text("Cancel") } },
            title = { Text("Delete Project") },
            text = { Text("This will permanently delete all files, analysis runs, metrics, insights, "
                + "DAX measures, dashboard images, and reports. This action cannot be undone.") },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Project Settings") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading…")
            state.error != null -> ErrorBox(state.error!!)
            else -> Column(
                Modifier.fillMaxSize().padding(padding).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                state.project?.let { project ->
                    Card(Modifier.fillMaxWidth(),
                         colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                        Column(Modifier.padding(16.dp)) {
                            Text("Project", style = MaterialTheme.typography.labelMedium,
                                 color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(project.name, style = MaterialTheme.typography.titleLarge,
                                 fontWeight = FontWeight.Bold)
                            Text(project.description.ifBlank { "No description" },
                                 style = MaterialTheme.typography.bodyMedium,
                                 color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }

                Card(Modifier.fillMaxWidth(),
                     colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.2f))) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Danger Zone", style = MaterialTheme.typography.titleMedium,
                             fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(8.dp))
                        Text("Deleting this project removes all associated data irreversibly.",
                             style = MaterialTheme.typography.bodyMedium,
                             color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(12.dp))
                        Button(
                            onClick = { showDeleteConfirm = true },
                            enabled = !state.deleting,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            if (state.deleting) {
                                CircularProgressIndicator(Modifier.padding(0.dp).height(20.dp),
                                    strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onError)
                            } else {
                                Text("Delete Project")
                            }
                        }
                    }
                }
            }
        }
    }
}
