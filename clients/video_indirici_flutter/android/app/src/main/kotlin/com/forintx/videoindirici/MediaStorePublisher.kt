package com.forintx.videoindirici

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File

internal object MediaStorePublisher {
    private const val ROOT_DIRECTORY = "video_indirici"

    fun relativeDirectory(kind: String): String =
        "${Environment.DIRECTORY_DOWNLOADS}/$ROOT_DIRECTORY/${if (kind == "audio") "musics" else "videos"}"

    @Suppress("DEPRECATION")
    fun absoluteDirectory(kind: String): String =
        File(Environment.getExternalStorageDirectory(), relativeDirectory(kind)).absolutePath

    fun ensureDirectory(context: Context, kind: String) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            File(absoluteDirectory(kind)).mkdirs()
            return
        }
        val resolver = context.contentResolver
        val collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        val relativePath = "${relativeDirectory(kind).trimEnd('/')}/"
        val markerName = ".video_indirici"
        val exists = resolver.query(
            collection,
            arrayOf(MediaStore.MediaColumns._ID),
            "${MediaStore.MediaColumns.DISPLAY_NAME} = ? AND ${MediaStore.MediaColumns.RELATIVE_PATH} = ?",
            arrayOf(markerName, relativePath),
            null,
        )?.use { it.moveToFirst() } ?: false
        if (exists) return
        resolver.insert(
            collection,
            ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, markerName)
                put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream")
                put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
                put(MediaStore.MediaColumns.IS_PENDING, 0)
            },
        ) ?: error("İndirme klasörü oluşturulamadı")
    }

    fun publish(context: Context, source: File, displayName: String, kind: String): Uri {
        val audio = kind == "audio"
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else if (audio) {
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }
        val mime = when (source.extension.lowercase()) {
            "mp3" -> "audio/mpeg"
            "m4a" -> "audio/mp4"
            "opus" -> "audio/opus"
            else -> "video/mp4"
        }
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
            put(MediaStore.MediaColumns.MIME_TYPE, mime)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.MediaColumns.RELATIVE_PATH, "${relativeDirectory(kind).trimEnd('/')}/")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            } else {
                @Suppress("DEPRECATION")
                val directory = File(absoluteDirectory(kind)).apply { mkdirs() }
                @Suppress("DEPRECATION")
                put(MediaStore.MediaColumns.DATA, File(directory, displayName).absolutePath)
            }
        }
        val resolver = context.contentResolver
        val uri = resolver.insert(collection, values) ?: error("MediaStore kaydı oluşturulamadı")
        try {
            resolver.openOutputStream(uri, "w")!!.use { output -> source.inputStream().use { it.copyTo(output) } }
            values.clear()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.put(MediaStore.MediaColumns.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            }
            return uri
        } catch (error: Throwable) {
            resolver.delete(uri, null, null)
            throw error
        }
    }

    fun exists(context: Context, value: String): Boolean {
        val uri = Uri.parse(value)
        if (uri.scheme == "content") {
            return try {
                context.contentResolver.query(uri, arrayOf(MediaStore.MediaColumns._ID), null, null, null)?.use { it.moveToFirst() } ?: false
            } catch (_: Throwable) {
                false
            }
        }
        return File(value).exists()
    }

    fun parentRelativePath(context: Context, value: String): String? {
        val uri = Uri.parse(value)
        if (uri.scheme == "content") {
            return try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    context.contentResolver.query(
                        uri,
                        arrayOf(MediaStore.MediaColumns.RELATIVE_PATH),
                        null,
                        null,
                        null,
                    )?.use { cursor ->
                        if (!cursor.moveToFirst()) return@use null
                        cursor.getString(0)?.trim('/')
                    }
                } else {
                    @Suppress("DEPRECATION")
                    context.contentResolver.query(
                        uri,
                        arrayOf(MediaStore.MediaColumns.DATA),
                        null,
                        null,
                        null,
                    )?.use { cursor ->
                        if (!cursor.moveToFirst()) return@use null
                        relativeParent(cursor.getString(0))
                    }
                }
            } catch (_: Throwable) {
                null
            }
        }
        val path = if (uri.scheme == "file") uri.path else value
        return relativeParent(path)
    }

    @Suppress("DEPRECATION")
    private fun relativeParent(path: String?): String? {
        if (path.isNullOrBlank()) return null
        val parent = File(path).parentFile ?: return null
        val root = Environment.getExternalStorageDirectory().absolutePath.trimEnd('/')
        val absolute = parent.absolutePath
        if (!absolute.startsWith("$root/")) return null
        return absolute.removePrefix("$root/").trim('/')
    }
}
