# Custom Music Player — Red World Edition 🎧🖤

Un reproductor de música de escritorio y móvil moderno, ultra liviano y personalizable (**Linux, Windows & Android**), diseñado con estética **Negro Azabache & Colores Neón Reactivos**, transiciones suaves *cross-fade* de fondos, visualizadores de audio reactivos al ritmo de la música, carátula nítida en alta resolución con formas geométricas personalizables (**Circular, Cuadrada, Corazón**), motor de audio nativo de alto rendimiento y control total vía **MPRIS2 / Teclas Multimedia**.

---

## 📸 Tres Modos de Visualización Adaptables e Independientes

Cada modo cuenta con su **propia configuración de tema, color de acento, fondo de pantalla y forma de carátula**, permitiendo alternar entre ellos al instante sin afectar la personalización de los demás.

| Modo | Dimensiones | Descripción & Características |
| :--- | :--- | :--- |
| **Modo Pequeño (Normal)** | `350 × 430 px` | Widget flotante vertical ideal para escritorio. Carátula centrada con barras de ecualizador vertical al ritmo de la música integradas, marquesina con título y artista, deslizador de volumen Y2K de alta precisión con control de rueda del ratón, botones de transporte simétricos y menú unificado con lista de canciones. |
| **Modo Compacto** | `640 × 260 px` | Layout horizontal elegante inspirado en reproductores Hi-Fi. Carátula de alta resolución (220×220px) con forma personalizable, visualizador de onda EKG interactivo, barra de progreso dual (`0:15` / `3:27`), acceso a lista `☰♪`, favoritos `♥`, aleatorio `⇄`, repetición `A→` y utilidades en cabecera `[⌄] ... [🔊] [📊] [⋮]`. |
| **Modo Expandido** | `Ventana Completa` | Vista de biblioteca inmersiva con barra lateral colapsable, explorador de biblioteca con buscador en tiempo real, gestión completa de playlists y sección dedicada **"En Reproducción"** con carátula ampliada (330px), ecualizador de barras verticales de alta definición con degradado de color y controles completos. |

---

## 📐 Formas Geométricas de Carátula Personalizables

En los tres modos de visualización se puede seleccionar de manera **100% independiente** la forma estética de la carátula:

* 🔘 **Redonda / Circular (`circle`):** Recorte circular perfecto con borde perimetral iluminado en el color de acento del tema.
* 🔲 **Cuadrada con Esquinas Redondeadas (`rounded`):** Estilo moderno con curvas suaves y resplandor sutil.
* 💖 **Corazón (`heart`):** Silueta vectorial de curvas suaves simétricas para una estética personalizada.

---

## 🚀 Características Principales

### 🎵 Motor de Audio Nativo & Integración Multimedia
- **Motor de Audio Autónomo:** Basado en `PyQt6.QtMultimedia` con decodificación directa vía FFmpeg (soporta **FLAC, MP3, WAV, OGG, AAC, M4A, OPUS** y más).
- **Servidor y Cliente MPRIS2 (Linux DBus):** Control total desde applets del sistema (GNOME, KDE Plasma, Waybar, etc.) y respuesta inmediata a teclas de hardware multimedia (`Play/Pause`, `Next`, `Prev`, `Stop`).
- **Lista de Canciones Instantánea:** Vista de lista ligera y optimizada ([`SmallPlaylistPage`](ui/small_playlist.py)) con `QStyledItemDelegate` nativo para búsqueda y filtrado en tiempo real sin retrasos ni consumo excesivo de memoria.
- **Gestión Completa de Listas de Reproducción:** Creación, edición, eliminación y reproducción de playlists personalizadas guardadas automáticamente en disco.

### 🎨 Estética Neón & Personalización Visual
- **Temas Neón Reactivos e Independientes:** Extracción automática de paleta de color dominante a partir de la carátula o fondo activo, con soporte para paletas sólidas o degradados multi-parada.
- **Diálogo de Personalización Avanzado ([`PersonalizationDialog`](ui/personalization_dialog.py)):** Panel unificado para configurar color de acento, degradados, fondos de pantalla, carátulas y forma geométrica por cada modo.
- **Carrusel de Fondos con *Cross-Fade*:** Ciclo automático de imágenes de fondo personalizables con transición suave y monitoreo en tiempo real del directorio mediante `QFileSystemWatcher`.
- **Deslizador de Volumen Y2K Calibrado:** Control preciso de 0% a 100% con respuesta táctil y ajuste mediante scroll del ratón (±5%).
- **Fijación Flotante Opcional:** Ejecución normal por defecto o modo fijado (*Always on Top*) alternable con `Ctrl+T`.

---

## ⌨️ Atajos de Teclado y Controles

| Atajo | Acción |
| :--- | :--- |
| `Espacio` / `Media Play-Pause` | Reproducir / Pausar (alternar) |
| `Flecha Izquierda` / `Media Prev` | Pista Anterior |
| `Flecha Derecha` / `Media Next` | Pista Siguiente |
| `Flecha Arriba` / `Flecha Abajo` | Subir / Bajar Volumen (±5%) |
| `Rueda del Ratón sobre Volumen` | Ajustar volumen progresivamente |
| `Ctrl+F` | Marcar / Desmarcar Canción como Favorita |
| `Ctrl+C` / `F11` | Alternar entre **Modo Compacto**, **Modo Pequeño** y **Modo Expandido** |
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
│   ├── expanded_view.py       # Vista expandida de biblioteca, playlists y visualizador EKG
│   ├── personalization_dialog.py # Diálogo de personalización multi-modo (colores, fondos, formas de carátula)
│   ├── small_playlist.py      # Lista de canciones ultra rápida con SmallPlaylistDelegate
│   ├── unified_mode_menu.py   # Menú unificado de modos y canciones
│   ├── styles.py              # Tokens de diseño, constantes de dimensiones y generador de estilos QSS
│   ├── color_extractor.py     # Extractor de colores vibrantes y paletas degradadas automáticas
│   ├── gradient_dialog.py     # Diálogo de personalización de temas y colores degradados
│   ├── y2k_volume_slider.py   # Deslizador de volumen con estilo personalizado y soporte de rueda de ratón
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
   * Instala el archivo `CustomMusicPlayer.apk` en tu dispositivo.
2. **Entorno de Desarrollo:**
   ```bash
   cd mobile
   npx expo start
   ```

---

## 📄 Licencia

Este proyecto está distribuido bajo licencia abierta para uso personal y comunitario.
