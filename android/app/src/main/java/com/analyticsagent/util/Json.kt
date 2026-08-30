package com.analyticsagent.util

import kotlin.math.abs
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** Helpers to extract values from JSON payloads for display. */
object JsonFormat {
    fun asText(e: JsonElement?): String = when (e) {
        null -> ""
        is JsonPrimitive -> e.contentOrNull ?: ""
        is JsonObject -> e.toString()
        is JsonArray -> e.toString()
        else -> e.toString()
    }

    fun asPrimitiveValue(e: JsonElement?): Any? = when (e) {
        null -> null
        is JsonPrimitive -> when {
            e.isString -> e.content
            e.content == "true" -> true
            e.content == "false" -> false
            else -> e.content
        }
        else -> null
    }

    /** Best-effort human display for a metric value object from the backend registry. */
    fun metricDisplay(value: JsonElement?): String {
        if (value == null) return "—"
        if (value is JsonPrimitive) return value.content
        if (value is JsonObject) {
            val reason = value["reason"]
            if (reason != null) {
                return "Not supported: ${asText(reason)}"
            }
            val v = value["value"]
            val unit = asText(value["unit"])
            val number = jsonNumber(v)
            if (number != null) return compact(number, unit)
            val text = asText(v)
            return text.ifBlank { value.toString() }
        }
        return value.toString()
    }

    fun jsonNumber(e: JsonElement?): Double? =
        (e as? JsonPrimitive)?.content?.toDoubleOrNull()

    fun compact(v: Double, unit: String = ""): String {
        val a = abs(v)
        val s = when {
            a >= 1_000_000_000 -> if (v == 0.0) "0" else "%.2fB".format(v / 1_000_000_000)
            a >= 1_000_000 -> "%.2fM".format(v / 1_000_000)
            a >= 1_000 -> "%.1fK".format(v / 1_000)
            else -> "%.2f".format(v)
        }
        return if (unit.isBlank()) s else "$s $unit"
    }

    /** Dictionaries from a JSON array element, for chart/table rendering. */
    fun listOfObjects(e: JsonElement?): List<JsonObject> = when (e) {
        is JsonArray -> e.mapNotNull { it as? JsonObject }
        else -> emptyList()
    }

    fun textOf(e: JsonElement?, key: String): String {
        val o = e as? JsonObject ?: return ""
        return asText(o[key])
    }

    fun number(e: JsonElement?, key: String): Double? {
        val o = e as? JsonObject ?: return null
        return jsonNumber(o[key])
    }

    fun long(e: JsonElement?, key: String): Long? {
        val o = e as? JsonObject ?: return null
        val v = (o[key] as? JsonPrimitive)?.content ?: return null
        return v.toLongOrNull()
    }

    /** Nested object value, e.g. obj(profile, "quality"). */
    fun obj(e: JsonElement?, key: String): JsonObject? {
        return (e as? JsonObject)?.get(key) as? JsonObject
    }
}