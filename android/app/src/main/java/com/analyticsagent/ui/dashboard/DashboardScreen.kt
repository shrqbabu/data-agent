package com.analyticsagent.ui.dashboard

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.analyticsagent.AppContainer
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.VmFactory

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(container: AppContainer, nav: NavController, projectId: String, runId: String) {
    val vm: DashboardViewModel = viewModel(factory = VmFactory.from {
        DashboardViewModel(container.analysisRepository, container.artifactRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(runId) { vm.load(runId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dashboard") },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingBox("Loading dashboard…")
            state.error != null -> ErrorBox(state.error!!)
            else -> Column(
                Modifier.fillMaxSize().padding(padding)
                    .verticalScroll(rememberScrollState()).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Dashboard PNG", style = MaterialTheme.typography.titleLarge,
                     fontWeight = FontWeight.Bold)
                Text("Generated from validated metric registry values. "
                    + "Every number on this dashboard is reconciled with the analysis report and DAX.",
                     style = MaterialTheme.typography.bodyMedium,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)

                state.imageUrl?.let { url ->
                    AsyncImage(
                        model = url,
                        contentDescription = "Dashboard PNG",
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = {
                        state.fullUrl?.let { url ->
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                            context.startActivity(intent)
                        }
                    },
                    enabled = state.fullUrl != null,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Download PNG")
                }
            }
        }
    }
}
