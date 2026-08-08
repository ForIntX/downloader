package com.forintx.videoindirici

import android.app.NotificationManager
import android.app.job.JobParameters
import android.app.job.JobService
import android.os.Build
import org.json.JSONObject

class UserInitiatedDownloadJobService : JobService() {
    override fun onStartJob(params: JobParameters): Boolean {
        val jobJson = params.extras.getString(DownloadForegroundService.EXTRA_JOB_JSON) ?: return false
        val job = JSONObject(jobJson)
        val notificationId = job.getString("id").hashCode()
        val notification = DownloadNotifications.progress(this, job.getString("id"), job.optString("title", "Video"))
        if (Build.VERSION.SDK_INT >= 34) {
            setNotification(params, notificationId, notification, JOB_END_NOTIFICATION_POLICY_REMOVE)
        } else {
            getSystemService(NotificationManager::class.java).notify(notificationId, notification)
        }
        EngineRuntime.run(jobJson) { jobFinished(params, false) }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        val json = params.extras.getString(DownloadForegroundService.EXTRA_JOB_JSON) ?: return true
        val jobId = JSONObject(json).getString("id")
        val userRequested = EngineRuntime.hasStopRequest(jobId)
        if (!userRequested) EngineRuntime.requestStop(jobId, paused = true)
        return !userRequested
    }
}
