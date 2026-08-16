# Custom Music Player — Red World Edition 🎧🖤

Un reproductor de música de escritorio y móvil moderno, ultra liviano y personalizable (**Linux, Windows & Android**), diseñado con estética **Negro Azabache & Colores Neón Reactivos**, transiciones suaves *cross-fade* de fondos, visualizador de audio, carátula nítida en alta resolución, motor de audio nativo de alto rendimiento y control total vía **MPRIS2 / Teclas Multimedia**.

---

## 📸 Tres Modos de Visualización Adaptables

| Modo | Dimensiones | Descripción |
| :--- | :--- | :--- |
| **Modo Pequeño (Normal)** | `350 × 430 px` | Widget flotante vertical ideal para escritorio. Carátula centrada 100% nítida, marquesina con título y artista, control deslizante Y2K, botones de transporte y menú unificado con lista de canciones. |
| **Modo Compacto** | `640 × 260 px` | Layout horizontal elegante inspirado en reproductores de alta fidelidad. Carátula grande (220×220px) con bordes redondeados, barra de progreso dual (`0:15` / `3:27`), acceso a lista `☰♪`, favoritos `♥`, aleatorio `⇄`, repetición `A→` y utilidades en cabecera `[⌄] ... [🔊] [📊] [⋮]`. |
| **Modo Expandido** | `Ventana Completa` | Vista de biblioteca inmersiva con buscador en tiempo real, visualizador EKG detrás de la carátula, panel de pistas, gestión de carpetas y navegación de playlists. |

---

## 🚀 Características Principales

### 🎵 Motor de Audio Nativo & Integración Multimedia
- **Motor de Audio Autónomo:** Basado en `PyQt6.QtMultimedia` con decodificación directa vía FFmpeg (soporta **FLAC, MP3, WAV, OGG, AAC, M4A, OPUS** y más).
- **Servidor y Cliente MPRIS2 (Linux DBus):** Control total desde applets del sistema (GNOME, KDE Plasma, Waybar, etc.) y respuesta inmediata a teclas de hardware multimedia (`Play/Pause`, `Next`, `Prev`, `Stop`).
- **Lista de Canciones Instantánea:** Vista de lista ligera y optimizada ([`SmallPlaylistPage`](file:///home/phame/.local/bin/custom-music-player/ui/small_playlist.py)) con `QStyledItemDelegate` nativo para búsqueda y filtrado en tiempo real sin retrasos ni consumo excesivo de memoria.

### 🎨 Estética Neón & Personalización Visual
- **Temas Neón Reactivos:** Extracción automática de paleta de color dominante a partir de la carátula o fondo activo (con soporte para degradados multi-parada).
- **Control de Tipografía e Íconos Monocromáticos:** Todos los controles (`⏮`, `⏭`, `▶`, `⏸`, `⇄`, `♥`, `A→`, `⋮`, `×`) se integran con la fuente del sistema y se iluminan dinámicamente según el estado y tema activo.
- **Carrusel de Fondos con *Cross-Fade*:** Ciclo automático de imágenes de fondo personalizables con transición suave y monitoreo en tiempo real del directorio mediante `QFileSystemWatcher`.
- **Fijación Flotante Opcional:** Ejecución normal por defecto o modo fijado (*Always on Top*) alternable con `Ctrl+T`.

---

## ⌨️ Atajos de Teclado y Controles

| Atajo | Acción |
| :--- | :--- |
| `Espacio` / `Media Play-Pause` | Reproducir / Pausar (alternar) |
| `Flecha Izquierda` / `Media Prev` | Pista Anterior |
| `Flecha Derecha` / `Media Next` | Pista Siguiente |
| `Flecha Arriba` / `Flecha Abajo` | Subir / Bajar Volumen (±5%) |
| `Ctrl+F` | Marcar / Desmarcar Canción como Favorita |
| `Ctrl+C` / `F11` | Alternar entre **Modo Compacto** y **Modo Pequeño** |
| `Ctrl+B` | Cambiar Fondo de Pantalla Inmediatamente |
| `Ctrl+T` | Alternar Fijación Superior (*Always on Top*) |
| `Ctrl+H` / `F12` / `Esc` | Mostrar / Ocultar en la Bandeja del Sistema (*System Tray*) |

---

## 📁 Estructura del Proyecto

```text
custom-music-player/
├── main.py                    # Punto de entrada principal (Inicialización Qt, MPRIS y Detección de SO)
├── audio_engine.py            # Motor de audio nativo (PyQt6 QMediaPlayer / FFmpeg / Slots MPRIS)
├── mpris_server.py            # Servidor DBus MPRIS2 (org.mpris.MediaPlayer2.CustomMusicPlayer)
├── mpris_client.py            # Adaptador de compatibilidad MPRISClient
├── config_manager.py          # Gestor de configuración persistente JSON (~/.config/custom-music-player/)
├── build.sh                   # Script de compilación para binario ejecutable en Linux
├── requirements.txt           # Dependencias de Python (PyQt6, dbus-next, etc.)
│
├── ui/                        # Interfaz Gráfica PyQt6 de Escritorio
│   ├── player_widget.py       # FloatingMusicPlayer, CompactCoverWidget, HeadphoneEKGWidget & BackgroundContainer
│   ├── expanded_view.py       # Vista expandida de biblioteca, buscador y visualizador EKG
│   ├── small_playlist.py      # Lista de canciones ultra rápida con SmallPlaylistDelegate
│   ├── unified_mode_menu.py   # Menú unificado de modos (Pequeño, Compacto, Expandido) y canciones
│   ├── styles.py              # Tokens de diseño, constantes de dimensiones y generador de estilos QSS
│   ├── color_extractor.py     # Extractor de colores vibrantes y paletas degradadas automáticas
│   ├── gradient_dialog.py     # Diálogo de personalización de temas y colores degradados
│   ├── y2k_volume_slider.py   # Deslizador de volumen con estilo personalizado
│   ├── marquee_label.py       # Scroll de texto horizontal fluido para títulos largos
│   └── equalizer_widget.py    # Indicador de ecualización animado
│
└── mobile/                    # 📱 Aplicación Móvil (React Native / Expo SDK)
    ├── src/app/               # Pantallas principales y panel de ajustes
    ├── assets/                # Iconos y recursos gráficos móviles
    └── package.json           # Dependencias de la app móvil
```

---

## 🛠️ Instalación y Ejecución

### 🐧 En Linux

1. **Instalar dependencias y ejecutar:**
   ```bash
   pip install -r requirements.txt
   python3 main.py
   ```

2. **Generar Binario Portátil:**
   ```bash
   ./build.sh
   ```
   El ejecutable resultante se ubicará en `dist/CustomMusicPlayer`.

---

### 🪟 En Windows (10 / 11)

1. **Instalar dependencias y ejecutar:**
   ```cmd
   pip install -r requirements-windows.txt
   python main.py
   ```

2. **Generar Ejecutable `.exe`:**
   Ejecuta el script `build_windows.bat` o compila con PyInstaller:
   ```cmd
   build_windows.bat
   ```
   *(O manualmente con: `pyinstaller --noconfirm CustomMusicPlayer.spec`)*
   El ejecutable quedará listo en `dist\CustomMusicPlayer.exe`.

---

### 📱 En Android

1. **Instalación Directa:**
   * Instala el archivo [`CustomMusicPlayer.apk`](file:///home/phame/.local/bin/custom-music-player/CustomMusicPlayer.apk) en tu dispositivo.
2. **Entorno de Desarrollo:**
   ```bash
   cd mobile
   npx expo start
   ```

---

## 📄 Licencia

Este proyecto está distribuido bajo licencia abierta para uso personal y comunitario.
