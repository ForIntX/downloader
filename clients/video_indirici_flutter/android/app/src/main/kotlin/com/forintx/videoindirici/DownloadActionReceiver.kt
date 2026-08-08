package com.forintx.videoindirici

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class DownloadActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val jobId = intent.getStringExtra("job_id") ?: return
        when (intent.action) {
            ACTION_PAUSE -> EngineRuntime.requestStop(jobId, paused = true)
            ACTION_CANCEL -> EngineRuntime.requestStop(jobId, paused = false)
        }
    }

    companion object {
        const val ACTION_PAUSE = "com.forintx.videoindirici.PAUSE"
        const val ACTION_CANCEL = "com.forintx.videoindirici.CANCEL"
    }
}
