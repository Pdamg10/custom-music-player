package com.custom.musicplayer.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import com.custom.musicplayer.R
import com.custom.musicplayer.service.MediaNotificationListenerService

class MusicPlayerWidgetProvider : AppWidgetProvider() {

    companion object {
        const val ACTION_PLAY_PAUSE = "com.custom.musicplayer.ACTION_PLAY_PAUSE"
        const val ACTION_NEXT = "com.custom.musicplayer.ACTION_NEXT"
        const val ACTION_PREVIOUS = "com.custom.musicplayer.ACTION_PREVIOUS"

        fun updateAllWidgets(context: Context) {
            val appWidgetManager = AppWidgetManager.getInstance(context)
            val ids = appWidgetManager.getAppWidgetIds(ComponentName(context, MusicPlayerWidgetProvider::class.java))
            for (id in ids) {
                updateAppWidget(context, appWidgetManager, id)
            }
        }

        private fun updateAppWidget(context: Context, appWidgetManager: AppWidgetManager, appWidgetId: Int) {
            val views = RemoteViews(context.packageName, R.layout.layout_home_widget)

            views.setTextViewText(R.id.widget_song_title, MediaNotificationListenerService.currentTitle)
            views.setTextViewText(R.id.widget_song_artist, MediaNotificationListenerService.currentArtist)

            val isPlaying = MediaNotificationListenerService.isPlaying
            views.setImageViewResource(
                R.id.btn_widget_play_pause,
                if (isPlaying) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play
            )

            MediaNotificationListenerService.currentAlbumArt?.let { art ->
                views.setImageViewBitmap(R.id.widget_album_art, art)
            }

            // Intent para botones
            views.setOnClickPendingIntent(R.id.btn_widget_play_pause, getPendingIntent(context, ACTION_PLAY_PAUSE))
            views.setOnClickPendingIntent(R.id.btn_widget_next, getPendingIntent(context, ACTION_NEXT))
            views.setOnClickPendingIntent(R.id.btn_widget_prev, getPendingIntent(context, ACTION_PREVIOUS))

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }

        private fun getPendingIntent(context: Context, action: String): PendingIntent {
            val intent = Intent(context, MusicPlayerWidgetProvider::class.java).apply {
                this.action = action
            }
            return PendingIntent.getBroadcast(
                context,
                action.hashCode(),
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }
    }

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (id in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, id)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_PLAY_PAUSE, ACTION_NEXT, ACTION_PREVIOUS -> {
                updateAllWidgets(context)
            }
        }
    }
}
