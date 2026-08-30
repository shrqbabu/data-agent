package com.analyticsagent.ui.projects

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.Project
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.EmptyBox
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.StatusChip
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.Formatters

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectsScreen(container: AppContainer, nav: NavController) {
    val vm: ProjectsViewModel = viewModel(factory = VmFactory.from {
        ProjectsViewModel(container.projectRepository, container.authRepository)
    })
    val state by vm.state

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Analytics", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = vm::signOut) {
                        Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = "Sign out")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { nav.navigate(Routes.NEW_PROJECT) }) {
                Icon(Icons.Filled.Add, contentDescription = "New Project")
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (state.loading && state.projects.isEmpty()) {
                LoadingBox("Loading projects…")
            } else if (state.error != null && state.projects.isEmpty()) {
                ErrorBox(state.error!!, onRetry = vm::refresh)
            } else if (state.projects.isEmpty()) {
                EmptyBox(
                    title = "No projects yet",
                    subtitle = "Tap + to create your first analytics project.",
                )
            } else {
                LazyColumn(Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item {
                        Text("Recent Projects", style = MaterialTheme.typography.titleLarge,
                             fontWeight = FontWeight.Bold)
                    }
                    items(state.projects, key = { it.id }) { project ->
                        ProjectCard(project, onClick = { nav.navigate(Routes.project(project.id)) })
                    }
                }
            }
        }
    }
}

@Composable
private fun ProjectCard(project: Project, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth(),
         colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            Text(project.name, style = MaterialTheme.typography.titleMedium,
                 fontWeight = FontWeight.SemiBold,
                 color = MaterialTheme.colorScheme.onSurface)
            Text(project.description.ifBlank { "No description" },
                 style = MaterialTheme.typography.bodySmall,
                 color = MaterialTheme.colorScheme.onSurfaceVariant,
                 maxLines = 2)
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                StatusChip(
                    label = if (project.hasRun) "Analyzed" else "New",
                    color = if (project.hasRun) MaterialTheme.colorScheme.primary else Color(0xFF6B7280),
                )
                Spacer(Modifier.size(8.dp))
                Text(
                    if (project.hasRun) "Last analyzed: ${Formatters.formatDate(project.lastRunAt)}"
                    else "No analysis yet",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}