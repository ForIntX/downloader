package com.forintx.videoindirici

import android.app.NotificationManager
import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.annotation.Keep
import com.arthenica.ffmpegkit.FFmpegKit
import com.arthenica.ffmpegkit.ReturnCode
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

internal object EngineRuntime {
    private lateinit var appContext: Context
    private val executor = Executors.newFixedThreadPool(3)
    private val mainHandler = Handler(Looper.getMainLooper())
    private val stopReasons = ConcurrentHashMap<String, String>()
    private val running = ConcurrentHashMap.newKeySet<String>()
    private var eventListener: ((Map<String, Any?>) -> Unit)? = null
    private val pendingEvents = ConcurrentHashMap<String, Map<String, Any?>>()
    private val batchCompleted = AtomicInteger(0)
    private val batchFailed = AtomicInteger(0)
    @Volatile private var pythonConfigured = false

    fun initialize(context: Context) {
        appContext = context.applicationContext
        executor.execute {
            try {
                downloaderModule()
            } catch (_: Throwable) {
                // İlk gerçek istekte ayrıntılı hata kullanıcıya aktarılır.
            }
        }
    }

    @Synchronized
    fun downloaderModule(): PyObject {
        if (!Python.isStarted()) Python.start(AndroidPlatform(appContext))
        val module = Python.getInstance().getModule("downloader_bridge")
        if (!pythonConfigured) {
            val qjs = File(appContext.applicationInfo.nativeLibraryDir, "libqjs.so")
            module.callAttr("set_qjs_path", qjs.takeIf { it.canExecute() }?.absolutePath)
            pythonConfigured = true
        }
        return module
    }

    @Synchronized
    fun setEventListener(listener: ((Map<String, Any?>) -> Unit)?) {
        eventListener = listener
        if (listener != null) {
            val events = pendingEvents.values.toList()
            pendingEvents.clear()
            events.forEach(listener)
        }
    }

    fun requestStop(jobId: String, paused: Boolean) {
        stopReasons[jobId] = if (paused) "paused" else "cancelled"
    }

    fun isRunning(jobId: String): Boolean = running.contains(jobId)

    fun hasStopRequest(jobId: String): Boolean = stopReasons.containsKey(jobId)

    fun activeJobCount(): Int = running.size

    fun run(jobJson: String, finished: (Boolean) -> Unit) {
        val job = JSONObject(jobJson)
        val jobId = job.getString("id")
        if (!running.add(jobId)) {
            finished(false)
            return
        }
        stopReasons.remove(jobId)
        emit(jobId, "preparing", progress = 0.0)
        executor.execute {
            var success = false
            try {
                val callback = PythonDownloadCallback(jobId, job.optString("title", "Video"))
                val module = downloaderModule()
                val responseJson = module.callAttr(
                    "download_job_json",
                    jobJson,
                    File(appContext.cacheDir, "download_engine").absolutePath,
                    PyObject.fromJava(callback),
                ).toString()
                if (stopReasons.containsKey(jobId)) throw InterruptedException("Kullanıcı tarafından durduruldu")
                emit(jobId, "processing", progress = 100.0)
                val result = JSONObject(responseJson)
                val processed = process(job, result)
                if (stopReasons.containsKey(jobId)) throw InterruptedException("Kullanıcı tarafından durduruldu")
                val displayName = renderDisplayName(job, processed.extension)
                val uri = MediaStorePublisher.publish(appContext, processed.file, displayName, result.getString("kind"))
                emit(jobId, "completed", progress = 100.0, outputPath = uri.toString())
                processed.file.delete()
                success = true
                batchCompleted.incrementAndGet()
            } catch (error: Throwable) {
                val reason = stopReasons.remove(jobId)
                if (reason != null) {
                    emit(jobId, reason)
                } else {
                    emit(jobId, "failed", error = friendlyError(error))
                    batchFailed.incrementAndGet()
                }
            } finally {
                running.remove(jobId)
                appContext.getSystemService(NotificationManager::class.java).cancel(jobId.hashCode())
                finished(success)
                notifyBatchIfDone()
            }
        }
    }

    private data class ProcessedFile(val file: File, val extension: String)

    private fun process(job: JSONObject, result: JSONObject): ProcessedFile {
        val components = result.getJSONArray("components")
        val extension = result.getString("extension")
        val source = File(components.getString(0))
        if (result.getString("kind") == "video" && components.length() == 1 && source.extension.equals("mp4", true)) {
            return ProcessedFile(source, "mp4")
        }
        val output = File(source.parentFile, "final.$extension")
        if (output.exists()) output.delete()
        val arguments = when (result.getString("kind")) {
            "video" -> if (components.length() == 1) {
                arrayOf(
                    "-y", "-i", source.absolutePath, "-map", "0:v:0", "-map", "0:a:0?",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    output.absolutePath,
                )
            } else {
                arrayOf(
                    "-y", "-i", source.absolutePath, "-i", components.getString(1),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", output.absolutePath,
                )
            }
            else -> when (extension) {
                "mp3" -> arrayOf(
                    "-y", "-i", source.absolutePath, "-vn", "-c:a", "libmp3lame",
                    "-b:a", "${result.optInt("bitrate", 192)}k", output.absolutePath,
                )
                "opus" -> arrayOf("-y", "-i", source.absolutePath, "-vn", "-c:a", "libopus", "-b:a", "160k", output.absolutePath)
                else -> arrayOf("-y", "-i", source.absolutePath, "-vn", "-c:a", "aac", "-b:a", "192k", output.absolutePath)
            }
        }
        val session = FFmpegKit.executeWithArguments(arguments)
        if (!ReturnCode.isSuccess(session.returnCode)) {
            throw IllegalStateException(session.allLogsAsString.ifBlank { "FFmpeg işlemi başarısız" })
        }
        for (index in 0 until components.length()) File(components.getString(index)).delete()
        if (!output.exists()) error("Dönüştürülen dosya bulunamadı")
        return ProcessedFile(output, extension)
    }

    private fun emit(
        jobId: String,
        status: String,
        progress: Double? = null,
        speed: String? = null,
        eta: Int? = null,
        outputPath: String? = null,
        error: String? = null,
    ) {
        val event = mutableMapOf<String, Any?>("job_id" to jobId, "status" to status)
        if (progress != null) event["progress"] = progress
        if (!speed.isNullOrBlank()) event["speed"] = speed
        if (eta != null && eta >= 0) event["eta_seconds"] = eta
        if (outputPath != null) event["output_path"] = outputPath
        if (error != null) event["error"] = error
        mainHandler.post {
            val listener = eventListener
            if (listener == null) pendingEvents[jobId] = event else listener(event)
        }
    }

    private fun notifyBatchIfDone() {
        if (running.isNotEmpty()) return
        val completed = batchCompleted.getAndSet(0)
        val failed = batchFailed.getAndSet(0)
        if (completed + failed == 0) return
        val message = "$completed tamamlandı, $failed hata"
        val notification = DownloadNotifications.result(appContext, message, failed == 0)
        appContext.getSystemService(NotificationManager::class.java).notify(30_001, notification)
    }

    private fun safeName(value: String): String = value
        .replace(Regex("[\\\\/:*?\"<>|]"), "_")
        .trim()
        .take(160)
        .ifBlank { "video" }

    private fun renderDisplayName(job: JSONObject, extension: String): String {
        val title = job.optString("title", "video")
        val sourceId = job.optString("source_id", job.optString("id", ""))
        var rendered = job.optString("filename_template", "%(title)s.%(ext)s")
        rendered = Regex("""%\(title\)\.(\d+)B""").replace(rendered) { match ->
            title.take(match.groupValues[1].toIntOrNull()?.coerceIn(1, 180) ?: 180)
        }
        rendered = rendered
            .replace("%(title)s", title)
            .replace("%(id)s", sourceId)
            .replace("%(ext)s", extension)
        rendered = Regex("""%\([^)]+\)[^ ]*""").replace(rendered, "_")
        val safe = safeName(rendered.substringAfterLast('/').substringAfterLast('\\'))
        return if (safe.endsWith(".$extension", ignoreCase = true)) {
            safe
        } else {
            "${safe.take(150)}.$extension"
        }
    }

    private fun friendlyError(error: Throwable): String {
        val message = generateSequence(error) { it.cause }.mapNotNull { it.message }.lastOrNull()
        return message?.take(4000) ?: error.javaClass.simpleName
    }

    @Keep
    private class PythonDownloadCallback(private val jobId: String, private val title: String) {
        @Suppress("unused")
        fun isCancelled(): Boolean = stopReasons.containsKey(jobId)

        @Suppress("unused")
        fun onProgress(percent: Double, speed: String, etaSeconds: Int) {
            emit(jobId, "downloading", percent.coerceIn(0.0, 100.0), speed, etaSeconds)
            val notification = DownloadNotifications.progress(appContext, jobId, title, percent.toInt())
            appContext.getSystemService(NotificationManager::class.java).notify(jobId.hashCode(), notification)
        }
    }
}
