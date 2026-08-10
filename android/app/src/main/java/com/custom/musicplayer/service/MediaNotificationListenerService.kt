package com.custom.musicplayer.service

import android.content.ComponentName
import android.content.Intent
import android.graphics.Bitmap
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.service.notification.NotificationListenerService

class MediaNotificationListenerService : NotificationListenerService() {

    companion object {
        const val ACTION_MEDIA_STATE_CHANGED = "com.custom.musicplayer.MEDIA_STATE_CHANGED"
        const val EXTRA_TITLE = "extra_title"
        const val EXTRA_ARTIST = "extra_artist"
        const val EXTRA_IS_PLAYING = "extra_is_playing"
        
        var currentTitle: String = "Sin reproducción"
        var currentArtist: String = "Artista desconocido"
        var isPlaying: Boolean = false
        var currentAlbumArt: Bitmap? = null

        private var activeController: MediaController? = null

        fun sendMediaCommand(command: String) {
            activeController?.transportControls?.let { transport ->
                when (command) {
                    "PLAY_PAUSE" -> {
                        if (isPlaying) transport.pause() else transport.play()
                    }
                    "NEXT" -> transport.skipToNext()
                    "PREVIOUS" -> transport.skipToPrevious()
                }
            }
        }
    }

    private lateinit var mediaSessionManager: MediaSessionManager
    private val sessionChangeListener = MediaSessionManager.OnActiveSessionsChangedListener { controllers ->
        registerMediaController(controllers)
    }

    override fun onCreate() {
        super.onCreate()
        mediaSessionManager = getSystemService(MEDIA_SESSION_SERVICE) as MediaSessionManager
        try {
            val component = ComponentName(this, MediaNotificationListenerService::class.java)
            val controllers = mediaSessionManager.getActiveSessions(component)
            registerMediaController(controllers)
            mediaSessionManager.addOnActiveSessionsChangedListener(sessionChangeListener, component)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun registerMediaController(controllers: List<MediaController>?) {
        if (controllers.isNullOrEmpty()) return
        val controller = controllers.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING }
            ?: controllers.first()

        activeController = controller
        controller.registerCallback(object : MediaController.Callback() {
            override fun onMetadataChanged(metadata: MediaMetadata?) {
                updateMetadata(metadata)
            }

            override fun onPlaybackStateChanged(state: PlaybackState?) {
                updatePlaybackState(state)
            }
        })

        updateMetadata(controller.metadata)
        updatePlaybackState(controller.playbackState)
    }

    private fun updateMetadata(metadata: MediaMetadata?) {
        if (metadata != null) {
            currentTitle = metadata.getString(MediaMetadata.METADATA_KEY_TITLE) ?: "Sin título"
            currentArtist = metadata.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: "Artista desconocido"
            currentAlbumArt = metadata.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART)
                ?: metadata.getBitmap(MediaMetadata.METADATA_KEY_ART)
        } else {
            currentTitle = "Sin reproducción"
            currentArtist = "Artista desconocido"
            currentAlbumArt = null
        }
        broadcastUpdate()
    }

    private fun updatePlaybackState(state: PlaybackState?) {
        isPlaying = state?.state == PlaybackState.STATE_PLAYING
        broadcastUpdate()
    }

    private fun broadcastUpdate() {
        val intent = Intent(ACTION_MEDIA_STATE_CHANGED)
        intent.putExtra(EXTRA_TITLE, currentTitle)
        intent.putExtra(EXTRA_ARTIST, currentArtist)
        intent.putExtra(EXTRA_IS_PLAYING, isPlaying)
        sendBroadcast(intent)

        // Actualizar servicios flotantes y widget
        FloatingWidgetService.updateMediaState(currentTitle, currentArtist, isPlaying, currentAlbumArt)
        com.custom.musicplayer.widget.MusicPlayerWidgetProvider.updateAllWidgets(this)
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            mediaSessionManager.removeOnActiveSessionsChangedListener(sessionChangeListener)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
