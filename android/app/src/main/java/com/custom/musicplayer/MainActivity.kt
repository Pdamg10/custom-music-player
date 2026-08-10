package com.custom.musicplayer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.content.ContextCompat
import com.custom.musicplayer.service.FloatingWidgetService

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var hasNotificationPermission by remember {
                mutableStateOf(
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        ContextCompat.checkSelfPermission(
                            this,
                            Manifest.permission.POST_NOTIFICATIONS
                        ) == PackageManager.PERMISSION_GRANTED
                    } else true
                )
            }

            val permissionLauncher = rememberLauncherForActivityResult(
                contract = ActivityResultContracts.RequestPermission(),
                onResult = { isGranted ->
                    hasNotificationPermission = isGranted
                }
            )

            CustomMusicPlayerApp(
                onGrantOverlayPermission = { requestOverlayPermission() },
                onGrantNotificationPermission = {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !hasNotificationPermission) {
                        permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                    }
                    requestNotificationListenerPermission()
                },
                onToggleFloatingService = { toggleFloatingService() }
            )
        }
    }

    private fun requestOverlayPermission() {
        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            startActivity(intent)
        }
    }

    private fun requestNotificationListenerPermission() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        startActivity(intent)
    }

    private fun toggleFloatingService() {
        if (!Settings.canDrawOverlays(this)) {
            requestOverlayPermission()
            return
        }

        val intent = Intent(this, FloatingWidgetService::class.java)
        try {
            if (FloatingWidgetService.instance != null) {
                stopService(intent)
            } else {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(intent)
                } else {
                    startService(intent)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}

@Preview(showBackground = true, device = "spec:width=411dp,height=891dp,dpi=420,isRound=false,chinSize=0dp,orientation=portrait")
@Composable
fun DefaultPreview() {
    CustomMusicPlayerApp(
        onGrantOverlayPermission = {},
        onGrantNotificationPermission = {},
        onToggleFloatingService = {}
    )
}

@Composable
fun CustomMusicPlayerApp(
    onGrantOverlayPermission: () -> Unit,
    onGrantNotificationPermission: () -> Unit,
    onToggleFloatingService: () -> Unit
) {
    val bgDark = Color(0xFF050508)
    val neonRed = Color(0xFFFF1744)

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = bgDark
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "🎧 Custom Music Player",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )

            Text(
                text = "Edición Móvil (Android)",
                fontSize = 14.sp,
                color = neonRed,
                modifier = Modifier.padding(bottom = 32.dp)
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0C0C10)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "1. Permiso de Notificaciones",
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = "Necesario para detectar automáticamente la canción activa en Spotify, YouTube Music, VLC, etc.",
                        fontSize = 12.sp,
                        color = Color.Gray,
                        modifier = Modifier.padding(vertical = 8.dp)
                    )
                    Button(
                        onClick = onGrantNotificationPermission,
                        colors = ButtonDefaults.buttonColors(containerColor = neonRed)
                    ) {
                        Text("Activar Lector de Música")
                    }
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0C0C10)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 24.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "2. Permiso de Superposición",
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = "Necesario para dibujar el widget flotante con barras EKG sobre otras aplicaciones.",
                        fontSize = 12.sp,
                        color = Color.Gray,
                        modifier = Modifier.padding(vertical = 8.dp)
                    )
                    Button(
                        onClick = onGrantOverlayPermission,
                        colors = ButtonDefaults.buttonColors(containerColor = neonRed)
                    ) {
                        Text("Permitir Superposición")
                    }
                }
            }

            Button(
                onClick = onToggleFloatingService,
                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "🚀 Activar / Detener Ventana Flotante",
                    color = Color.Black,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
