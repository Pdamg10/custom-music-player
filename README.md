# Custom Floating Music Player (PyQt6) — Red World Edition 🎧🖤

Un reproductor de música flotante, compacto y moderno **multi-plataforma (Linux Wayland/X11 & Windows 10/11)** con estética **Negro Azabache & Colores Neón Personalizables**, fondo animado de audífonos con 18 barras de ecualizador EKG en tiempo real, recuadro de carátula personalizable, carrusel de fondos con transiciones *cross-fade* y control multimedia completo.

---

## 🚀 Características Principales

### 🌐 Soporte Multi-Plataforma Nativo
- **Linux (Wayland & X11):** Integración event-driven con el estándar **DBus / MPRIS2** (*Spotify, Strawberry, Rhythmbox, Amberol, Audacious, Firefox, Chrome, VLC*, etc.).
- **Windows (10 / 11):** Integración nativa con **System Media Transport Controls (SMTC / WinRT)** (*Spotify para Windows, Microsoft Edge, Chrome, Windows Media Player, iTunes*, etc.).

---

### 🎨 Experiencia Visual & Personalización Completa
- **🖼️ Personalización del Recuadro Central de Canción:** 
  - Selección interactiva de cualquier imagen (`.png`, `.jpg`, `.jpeg`, `.webp`) para el recuadro central desde el menú contextual.
  - Alternancia entre **Modo Automático** (muestra la portada del álbum cuando hay canción activa) y **Modo Fijo** (mantiene fija tu imagen personalizada semi-transparente).
- **🎨 Color de Tema & Controles:** Elige entre varios temas neón (🔴 Carmesí, 🔵 Cyan, 🟣 Púrpura, 🟢 Verde Esmeralda, 🟠 Naranja, 🩷 Rosa, ⚪ Blanco) o selecciona un color personalizado con `QColorDialog`. Todos los botones, bordes, menus y tiradores (`♥` y `⚪`) cambian instantáneamente al tono elegido.
- **🎧 Fondo Animado & 18 Barras EKG:** Capa gráfica con barras de ecualizador en tiempo real que oscilan al ritmo de la música en el color del tema activo.
- **🖼️ Carrusel de Fondos con Transición Suave (Cross-Fade):** Galería rotativa de fondos con transiciones progresivas a ~50 FPS y monitoreo en tiempo real con `QFileSystemWatcher`.
- **📐 Modos Adaptativos de Imagen (Aspect Mode):** `Ajustar (fit)`, `Llenar (fill)` y `Estirar (stretch)`.
- **♥ Barra de Reproducción & Volumen:** Tirador gráfico en forma de corazón dinámico (`♥`) para el *seekbar* y tirador circular perfecto para el volumen.
- **🎛️ Disposición de Controles Simétricos:** Favorito (`♥`), Pista Anterior (`⏮`), Botón Central Circular Play/Pausa (`▶` / `⏸`), Pista Siguiente (`⏭`) y Repetición (`↻`).
- **📜 Efecto Marquesina (*Marquee Scroll*):** Títulos y artistas largos se desplazan en texto continuo a 25 FPS.
- **📐 Modo Compacto & Normal:** Alterna dinámicamente entre la vista completa (280x360) y la barra mini (280x68) con el botón `⤢` o las teclas `Ctrl+C` / `F11`.

---

### ⌨️ Atajos de Teclado

| Atajo | Acción |
| :--- | :--- |
| `Espacio` | Reproducir / Pausar |
| `Flecha Izquierda` / `Derecha` | Pista Anterior / Siguiente |
| `Flecha Arriba` / `Abajo` | Subir / Bajar Volumen (+5% / -5%) |
| `Ctrl+F` | Marcar / Desmarcar Canción como Favorita |
| `Ctrl+B` | Cambiar de Fondo de Pantalla Inmediatamente |
| `Ctrl+C` / `F11` | Alternar Modo Compacto / Normal |
| `Ctrl+H` / `F12` / `Esc` | Mostrar / Ocultar Ventana (System Tray) |
| `Ctrl+T` | Fijar Ventana Siempre Encima (*Stays on Top*) |

---

## 📁 Estructura del Proyecto

```text
custom-music-player/
├── main.py                    # Punto de entrada principal Escritorio (Detección de SO & Ventana)
├── player.py                  # Wrapper ejecutable de compatibilidad
├── mpris_client.py            # Adaptador Linux DBus / MPRIS2 event-driven
├── win_media_client.py        # Adaptador Windows SMTC / WinRT
├── config_manager.py          # Gestor de ajustes JSON (~/.config/custom-music-player/)
├── build.sh                   # Script de compilación ejecutable portátil Linux
├── ui/                        # Interfaz gráfica PyQt6 para Escritorio
│   ├── player_widget.py       # FloatingMusicPlayer, HeadphoneEKGWidget & BackgroundContainer
│   ├── marquee_label.py       # Scroll continuo de texto en marquesina
│   ├── equalizer_widget.py    # Indicador animado de cabecera
│   ├── elided_label.py        # Etiqueta con truncado elíptico
│   ├── color_extractor.py     # Extractor de paletas de color HSV
│   └── styles.py              # Hoja de estilos QSS & Generador de tiradores PNG
├── android/                   # 📱 Módulo Nativo para Android (Kotlin + Jetpack Compose)
│   ├── app/src/main/
│   │   ├── java/com/custom/musicplayer/
│   │   │   ├── MainActivity.kt                       # Configuración & Permisos Android
│   │   │   ├── ui/EKGVisualizerView.kt               # Canvas EKG Animado para Android
│   │   │   ├── service/MediaNotificationListenerService.kt # Lector de música activo
│   │   │   ├── service/FloatingWidgetService.kt       # Overlay flotante sobre apps
│   │   │   └── widget/MusicPlayerWidgetProvider.kt   # Widget de Escritorio Android
│   │   └── res/                                      # Layouts, Widgets & Recurso Neón
│   ├── build.gradle.kts
│   └── settings.gradle.kts
├── requirements.txt           # Dependencias Python
└── README.md                  # Documentación del proyecto
```

---

## 🛠️ Instalación y Ejecución

### 🐧 En Linux

1. **Instalar dependencias y ejecutar:**
   ```bash
   pip install -r requirements.txt
   python3 main.py
   ```

2. **Generar un Ejecutable Portátil Binario Independiente:**
   ```bash
   ./build.sh
   ```
   El ejecutable portátil quedará listo en `dist/CustomMusicPlayer` para llevar a cualquier otra PC con Linux en un pendrive USB sin necesidad de instalar Python ni librerías.

---

### 🪟 En Windows (10 / 11)

1. **Instalar dependencias y ejecutar:**
   ```cmd
   pip install pyqt6 winsdk
   python main.py
   ```

2. **Generar Ejecutable `.exe` para Windows:**
   ```cmd
   pip install pyinstaller
   pyinstaller --noconfirm --onefile --windowed --name "CustomMusicPlayer" main.py
   ```
   El ejecutable quedará en `dist\CustomMusicPlayer.exe` listo para usar o compartir.

---

### 📱 En Android

1. Abrir la carpeta `android/` en **Android Studio**.
2. Compilar e instalar el proyecto en tu dispositivo Android o emulador (`./gradlew assembleDebug`).
3. Conceder los permisos de **Lectura de Notificaciones de Música** (para leer Spotify, YouTube Music, etc.) y **Superposición sobre otras aplicaciones**.
4. ¡Disfruta de la ventana flotante con ecualizador EKG sobre cualquier app o agrega el Widget a tu pantalla de inicio!

