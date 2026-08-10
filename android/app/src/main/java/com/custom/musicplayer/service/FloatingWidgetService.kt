package com.custom.musicplayer.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.ImageButton
import android.widget.TextView
import androidx.core.app.NotificationCompat
import com.custom.musicplayer.R
import com.custom.musicplayer.ui.EKGVisualizerView

/**
 * A foreground service that manages and displays a floating music player widget.
 * This widget overlays other applications and provides media controls and visualizers.
 */
class FloatingWidgetService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var floatingView: View
    private lateinit var ekgVisualizer: EKGVisualizerView
    private lateinit var txtTitle: TextView
    private lateinit var txtArtist: TextView
    private lateinit var btnPlayPause: ImageButton

    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    companion object {
        /**
         * Singleton instance of the service for external interaction.
         */
        var instance: FloatingWidgetService? = null

        /**
         * Updates the UI of the floating widget with the current media state.
         *
         * @param title The title of the current song.
         * @param artist The artist of the current song.
         * @param isPlaying True if media is currently playing, false otherwise.
         * @param art The album art bitmap, if available.
         */
        fun updateMediaState(title: String, artist: String, isPlaying: Boolean, art: Bitmap?) {
            instance?.let { service ->
                service.txtTitle.text = title
                service.txtArtist.text = artist
                service.ekgVisualizer.setAlbumArt(art)
                service.ekgVisualizer.setPlaying(isPlaying)
                service.btnPlayPause.setImageResource(
                    if (isPlaying) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play
                )
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    /**
     * Called when the service is first created. Initializes the floating view,
     * window manager parameters, and sets up touch and click listeners.
     */
    override fun onCreate() {
        super.onCreate()
        instance = this
        startForegroundServiceNotification()

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        floatingView = LayoutInflater.from(this).inflate(R.layout.layout_floating_widget, null)

        val paramsType = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            paramsType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.START
            x = 40
            y = 120
        }

        ekgVisualizer = floatingView.findViewById(R.id.ekg_visualizer)
        txtTitle = floatingView.findViewById(R.id.txt_floating_title)
        txtArtist = floatingView.findViewById(R.id.txt_floating_artist)
        btnPlayPause = floatingView.findViewById(R.id.btn_floating_play_pause)
        val btnPrev: ImageButton = floatingView.findViewById(R.id.btn_floating_prev)
        val btnNext: ImageButton = floatingView.findViewById(R.id.btn_floating_next)
        val btnClose: ImageButton = floatingView.findViewById(R.id.btn_close_floating)

        txtTitle.isSelected = true // Para scroll marquee

        btnClose.setOnClickListener { stopSelf() }

        btnPlayPause.setOnClickListener { MediaNotificationListenerService.sendMediaCommand("PLAY_PAUSE") }
        btnPrev.setOnClickListener { MediaNotificationListenerService.sendMediaCommand("PREVIOUS") }
        btnNext.setOnClickListener { MediaNotificationListenerService.sendMediaCommand("NEXT") }

        // Touch Listener para arrastrar la ventana flotante por la pantalla
        floatingView.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = initialX + (event.rawX - initialTouchX).toInt()
                    params.y = initialY - (event.rawY - initialTouchY).toInt()
                    windowManager.updateViewLayout(floatingView, params)
                    true
                }
                MotionEvent.ACTION_UP -> {
                    // Si el movimiento es muy pequeño, considerar como click si fuera necesario
                    // En este caso el widget tiene botones específicos, pero cumplimos con performClick
                    floatingView.performClick()
                    true
                }
                else -> false
            }
        }

        windowManager.addView(floatingView, params)
    }

    /**
     * Initializes and starts the foreground notification for this service.
     * This is required for long-running background services that interact with the UI.
     */
    private fun startForegroundServiceNotification() {
        val channelId = "floating_music_channel"
        val channel = NotificationChannel(
            channelId,
            "Ventana Flotante Neón",
            NotificationManager.IMPORTANCE_LOW
        )
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)

        val notification: Notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("Custom Floating Music Player")
            .setContentText("Ventana flotante activa sobre otras apps")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .build()

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                startForeground(101, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
            } else {
                startForeground(101, notification)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Called when the service is being destroyed. Removes the floating view from the
     * window manager and clears the singleton instance.
     */
    override fun onDestroy() {
        super.onDestroy()
        instance = null
        if (::floatingView.isInitialized) {
            windowManager.removeView(floatingView)
        }
    }
}
