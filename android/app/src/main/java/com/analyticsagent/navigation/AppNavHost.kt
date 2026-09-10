package com.analyticsagent.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.analyticsagent.AppContainer
import com.analyticsagent.ui.dashboard.DashboardScreen
import com.analyticsagent.ui.dataset.DatasetScreen
import com.analyticsagent.ui.dax.DaxScreen
import com.analyticsagent.ui.excel.ExcelFormulaScreen
import com.analyticsagent.ui.newproject.NewProjectScreen
import com.analyticsagent.ui.progress.AnalysisProgressScreen
import com.analyticsagent.ui.projects.ProjectsScreen
import com.analyticsagent.ui.prompt.PromptLibraryScreen
import com.analyticsagent.ui.prompt.ReportPromptScreen
import com.analyticsagent.ui.quality.DataQualityScreen
import com.analyticsagent.ui.results.ResultsScreen
import com.analyticsagent.ui.schema.StarSchemaScreen
import com.analyticsagent.ui.settings.ProjectSettingsScreen
import com.analyticsagent.ui.sql.SqlScreen

@Composable
fun AppNavHost(container: AppContainer) {
    val nav = rememberNavController()

    NavHost(navController = nav, startDestination = Routes.PROJECTS) {
        composable(Routes.PROJECTS) {
            ProjectsScreen(container, nav)
        }
        composable(Routes.NEW_PROJECT) {
            NewProjectScreen(container, nav)
        }
        composable(Routes.PROJECT, arguments = listOf(ProjectArgs.projectId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            DatasetScreen(container, nav, projectId)
        }
        composable(Routes.QUALITY, arguments = listOf(ProjectArgs.projectId, ProjectArgs.datasetId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            val datasetId = entry.arguments?.getString("datasetId").orEmpty()
            DataQualityScreen(container, nav, projectId, datasetId)
        }
        composable(Routes.PROMPT, arguments = listOf(ProjectArgs.projectId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            ReportPromptScreen(container, nav, projectId)
        }
        composable(Routes.RUN_PROGRESS, arguments = listOf(ProjectArgs.projectId, ProjectArgs.runId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            val runId = entry.arguments?.getString("runId").orEmpty()
            AnalysisProgressScreen(container, nav, projectId, runId)
        }
        composable(Routes.RUN_RESULTS, arguments = listOf(ProjectArgs.projectId, ProjectArgs.runId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            val runId = entry.arguments?.getString("runId").orEmpty()
            ResultsScreen(container, nav, projectId, runId)
        }
        composable(Routes.DAX, arguments = listOf(ProjectArgs.projectId, ProjectArgs.runId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            val runId = entry.arguments?.getString("runId").orEmpty()
            DaxScreen(container, nav, projectId, runId)
        }
        composable(Routes.DASHBOARD, arguments = listOf(ProjectArgs.projectId, ProjectArgs.runId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            val runId = entry.arguments?.getString("runId").orEmpty()
            DashboardScreen(container, nav, projectId, runId)
        }
        composable(Routes.PROMPT_LIBRARY) {
            PromptLibraryScreen(
                onPromptSelected = { prompt, mode ->
                    nav.previousBackStackEntry?.savedStateHandle?.set("selected_prompt", prompt)
                    nav.previousBackStackEntry?.savedStateHandle?.set("selected_mode", mode.name)
                    nav.popBackStack()
                },
                onBack = { nav.popBackStack() }
            )
        }
        composable(Routes.SETTINGS, arguments = listOf(ProjectArgs.projectId)) { entry ->
            val projectId = entry.arguments?.getString("projectId").orEmpty()
            ProjectSettingsScreen(container, nav, projectId)
        }
    }
}
