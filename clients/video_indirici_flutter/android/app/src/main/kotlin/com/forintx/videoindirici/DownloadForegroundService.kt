package com.forintx.videoindirici

import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import org.json.JSONObject

class DownloadForegroundService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val jobJson = intent?.getStringExtra(EXTRA_JOB_JSON) ?: return START_NOT_STICKY
        val job = JSONObject(jobJson)
        val jobId = job.getString("id")
        val notification = DownloadNotifications.progress(this, jobId, job.optString("title", "Video"))
        if (Build.VERSION.SDK_INT >= 35) {
            startForeground(jobId.hashCode(), notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING)
        } else if (Build.VERSION.SDK_INT >= 29) {
            startForeground(jobId.hashCode(), notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(jobId.hashCode(), notification)
        }
        EngineRuntime.run(jobJson) { stopSelf(startId) }
        return START_REDELIVER_INTENT
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_JOB_JSON = "job_json"
    }
}
