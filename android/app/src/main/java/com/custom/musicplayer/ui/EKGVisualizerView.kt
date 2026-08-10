package com.custom.musicplayer.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import java.util.Random

class EKGVisualizerView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val barCount = 18
    private val barHeights = FloatArray(barCount) { 10f }
    private val random = Random()
    private var isPlaying = false

    private var accentColor = Color.parseColor("#FF1744")
    private var albumArtBitmap: Bitmap? = null

    private val srcRect = android.graphics.Rect()
    private val destRect = RectF()
    private val barRect = RectF()

    private val paintBar = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = accentColor
    }

    private val paintBg = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#050508")
    }

    private val paintArt = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        isFilterBitmap = true
    }

    private val animatorRunnable = object : Runnable {
        override fun run() {
            if (isPlaying) {
                for (i in 0 until barCount) {
                    barHeights[i] = 10f + (random.nextFloat() * 100f)
                }
                invalidate()
                postDelayed(this, 60)
            }
        }
    }

    fun setPlaying(playing: Boolean) {
        if (this.isPlaying != playing) {
            this.isPlaying = playing
            if (playing) {
                removeCallbacks(animatorRunnable)
                post(animatorRunnable)
            } else {
                removeCallbacks(animatorRunnable)
                for (i in 0 until barCount) barHeights[i] = 10f
                invalidate()
            }
        }
    }

    fun setAccentColor(colorHex: String) {
        try {
            accentColor = Color.parseColor(colorHex)
            paintBar.color = accentColor
            invalidate()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun setAlbumArt(bitmap: Bitmap?) {
        albumArtBitmap = bitmap
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val width = width.toFloat()
        val height = height.toFloat()

        // 1. Fondo Oscuro
        canvas.drawRect(0f, 0f, width, height, paintBg)

        // 2. Carátula de álbum semi-transparente
        albumArtBitmap?.let { art ->
            srcRect.set(0, 0, art.width, art.height)
            destRect.set(0f, 0f, width, height)
            paintArt.alpha = 180
            canvas.drawBitmap(art, srcRect, destRect, paintArt)
        }

        // 3. Barras EKG animadas en la parte inferior
        val totalSpacing = width * 0.1f
        val availableWidth = width - totalSpacing
        val barWidth = availableWidth / barCount
        val gap = totalSpacing / (barCount + 1)

        val bottomY = height - 80f

        for (i in 0 until barCount) {
            val left = gap + i * (barWidth + gap)
            val barH = barHeights[i]
            val top = bottomY - barH
            val right = left + barWidth
            barRect.set(left, top, right, bottomY)
            canvas.drawRoundRect(barRect, 6f, 6f, paintBar)
        }
    }
}
