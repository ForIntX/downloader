package com.forintx.videoindirici

import android.Manifest
import android.content.ClipData
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import androidx.core.app.ActivityCompat
import androidx.annotation.Keep
import com.chaquo.python.Python
import com.ryanheise.audioservice.AudioServiceActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

class MainActivity : AudioServiceActivity() {
    private val executor = Executors.newCachedThreadPool()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var eventSink: EventChannel.EventSink? = null
    private var shareSink: EventChannel.EventSink? = null
    private var playlistSink: EventChannel.EventSink? = null
    private var pendingSharedUrl: String? = null
    private val playlistGeneration = AtomicInteger(0)

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        requestNotificationPermission()
        requestLegacyStoragePermission()
        pendingSharedUrl = sharedText(intent)

        EventChannel(flutterEngine.dartExecutor.binaryMessenger, EVENTS).setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                eventSink = events
                EngineRuntime.setEventListener { event -> mainHandler.post { eventSink?.success(event) } }
            }

            override fun onCancel(arguments: Any?) {
                eventSink = null
                EngineRuntime.setEventListener(null)
            }
        })
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, SHARES).setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                shareSink = events
                pendingSharedUrl?.let { events?.success(it) }
                pendingSharedUrl = null
            }

            override fun onCancel(arguments: Any?) {
                shareSink = null
            }
        })
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, PLAYLIST).setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                playlistSink = events
            }

            override fun onCancel(arguments: Any?) {
                playlistSink = null
                playlistGeneration.incrementAndGet()
            }
        })

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, METHODS).setMethodCallHandler { call, result ->
            when (call.method) {
                "getVideoInfo" -> pythonResult(result) {
                    val url = call.argument<String>("url") ?: error("URL eksik")
                    val json = EngineRuntime.downloaderModule().callAttr("get_video_info_json", url).toString()
                    JSONObject(json).toFlutterMap()
                }
                "startPlaylistScan" -> {
                    val url = call.argument<String>("url") ?: run {
                        result.error("invalid_url", "URL eksik", null)
                        return@setMethodCallHandler
                    }
                    val generation = playlistGeneration.incrementAndGet()
                    result.success(null)
                    executor.execute {
                        try {
                            val callback = PlaylistScanCallback(generation)
                            EngineRuntime.downloaderModule().callAttr(
                                "scan_playlist", url, callback,
                            )
                            emitPlaylist(mapOf("kind" to "done"), generation)
                        } catch (error: Throwable) {
                            emitPlaylist(
                                mapOf("kind" to "error", "message" to (error.message ?: "Playlist taranamadı")),
                                generation,
                            )
                        }
                    }
                }
                "stopPlaylistScan" -> {
                    playlistGeneration.incrementAndGet()
                    result.success(null)
                }
                "startDownload", "resumeDownload" -> {
                    try {
                        val arguments = call.arguments as? Map<*, *> ?: error("Eksik iş bilgisi")
                        val json = arguments.toJsonObject().toString()
                        AndroidDownloadScheduler.start(this, json)
                        result.success(null)
                    } catch (error: Throwable) {
                        result.error("start_failed", error.message, error.stackTraceToString())
                    }
                }
                "pauseDownload" -> {
                    val jobId = call.argument<String>("job_id") ?: ""
                    EngineRuntime.requestStop(jobId, paused = true)
                    AndroidDownloadScheduler.cancel(this, jobId)
                    result.success(null)
                }
                "cancelDownload" -> {
                    val jobId = call.argument<String>("job_id") ?: ""
                    EngineRuntime.requestStop(jobId, paused = false)
                    AndroidDownloadScheduler.cancel(this, jobId)
                    result.success(null)
                }
                "setDownloadConstraints" -> {
                    AndroidDownloadScheduler.rescheduleWaiting(
                        this,
                        call.argument<Boolean>("wifi_only") ?: false,
                        call.argument<Boolean>("charging_only") ?: false,
                    )
                    result.success(null)
                }
                "outputExists" -> result.success(MediaStorePublisher.exists(this, call.argument<String>("path") ?: ""))
                "downloadLocations" -> result.success(
                    mapOf(
                        "video" to MediaStorePublisher.absoluteDirectory("video"),
                        "audio" to MediaStorePublisher.absoluteDirectory("audio"),
                    ),
                )
                "openDownloadLocation" -> intentResult(result) {
                    openDownloadFolder(call.argument<String>("kind") ?: "video")
                }
                "openOutputLocation" -> intentResult(result) {
                    val path = call.argument<String>("path") ?: error("Dosya yolu eksik")
                    if (!MediaStorePublisher.exists(this, path)) error("Dosya bulunamadı")
                    val relativePath = MediaStorePublisher.parentRelativePath(this, path)
                        ?: error("Dosyanın klasörü bulunamadı")
                    openRelativeFolder(relativePath)
                }
                "openOutput" -> intentResult(result) { openUri(call.argument<String>("path") ?: "", share = false) }
                "shareOutput" -> intentResult(result) { openUri(call.argument<String>("path") ?: "", share = true) }
                "diagnostics" -> pythonResult(result) {
                    EngineRuntime.downloaderModule()
                    val version = Python.getInstance().getModule("yt_dlp.version")
                        .get("__version__")?.toString()
                    val qjs = java.io.File(applicationInfo.nativeLibraryDir, "libqjs.so")
                    mapOf(
                        "platform" to "android",
                        "android_sdk" to Build.VERSION.SDK_INT,
                        "python" to "3.12",
                        "yt_dlp" to version,
                        "ejs" to "yt-dlp-ejs 0.4.0 (paketlenmiş)",
                        "quickjs" to if (qjs.canExecute()) "QuickJS-NG 0.15.0" else "bulunamadı",
                        "ffmpeg" to "FFmpegKit 8.1.7 LGPL",
                        "active_jobs" to EngineRuntime.activeJobCount(),
                    )
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        sharedText(intent)?.let { shareSink?.success(it) ?: run { pendingSharedUrl = it } }
    }

    override fun onDestroy() {
        if (isFinishing) EngineRuntime.setEventListener(null)
        super.onDestroy()
    }

    private fun pythonResult(result: MethodChannel.Result, block: () -> Any?) {
        executor.execute {
            try {
                val value = block()
                mainHandler.post { result.success(value) }
            } catch (error: Throwable) {
                mainHandler.post { result.error("engine_error", error.message ?: "Motor hatası", error.stackTraceToString()) }
            }
        }
    }

    private fun intentResult(result: MethodChannel.Result, block: () -> Unit) {
        try {
            block()
            result.success(null)
        } catch (error: Throwable) {
            result.error("intent_error", error.message, error.stackTraceToString())
        }
    }

    private fun emitPlaylist(value: Map<String, Any?>, generation: Int) {
        if (playlistGeneration.get() != generation) return
        mainHandler.post {
            if (playlistGeneration.get() == generation) playlistSink?.success(value)
        }
    }

    @Keep
    private inner class PlaylistScanCallback(private val generation: Int) {
        @Suppress("unused")
        fun isCancelled(): Boolean = playlistGeneration.get() != generation

        @Suppress("unused")
        fun onEntry(json: String) {
            emitPlaylist(
                mapOf("kind" to "entry", "entry" to JSONObject(json).toFlutterMap()),
                generation,
            )
        }
    }

    private fun openUri(value: String, share: Boolean) {
        val uri = Uri.parse(value)
        val mime = contentResolver.getType(uri) ?: "*/*"
        val action = if (share) Intent.ACTION_SEND else Intent.ACTION_VIEW
        val intent = Intent(action).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.clipData = ClipData.newRawUri("Downloader dosyası", uri)
        if (share) {
            intent.type = mime
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            startActivity(Intent.createChooser(intent, "Dosyayı paylaş"))
        } else {
            intent.setDataAndType(uri, mime)
            startActivity(Intent.createChooser(intent, "Dosyayı aç"))
        }
    }

    private fun openDownloadFolder(kind: String) {
        MediaStorePublisher.ensureDirectory(this, kind)
        openRelativeFolder(MediaStorePublisher.relativeDirectory(kind))
    }

    private fun openRelativeFolder(relativePath: String) {
        val documentId = "primary:$relativePath"
        val authority = "com.android.externalstorage.documents"
        val documentUri = DocumentsContract.buildDocumentUri(authority, documentId)
        val viewIntent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(documentUri, DocumentsContract.Document.MIME_TYPE_DIR)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivity(viewIntent)
        } catch (_: Throwable) {
            val treeUri = DocumentsContract.buildTreeDocumentUri(authority, documentId)
            startActivity(
                Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
                    putExtra(DocumentsContract.EXTRA_INITIAL_URI, treeUri)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                },
            )
        }
    }

    private fun sharedText(intent: Intent?): String? {
        if (intent?.action != Intent.ACTION_SEND || intent.type != "text/plain") return null
        return intent.getStringExtra(Intent.EXTRA_TEXT)?.trim()?.takeIf { it.startsWith("http://") || it.startsWith("https://") }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 3001)
        }
    }

    private fun requestLegacyStoragePermission() {
        if (
            Build.VERSION.SDK_INT <= Build.VERSION_CODES.P &&
            ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.WRITE_EXTERNAL_STORAGE,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE),
                3002,
            )
        }
    }

    companion object {
        private const val METHODS = "com.forintx.videoindirici/engine"
        private const val EVENTS = "com.forintx.videoindirici/events"
        private const val SHARES = "com.forintx.videoindirici/share"
        private const val PLAYLIST = "com.forintx.videoindirici/playlist"
    }
}
