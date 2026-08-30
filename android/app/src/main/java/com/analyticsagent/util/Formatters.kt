package com.analyticsagent.util

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

object Formatters {
    private val dateFmt: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy")
    private val dateTimeFmt: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy HH:mm")

    fun formatDate(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        return runCatching {
            Instant.parse(iso).atZone(ZoneId.systemDefault()).format(dateFmt)
        }.getOrDefault(iso)
    }

    fun formatDateTime(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        return runCatching {
            Instant.parse(iso).atZone(ZoneId.systemDefault()).format(dateTimeFmt)
        }.getOrDefault(iso)
    }

    fun humanReadableStage(stage: String): String = when (stage) {
        "queued" -> "Queued"
        "VALIDATING_INPUT" -> "Validating input"
        "PROFILING" -> "Profiling dataset"
        "DATA_QUALITY" -> "Checking data quality"
        "SCHEMA_MODELING" -> "Building schema model"
        "ANALYSIS_PLANNING" -> "Planning analysis"
        "DETERMINISTIC_CALCULATIONS" -> "Computing metrics"
        "BUSINESS_ANALYSIS" -> "Running business analysis"
        "STATISTICS" -> "Statistical analysis"
        "FORECASTING_IF_SUPPORTED" -> "Forecasting"
        "INSIGHT_GENERATION" -> "Generating insights"
        "DAX_GENERATION" -> "Generating DAX"
        "DAX_VALIDATION" -> "Validating DAX"
        "DASHBOARD_PNG_GENERATION" -> "Rendering dashboard"
        "FINAL_VALIDATION" -> "Final validation"
        "COMPLETED" -> "Completed"
        "VALIDATION_FAILED" -> "Validation failed"
        else -> stage.replace("_", " ").lowercase().replaceFirstChar { it.uppercase() }
    }

    fun statusLabel(status: String): String = when (status) {
        "queued" -> "Queued"
        "running" -> "Running"
        "completed" -> "Completed"
        "failed" -> "Failed"
        "cancelled" -> "Cancelled"
        "validation_failed" -> "Validation failed"
        else -> status
    }
}