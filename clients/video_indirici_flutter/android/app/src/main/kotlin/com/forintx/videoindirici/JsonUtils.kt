package com.forintx.videoindirici

import org.json.JSONArray
import org.json.JSONObject

internal fun JSONObject.toFlutterMap(): Map<String, Any?> = keys().asSequence().associateWith { key ->
    when (val value = get(key)) {
        JSONObject.NULL -> null
        is JSONObject -> value.toFlutterMap()
        is JSONArray -> value.toFlutterList()
        else -> value
    }
}
internal fun JSONArray.toFlutterList(): List<Any?> = (0 until length()).map { index ->
    when (val value = get(index)) {
        JSONObject.NULL -> null
        is JSONObject -> value.toFlutterMap()
        is JSONArray -> value.toFlutterList()
        else -> value
    }
}

internal fun Map<*, *>.toJsonObject(): JSONObject {
    val result = JSONObject()
    for ((key, value) in this) {
        if (key != null) result.put(key.toString(), value)
    }
    return result
}
