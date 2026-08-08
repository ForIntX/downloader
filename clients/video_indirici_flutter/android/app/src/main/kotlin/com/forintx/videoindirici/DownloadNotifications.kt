package com.forintx.videoindirici

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat

internal object DownloadNotifications {
    const val CHANNEL_PROGRESS = "downloads"
    const val CHANNEL_RESULTS = "download_results"

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL_PROGRESS, "İndirmeler", NotificationManager.IMPORTANCE_LOW))
        manager.createNotificationChannel(NotificationChannel(CHANNEL_RESULTS, "İndirme sonuçları", NotificationManager.IMPORTANCE_DEFAULT))
    }

    fun progress(context: Context, jobId: String, title: String, percent: Int = 0): Notification {
        val openIntent = PendingIntent.getActivity(
            context,
            jobId.hashCode(),
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        fun actionIntent(action: String): PendingIntent = PendingIntent.getBroadcast(
            context,
            (jobId + action).hashCode(),
            Intent(context, DownloadActionReceiver::class.java).setAction(action).putExtra("job_id", jobId),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(context, CHANNEL_PROGRESS)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(title)
            .setContentText(if (percent > 0) "%$percent indirildi" else "Hazırlanıyor")
            .setProgress(100, percent.coerceIn(0, 100), percent <= 0)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .addAction(0, "Duraklat", actionIntent(DownloadActionReceiver.ACTION_PAUSE))
            .addAction(0, "İptal", actionIntent(DownloadActionReceiver.ACTION_CANCEL))
            .build()
    }

    fun result(context: Context, title: String, success: Boolean): Notification =
        NotificationCompat.Builder(context, CHANNEL_RESULTS)
            .setSmallIcon(if (success) android.R.drawable.stat_sys_download_done else android.R.drawable.stat_notify_error)
            .setContentTitle(if (success) "İndirme tamamlandı" else "İndirme başarısız")
            .setContentText(title)
            .setAutoCancel(true)
            .build()
}
