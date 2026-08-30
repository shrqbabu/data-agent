package com.analyticsagent.util

/** Simplified result wrapper for repository returns. */
sealed interface AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>
    data class Error(val error: AppError) : AppResult<Nothing>
}

data class AppError(
    val code: String = "UNKNOWN",
    val message: String,
    val userMessage: String = message,
) {
    companion object {
        fun from(e: Throwable): AppError {
            val msg = e.message ?: "Something went wrong."
            val cleaned = msg.replaceFirstChar { it.uppercase() }
            val code = when {
                msg.contains("401") || msg.contains("expired") || msg.contains("session") -> "AUTH_EXPIRED"
                msg.contains("403") -> "FORBIDDEN"
                msg.contains("404") -> "NOT_FOUND"
                msg.contains("timeout", ignoreCase = true) -> "TIMEOUT"
                msg.contains("connect", ignoreCase = true) -> "NETWORK"
                else -> "UNKNOWN"
            }
            return AppError(
                code = code,
                message = msg,
                userMessage = if (code == "AUTH_EXPIRED") {
                    "Your session has expired. Please sign in again."
                } else msg,
            )
        }
    }
}

fun <T> AppResult<T>.getOrNull(): T? = (this as? AppResult.Success)?.data

fun <T> AppResult<T>.getOrDefault(default: T): T = (this as? AppResult.Success)?.data ?: default