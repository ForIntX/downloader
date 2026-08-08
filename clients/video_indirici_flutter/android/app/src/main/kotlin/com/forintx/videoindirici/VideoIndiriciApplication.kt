package com.forintx.videoindirici

import io.flutter.app.FlutterApplication

class VideoIndiriciApplication : FlutterApplication() {
    override fun onCreate() {
        super.onCreate()
        EngineRuntime.initialize(this)
        DownloadNotifications.createChannels(this)
    }
}
