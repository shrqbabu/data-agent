package com.analyticsagent.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/** DTOs mirror the analytics backend REST contract (see backend/app/api). */

@Serializable
enum class AnalysisMode {
    @SerialName("excel") EXCEL,
    @SerialName("powerbi") POWER_BI,
    @SerialName("sql") SQL
}

@Serializable
data class MeResponse(
    val id: String = "",
    val email: String = "",
    val role: String = "",
)

@Serializable
data class Project(
    val id: String,
    val ownerId: String? = null,
    val name: String,
    val description: String = "",
    val status: String = "active",
    val createdAt: String? = null,
    val updatedAt: String? = null,
    val lastRunAt: String? = null,
) {
    val hasRun: Boolean get() = !lastRunAt.isNullOrBlank()
}

@Serializable
data class ColumnInfo(
    val name: String,
    val kind: String = "unknown",
    val dtype: String = "",
    val missing: Long = 0,
    @SerialName("missing_pct") val missingPct: Double = 0.0,
    val unique: Long = 0,
    val sample: List<JsonElement?> = emptyList(),
)

@Serializable
data class Profile(
    @SerialName("row_count") val rowCount: Long = 0,
    @SerialName("column_count") val columnCount: Int = 0,
    val columns: List<ColumnInfo> = emptyList(),
    @SerialName("date_columns") val dateColumns: List<String> = emptyList(),
    @SerialName("numeric_columns") val numericColumns: List<String> = emptyList(),
    @SerialName("categorical_columns") val categoricalColumns: List<String> = emptyList(),
    @SerialName("duplicate_rows") val duplicateRows: Long = 0,
    @SerialName("date_range") val dateRange: JsonElement? = null,
    val tables: Int = 1,
    val quality: Quality? = null,
)

@Serializable
data class DatasetTable(
    val id: String,
    @SerialName("dataset_id") val datasetId: String,
    @SerialName("table_name") val tableName: String,
    val grain: String? = null,
    @SerialName("row_count") val rowCount: Long = 0,
    val schema: JsonElement? = null,
)

@Serializable
data class Dataset(
    val id: String,
    @SerialName("project_id") val projectId: String,
    val name: String,
    @SerialName("source_type") val sourceType: String = "csv",
    @SerialName("storage_path") val storagePath: String? = null,
    @SerialName("file_size") val fileSize: Long = 0,
    @SerialName("mime_type") val mimeType: String? = null,
    @SerialName("row_count") val rowCount: Long = 0,
    @SerialName("column_count") val columnCount: Int = 0,
    val schema: JsonElement? = null,
    val profile: JsonElement? = null,
    @SerialName("created_at") val createdAt: String? = null,
    val tables: List<DatasetTable> = emptyList(),
) {
    val displaySizeKb: String
        get() = if (fileSize > 0) "%.1f KB".format(fileSize / 1024.0) else ""
    val sourceLabel: String
        get() = when (sourceType) {
            "csv" -> "CSV"
            "excel" -> "Excel"
            "sql" -> "SQL"
            else -> sourceType
        }
}

@Serializable
data class Run(
    val id: String,
    @SerialName("project_id") val projectId: String,
    val status: String = "queued",
    val stage: String = "queued",
    val progress: Int = 0,
    @SerialName("user_prompt") val userPrompt: String = "",
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("completed_at") val completedAt: String? = null,
    val error: JsonElement? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("job_started") val jobStarted: Boolean? = null,
) {
    val isRunning: Boolean get() = status in setOf("queued", "running")
    val isDone: Boolean get() = status in setOf("completed", "failed", "cancelled", "validation_failed")
    val isSuccess: Boolean get() = status == "completed"
}

@Serializable
data class Metric(
    val id: String? = null,
    @SerialName("analysis_run_id") val analysisRunId: String? = null,
    @SerialName("metric_id") val metricId: String,
    val name: String,
    val definition: String = "",
    val formula: String = "",
    val value: JsonElement? = null,
    val source: JsonElement? = null,
    @SerialName("validation_status") val validationStatus: String = "unvalidated",
) {
    val isNotSupported: Boolean get() = validationStatus == "NOT_SUPPORTED"
    val isFailed: Boolean get() = validationStatus == "failed"
}

@Serializable
data class Insight(
    val id: String? = null,
    val title: String,
    val finding: String,
    val evidence: JsonElement? = null,
    val interpretation: String? = null,
    @SerialName("business_impact") val businessImpact: String? = null,
    val recommendation: String? = null,
    val confidence: String = "medium",
    val priority: String = "medium",
)

@Serializable
data class DaxMeasure(
    val id: String? = null,
    val name: String,
    @SerialName("dax_code") val daxCode: String,
    val purpose: String? = null,
    val dependencies: JsonElement? = null,
    @SerialName("validation_status") val validationStatus: String = "unvalidated",
) {
    val isOk: Boolean get() = validationStatus != "failed"
}

@Serializable
data class ExcelFormula(
    val name: String,
    val category: String = "Dynamic Array",
    val formula: String,
    @SerialName("target_range") val targetRange: String = "",
    val explanation: String = "",
    @SerialName("example_output") val exampleOutput: String = "",
    @SerialName("m_code") val mCode: String? = null,
    @SerialName("vba_code") val vbaCode: String? = null,
)

@Serializable
data class SqlQuery(
    val title: String,
    @SerialName("query_type") val queryType: String = "Query",
    val dialect: String = "PostgreSQL",
    @SerialName("sql_code") val sqlCode: String,
    val explanation: String = "",
    @SerialName("expected_columns") val expectedColumns: List<String> = emptyList(),
    @SerialName("indexing_suggestion") val indexingSuggestion: String? = null,
)

@Serializable
data class StarTable(
    val name: String,
    val type: String,
    @SerialName("primary_key") val primaryKey: String? = null,
    val columns: List<String> = emptyList(),
    val description: String = "",
)

@Serializable
data class StarRelationship(
    @SerialName("from_table") val fromTable: String,
    @SerialName("from_column") val fromColumn: String,
    @SerialName("to_table") val toTable: String,
    @SerialName("to_column") val toColumn: String,
    val cardinality: String = "1:N",
    @SerialName("cross_filter_direction") val crossFilterDirection: String = "Single",
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class StarSchemaModel(
    @SerialName("model_name") val modelName: String = "Star Schema",
    @SerialName("fact_tables") val factTables: List<StarTable> = emptyList(),
    @SerialName("dimension_tables") val dimensionTables: List<StarTable> = emptyList(),
    val relationships: List<StarRelationship> = emptyList(),
    @SerialName("date_table_dax") val dateTableDax: String? = null,
    @SerialName("modeling_recommendations") val modelingRecommendations: List<String> = emptyList(),
)

@Serializable
data class Quality(
    val id: String? = null,
    val score: Double = 0.0,
    val completeness: JsonElement? = null,
    val validity: JsonElement? = null,
    val consistency: JsonElement? = null,
    val uniqueness: JsonElement? = null,
    val relationships: JsonElement? = null,
    val issues: JsonElement? = null,
) {
    val scoreLabel: String get() = if (score >= 0) "%.0f%%".format(score) else "—"
}

@Serializable
data class Artifact(
    val id: String,
    val projectId: String? = null,
    @SerialName("analysis_run_id") val analysisRunId: String? = null,
    @SerialName("artifact_type") val artifactType: String,
    @SerialName("storage_path") val storagePath: String,
    @SerialName("file_name") val fileName: String,
    @SerialName("mime_type") val mimeType: String? = null,
    @SerialName("file_size") val fileSize: Long = 0,
    val checksum: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
) {
    val typeLabel: String
        get() = when (artifactType) {
            "report" -> "Analysis Report"
            "dashboard_png" -> "Dashboard PNG"
            "dax_file" -> "DAX Measures"
            "data_quality" -> "Data Quality Report"
            else -> artifactType
        }
}

@Serializable
data class RunDetail(
    val id: String,
    @SerialName("project_id") val projectId: String,
    val status: String = "queued",
    val stage: String = "queued",
    val progress: Int = 0,
    @SerialName("user_prompt") val userPrompt: String = "",
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("completed_at") val completedAt: String? = null,
    val error: JsonElement? = null,
    @SerialName("created_at") val createdAt: String? = null,
    val metrics: List<Metric> = emptyList(),
    val insights: List<Insight> = emptyList(),
    @SerialName("dax_measures") val daxMeasures: List<DaxMeasure> = emptyList(),
    @SerialName("excel_formulas") val excelFormulas: List<ExcelFormula> = emptyList(),
    @SerialName("sql_queries") val sqlQueries: List<SqlQuery> = emptyList(),
    @SerialName("star_schema") val starSchema: StarSchemaModel? = null,
    @SerialName("data_quality") val dataQuality: Quality? = null,
    val artifacts: List<Artifact> = emptyList(),
) {
    val dashboardArtifact: Artifact? get() = artifacts.firstOrNull { it.artifactType == "dashboard_png" }
    val reportArtifact: Artifact? get() = artifacts.firstOrNull { it.artifactType == "report" }
    val daxArtifact: Artifact? get() = artifacts.firstOrNull { it.artifactType == "dax_file" }
}

@Serializable
data class DirectAnalysisResponse(
    val ok: Boolean = true,
    @SerialName("run_id") val runId: String = "",
    val mode: String = "powerbi",
    @SerialName("file_name") val fileName: String = "",
    @SerialName("row_count") val rowCount: Int = 0,
    @SerialName("column_count") val columnCount: Int = 0,
    val columns: List<String> = emptyList(),
    @SerialName("quality_score") val qualityScore: Double = 95.0,
    @SerialName("executive_summary") val executiveSummary: String = "",
    @SerialName("key_findings") val keyFindings: List<String> = emptyList(),
    @SerialName("dashboard_image_base64") val dashboardImageBase64: String? = null,
    @SerialName("dax_measures") val daxMeasures: List<DaxMeasure> = emptyList(),
    @SerialName("star_schema") val starSchema: StarSchemaModel? = null,
    @SerialName("excel_formulas") val excelFormulas: List<ExcelFormula> = emptyList(),
    @SerialName("sql_queries") val sqlQueries: List<SqlQuery> = emptyList(),
    val recommendations: List<String> = emptyList(),
)
