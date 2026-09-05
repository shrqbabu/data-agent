package com.analyticsagent.navigation

import androidx.navigation.NavType
import androidx.navigation.navArgument

/** App navigation graph. */
object Routes {
    const val LOGIN = "login"
    const val PROJECTS = "projects"
    const val NEW_PROJECT = "new-project"
    const val PROJECT = "project/{projectId}"
    const val QUALITY = "project/{projectId}/dataset/{datasetId}/quality"
    const val PROMPT = "project/{projectId}/report-prompt"
    const val RUN_PROGRESS = "project/{projectId}/run/{runId}/progress"
    const val RUN_RESULTS = "project/{projectId}/run/{runId}/results"
    const val DAX = "project/{projectId}/run/{runId}/dax"
    const val DASHBOARD = "project/{projectId}/run/{runId}/dashboard"
    const val STAR_SCHEMA = "project/{projectId}/run/{runId}/schema"
    const val EXCEL_FORMULAS = "project/{projectId}/run/{runId}/excel"
    const val SQL_QUERIES = "project/{projectId}/run/{runId}/sql"
    const val SETTINGS = "project/{projectId}/settings"

    fun project(id: String) = "project/$id"
    fun quality(projectId: String, datasetId: String) = "project/$projectId/dataset/$datasetId/quality"
    fun prompt(projectId: String) = "project/$projectId/report-prompt"
    fun runProgress(projectId: String, runId: String) = "project/$projectId/run/$runId/progress"
    fun runResults(projectId: String, runId: String) = "project/$projectId/run/$runId/results"
    fun dax(projectId: String, runId: String) = "project/$projectId/run/$runId/dax"
    fun dashboard(projectId: String, runId: String) = "project/$projectId/run/$runId/dashboard"
    fun starSchema(projectId: String, runId: String) = "project/$projectId/run/$runId/schema"
    fun excelFormulas(projectId: String, runId: String) = "project/$projectId/run/$runId/excel"
    fun sqlQueries(projectId: String, runId: String) = "project/$projectId/run/$runId/sql"
    fun settings(projectId: String) = "project/$projectId/settings"
}

object ProjectArgs {
    val projectId = navArgument("projectId") { type = NavType.StringType }
    val datasetId = navArgument("datasetId") { type = NavType.StringType }
    val runId = navArgument("runId") { type = NavType.StringType }
}
