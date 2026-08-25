# Custom Music Player — Neon Sound Experience 🎧⚡

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-MPRIS2-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Windows](https://img.shields.io/badge/Windows-SMTC%20Native-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Audio%20Stream-FF0000?style=for-the-badge&logo=youtube&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blueviolet?style=for-the-badge)

<p align="center">
  <b>Reproductor de música de escritorio de alto rendimiento, ultra personalizable y estéticamente refinado.</b><br>
  Diseñado con una estética <b>Negro Azabache & Acentos Neón Reactivos</b>, soporte integral de <b>traducción de letras en tiempo real (Online & Offline)</b>, visualizadores reactivos de audio (<i>Trap Nation</i>, Vinilo Hi-Fi y Tarjeta Neón), importación/descarga desde <b>YouTube y Spotify</b>, y control multimedia nativo del sistema operativo (<b>MPRIS2 / SMTC</b>).
</p>

</div>

---

## 📑 Tabla de Contenidos

1. [📸 Tres Modos de Visualización Adaptables](#-tres-modos-de-visualización-adaptables)
2. [🌐 Motor de Traducción de Letras (Online & Offline)](#-motor-de-traducción-de-letras-online--offline)
3. [🔗 Streaming y Descarga desde YouTube & Spotify](#-streaming-y-descarga-desde-youtube--spotify)
4. [🌊 Visualizadores de Audio en Modo Expandido](#-visualizadores-de-audio-en-modo-expandido)
5. [🎨 Personalización Visual & Formas Geométricas](#-personalización-visual--formas-geométricas)
6. [🔤 Tipografías Independientes por Modo](#-tipografías-independientes-por-modo)
7. [🚀 Características Principales y Arquitectura](#-características-principales-y-arquitectura)
8. [⌨️ Atajos de Teclado y Controles Multimedia](#️-atajos-de-teclado-y-controles-multimedia)
9. [📁 Estructura del Proyecto](#-estructura-del-proyecto)
10. [🛠️ Instalación y Compilación](#️-instalación-y-compilación)
11. [⚙️ Rutas de Configuración y Datos](#️-rutas-de-configuración-y-datos)
12. [📄 Licencia](#-licencia)

---

## 📸 Tres Modos de Visualización Adaptables

Cada modo cuenta con su **propia configuración independiente de tema, color de acento, tipografía, fondo de pantalla y forma de carátula**, permitiendo alternar entre ellos al instante sin alterar las preferencias de los demás:

| Modo | Dimensiones | Descripción & Características |
| :--- | :--- | :--- |
| **Modo Pequeño (Normal)** | `350 × 430 px` | Widget flotante vertical minimalista para el escritorio. Carátula centrada, barras de ecualizador vertical al ritmo de la música con degradado del tema activo, marquesina con título y artista, deslizador de volumen Y2K de alta precisión con control de rueda del ratón, botones de transporte circulares simétricos y menú unificado con acceso a playlist ligera y gestor de enlaces. |
| **Modo Compacto** | `640 × 260 px` | Layout horizontal elegante inspirado en sistemas Hi-Fi de alta gama. Carátula en alta resolución con forma geométrica personalizable, visualizador de onda EKG interactivo, barra de progreso dual (`0:15` / `3:27`), botones de favoritos (`♥`), aleatorio (`⇄`), repetición (`A→`) y panel de utilidades en cabecera. |
| **Modo Expandido** | `Ventana Completa` | Experiencia inmersiva con barra lateral de navegación, explorador de biblioteca con buscador en tiempo real, gestor de playlists, sección dedicada **"En Reproducción"** con 3 estilos de visualizador seleccionables, visor de letras sincronizadas a 60 FPS y selector dinámico de traducción multilingüe. |

---

## 🌐 Motor de Traducción de Letras (Online & Offline)

El reproductor incorpora un sistema inteligente de sincronización, traducción y visualización de letras ([`lyrics_translator.py`](lyrics_translator.py), [`lyrics_manager.py`](lyrics_manager.py), [`ui/lyrics_view_widget.py`](ui/lyrics_view_widget.py)):

* 🌍 **10 Idiomas Soportados:** Español (`es`), Inglés (`en`), Portugués (`pt`), Francés (`fr`), Italiano (`it`), Alemán (`de`), Japonés (`ja`), Chino (`zh`), Ruso (`ru`) y Coreano (`ko`).
* ⚡ **Traducción Online Inteligente:** Motor Google Web GTX optimizado con procesamiento por lotes delimitado y validación estricta de cardinalidad para asegurar correspondencia 1:1 con los timestamps LRC originales.
* 📦 **Traducción Offline (Argos Translate):** Soporte de modelos locales para traducción sin necesidad de conexión a internet.
* 🔄 **Descarga Automática de Paquetes:** Si se activa la traducción hacia un idioma cuyo modelo offline no esté instalado, el sistema descarga e instala el paquete `.argosmodel` en segundo plano con diálogo de progreso no bloqueante.
* 💾 **Caché Relacional SQLite:** Las letras traducidas se almacenan en la tabla `lyrics_translations` para consulta instantánea sin consumo repetitivo de ancho de banda.
* 🎯 **Sincronización & Scroll Suave:** Desplazamiento animado con curva cúbica hacia el verso activo a 60 FPS, resaltado visual del verso en curso y salto de reproducción instantáneo al hacer clic en cualquier línea.

---

## 🔗 Streaming y Descarga desde YouTube & Spotify

El reproductor cuenta con un motor de resolución y descarga de audio online ([`online_stream_manager.py`](online_stream_manager.py), [`ui/add_link_dialog.py`](ui/add_link_dialog.py)):

* ⚡ **Reproducción Online Inmediata:** Transmite audio directo en alta calidad (AAC / M4A) utilizando `yt-dlp` sin descargar el archivo previamente en disco.
* 📥 **Descarga Offline Automatizada:** Descarga el audio en segundo plano, lo convierte a MP3 a 320 kbps mediante FFmpeg, incrusta metadatos ID3 completos (título, artista, álbum) y carátula en alta definición, integrándolo automáticamente en la carpeta de música activa.
* 📋 **Detección Automática de Portapapeles:** Al abrir el diálogo (<kbd>Ctrl+L</kbd> o <kbd>Ctrl+U</kbd>), detecta y valida automáticamente cualquier enlace copiado de YouTube o Spotify.
* 📁 **Selector de Carpeta de Destino:** Opción para cambiar rápidamente el directorio de destino antes de iniciar la descarga.
* 🧹 **Limpieza Inteligente de Metadatos:** Analiza y normaliza títulos de YouTube (eliminando etiquetas como `(Official Video)`, `(Audio)`, `(Lyrics)`, etc.) para optimizar la búsqueda automática de carátulas y letras sincronizadas.

---

## 🌊 Visualizadores de Audio en Modo Expandido

En la sección **En Reproducción** del Modo Expandido, es posible alternar entre tres estilos de visualización reactiva:

1. 🌌 **Ondas Radiales (*Trap Nation Style* — `radial_waves`):**
   * 72 barras de espectro de audio distribuidas radialmente alrededor de la carátula circular central.
   * Ondas de choque concéntricas expansivas reactivas a las frecuencias graves.
   * Degradado angular cromático sincronizado con la paleta de acento del tema.
2. 📻 **Tocadiscos Hi-Fi Vinilo (`vinyl`):**
   * Disco de vinilo animado con texturas de surcos, reflejos de luz y carátula central rotatoria.
   * Brazo fonocaptor metálico articulado que se posiciona físicamente sobre el disco al reproducir y regresa a su base al detenerse.
3. 🔲 **Tarjeta Neón Flotante (`card_glow`):**
   * Tarjeta de álbum suspendida con iluminación perimetral neón reactiva y barras de ecualización horizontales dinámicas.

---

## 🎨 Personalización Visual & Formas Geométricas

### 📐 Formas de Carátula Personalizables
En los tres modos de visualización se puede configurar de forma **100% independiente** la forma de la carátula ([`ui/image_cache.py`](ui/image_cache.py)):
* 🔘 **Circular (`circle`):** Recorte circular perfecto con borde iluminado en el color de acento.
* 🔲 **Cuadrada con Esquinas Redondeadas (`rounded`):** Curvas suaves con resplandor perimetral sutil.
* 💖 **Corazón (`heart`):** Silueta vectorial simétrica para un toque estético diferenciador.

### 🌈 Paleta Dinámica y Fondos de Pantalla
* **Extractor de Color Dominante ([`ui/color_extractor.py`](ui/color_extractor.py)):** Genera automáticamente degradados armoniosos basados en los tonos de la carátula o el fondo activo.
* **Carrusel de Fondos con Cross-Fade:** Ciclo automático de imágenes de fondo personalizables con transición suave y monitoreo en tiempo real del directorio mediante `QFileSystemWatcher`.
* **Panel de Personalización Unificado ([`ui/personalization_dialog.py`](ui/personalization_dialog.py)):** Ajuste de acentos de color, degradados, fondos, formas de carátula y estilos de visualizador.

---

## 🔤 Tipografías Independientes por Modo

Mediante el módulo [`ui/font_manager.py`](ui/font_manager.py), cada modo puede utilizar una tipografía distinta:

* **Exploración Automática:** Escanea fuentes instaladas en el sistema operativo y fuentes locales en carpetas personalizadas (ej. `~/Documentos/tipografia` o carpetas del usuario).
* **Aplicación en Cascada Dinámica:** Al seleccionar una tipografía, se actualizan al instante todos los elementos de la interfaz: títulos, marquesinas, listas, botones, modales emergentes y letras de canciones.

---

## 🚀 Características Principales y Arquitectura

### 🎵 Motor de Audio Nativo & Integración Multimedia
* **Motor de Audio de Alta Fidelidad ([`audio_engine.py`](audio_engine.py)):** Basado en `PyQt6.QtMultimedia` con soporte para **FLAC, MP3, WAV, OGG, AAC, M4A, OPUS** y flujos directos HTTP/HTTPS.
* **Servidor D-Bus MPRIS2 en Linux ([`mpris_server.py`](mpris_server.py)):** Control total desde applets del sistema (GNOME, KDE Plasma, Waybar, etc.) con saneamiento de Object Paths y respuesta inmediata a teclas multimedia.
* **Soporte Nativo SMTC en Windows ([`win_media_client.py`](win_media_client.py)):** Integración completa con el System Media Transport Controls de Windows 10/11 mediante `winsdk`.
* **Buscador en Tiempo Real ([`ui/music_home_view.py`](ui/music_home_view.py)):** Barra de búsqueda con filtrado instantáneo por título, artista o álbum en la biblioteca completa.
* **Gestión de Playlists & Favoritos:** Creación, edición, eliminación y reproducción de listas personalizadas y canciones favoritas.

### 💾 Base de Datos & Persistencia ([`database_manager.py`](database_manager.py))
* **SQLite en Modo WAL:** Esquema relacional con claves foráneas, transacciones ACID e índices optimizados para búsquedas instantáneas.
* **Worker FIFO Asíncrono:** Hilo dedicado en segundo plano para operaciones de escritura, evitando bloqueos en la interfaz y en el flujo de audio.
* **Gestión Canónica de Pistas:** Identificación persistente mediante hash SHA-256 de metadatos normalizados (NFC) y resolución automática de duplicados o cambios de ruta.
* **Estadísticas de Uso:** Registro histórico de reproducciones, artistas más escuchados, álbumes más populares y pistas frecuentes.

---

## ⌨️ Atajos de Teclado y Controles Multimedia

Optimizado para responder a las **teclas multimedia de hardware y combinaciones Fn (`Fn + F5..F8`)** emitidas por teclados gamer y multimedia, funcionando en segundo plano sin interferir con otras aplicaciones:

| Control / Tecla | Código / Modificador | Acción Ejecutada |
| :--- | :--- | :--- |
| **`Fn + F7`** (o ⏯️ Play-Pause) | `Key_MediaPlay` / `MediaTogglePlayPause` | **Reproducir / Pausar (alternar)** |
| **`Fn + F8`** (o ⏭️ Next) | `Key_MediaNext` | **Pista Siguiente** |
| **`Fn + F6`** (o ⏮️ Previous) | `Key_MediaPrevious` | **Pista Anterior** |
| **`Fn + F5`** (o ⏹️ Stop) | `Key_MediaStop` | **Detener Reproducción** |
| **Rueda / Dial / Roller de Volumen** | `Key_VolumeUp` / `Key_VolumeDown` | **Ajustar Volumen (±5%)** |
| **Click en Dial / Botón Mute** | `Key_VolumeMute` | **Silenciar / Restaurar Volumen** |
| **`Espacio`** | `Key_Space` | **Play / Pause** *(con ventana enfocada)* |
| **`Ctrl + Flecha Derecha`** | `Ctrl + Right` | **Avance rápido (+5s)** |
| **`Ctrl + Flecha Izquierda`** | `Ctrl + Left` | **Retroceso rápido (-5s)** |
| **`Ctrl + L` / `Ctrl + U`** | `Ctrl + L` / `Ctrl + U` | **🔗 Agregar / Descargar Link de YouTube o Spotify** |
| **`Ctrl + F`** | `Ctrl + F` | **Marcar / Desmarcar Canción como Favorita** |
| **`Ctrl + B`** | `Ctrl + B` | **Cambiar Fondo de Pantalla Inmediatamente** |
| **`Ctrl + T`** | `Ctrl + T` | **Alternar Modo Siempre Visible (*Always on Top*)** |
| **`Ctrl + C`** | `Ctrl + C` | **Alternar Modo (*Pequeño / Compacto / Expandido*)** |
| **`Ctrl + H` / `F12` / `Esc`** | `Ctrl + H` / `F12` / `Esc` | **Mostrar / Ocultar en Bandeja del Sistema** |
| **`Ctrl + O`** | `Ctrl + O` | **Abrir Selector de Carpeta de Música** |

---

## 📁 Estructura del Proyecto

```text
custom-music-player/
├── main.py                     # Punto de entrada principal (Qt App, MPRIS2/SMTC, bandeja del sistema)
├── audio_engine.py             # Motor de audio nativo (PyQt6 QMediaPlayer / FFmpeg / soporte local y streams)
├── database_manager.py         # Persistencia SQLite (WAL) para biblioteca, historial, playlists y letras
├── config_manager.py           # Gestor de configuración JSON multiplataforma (%APPDATA% / XDG)
├── library_manager.py          # Escaneo asíncrono y extracción de metadatos de biblioteca musical
├── lyrics_manager.py           # Gestor de letras (.lrc) con limpieza de metadatos y caché local
├── lyrics_translator.py        # Motor de traducción Online (GTX) y Offline (Argos Translate)
├── online_stream_manager.py    # Motor de resolución y descarga de audio para YouTube y Spotify (yt-dlp)
├── mpris_server.py             # Servidor D-Bus MPRIS2 con soporte de Object Paths saneados (Linux)
├── win_media_client.py         # Integración nativa con Windows SMTC (Windows)
├── CustomMusicPlayer.spec       # Especificación PyInstaller para empaquetado y distribución
├── build.sh                    # Script de compilación para binario ejecutable en Linux
├── build_windows.bat           # Script de compilación para ejecutable en Windows
├── requirements.txt            # Dependencias de Python multiplataforma
│
├── assets/                     # Recursos gráficos e iconos de la aplicación
│   ├── icon.ico
│   └── icon.png
│
└── ui/                         # Interfaz Gráfica PyQt6
    ├── player_widget.py        # Widget flotante principal (Modo Pequeño y Modo Compacto)
    ├── expanded_view.py        # Vista expandida con biblioteca, ondas radiales, tocadiscos y letras
    ├── music_home_view.py      # Explorador de biblioteca, canciones, álbumes, artistas y playlists
    ├── add_link_dialog.py      # Diálogo modal para reproducir y descargar enlaces de YouTube/Spotify
    ├── font_manager.py         # Gestor dinámico de tipografías del sistema y locales
    ├── context_menus.py        # Menús contextuales unificados para canciones, listas y opciones rápidas
    ├── personalization_dialog.py # Diálogo unificado de personalización (colores, fuentes, fondos, visualizadores)
    ├── small_playlist.py       # Lista de canciones ligera con delegado personalizado
    ├── unified_mode_menu.py    # Menú unificado de cambio de modos y accesos rápidos
    ├── y2k_volume_slider.py    # Deslizador de volumen estilo Y2K con tirador de estrella
    ├── lyrics_view_widget.py   # Visualizador interactivo de letras sincronizadas con menú de traducción 🌐
    ├── styles.py               # Tokens de diseño, constantes y generador de estilos QSS
    ├── color_extractor.py      # Extractor de colores dominantes y generador de degradados
    ├── marquee_label.py        # Etiqueta con desplazamiento horizontal animado para títulos largos
    ├── equalizer_widget.py     # Indicador visual de barras de ecualización reactivas
    └── image_cache.py          # Gestor de caché y renderizado acelerado de carátulas e imágenes
```

---

## 🛠️ Instalación y Compilación

### 📋 Requisitos Previos

* **Python 3.10 o superior**
* **FFmpeg:** Requerido para conversión y descarga de audio de alta fidelidad.
  * **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
  * **Linux (Arch):** `sudo pacman -S ffmpeg`
  * **Windows:** Instalar mediante `winget install Gyan.FFmpeg` o `choco install ffmpeg`.

---

### 🐧 En Linux

1. **Instalar dependencias y ejecutar:**
   ```bash
   pip install -r requirements.txt
   python3 main.py
   ```

2. **Generar Binario Portátil:**
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
   El ejecutable se generará en `dist/CustomMusicPlayer`.

---

### 🪟 En Windows (10 / 11)

1. **Instalar dependencias y ejecutar:**
   ```cmd
   pip install -r requirements.txt
   python main.py
   ```

2. **Generar Ejecutable `.exe`:**
   ```cmd
   build_windows.bat
   ```
   El ejecutable se generará en `dist\CustomMusicPlayer.exe`.

---

## ⚙️ Rutas de Configuración y Datos

La aplicación sigue los estándares de almacenamiento por plataforma:

* **🐧 Linux:**
  * Configuración y Base de Datos: `~/.config/custom-music-player/`
* **🪟 Windows:**
  * Configuración y Base de Datos: `%APPDATA%\custom-music-player\`

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia MIT para uso personal y comunitario.
