package com.forintx.videoindirici

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PersistableBundle
import androidx.core.content.ContextCompat
import org.json.JSONObject

internal object AndroidDownloadScheduler {
    fun start(context: Context, jobJson: String) {
        val job = JSONObject(jobJson)
        val wifiOnly = job.optBoolean("wifi_only", false)
        val chargingOnly = job.optBoolean("charging_only", false)
        val constrained = wifiOnly || chargingOnly
        if (Build.VERSION.SDK_INT >= 34 || constrained) {
            val extras = PersistableBundle().apply {
                putString(DownloadForegroundService.EXTRA_JOB_JSON, jobJson)
            }
            val builder = JobInfo.Builder(
                job.getString("id").hashCode() and Int.MAX_VALUE,
                ComponentName(context, UserInitiatedDownloadJobService::class.java),
            )
                .setRequiredNetworkType(
                    if (wifiOnly) JobInfo.NETWORK_TYPE_UNMETERED else JobInfo.NETWORK_TYPE_ANY,
                )
                .setRequiresCharging(chargingOnly)
                .setExtras(extras)
            if (Build.VERSION.SDK_INT >= 34) builder.setUserInitiated(true)
            val info = builder.build()
            val result = context.getSystemService(JobScheduler::class.java).schedule(info)
            if (result != JobScheduler.RESULT_SUCCESS) error("Android indirme işini başlatamadı")
        } else {
            val intent = Intent(context, DownloadForegroundService::class.java)
                .putExtra(DownloadForegroundService.EXTRA_JOB_JSON, jobJson)
            ContextCompat.startForegroundService(context, intent)
        }
    }

    fun cancel(context: Context, jobId: String) {
        context.getSystemService(JobScheduler::class.java).cancel(jobId.hashCode() and Int.MAX_VALUE)
    }

    fun rescheduleWaiting(context: Context, wifiOnly: Boolean, chargingOnly: Boolean) {
        val scheduler = context.getSystemService(JobScheduler::class.java)
        val component = ComponentName(context, UserInitiatedDownloadJobService::class.java)
        val waiting = scheduler.allPendingJobs
            .filter { it.service == component }
            .mapNotNull { info ->
                val json = info.extras.getString(DownloadForegroundService.EXTRA_JOB_JSON) ?: return@mapNotNull null
                val jobId = runCatching { JSONObject(json).getString("id") }.getOrNull() ?: return@mapNotNull null
                if (EngineRuntime.isRunning(jobId)) null else Triple(info.id, jobId, json)
            }
        waiting.forEach { (schedulerId, _, json) ->
            scheduler.cancel(schedulerId)
            val updated = JSONObject(json)
                .put("wifi_only", wifiOnly)
                .put("charging_only", chargingOnly)
                .toString()
            start(context, updated)
        }
    }
}
