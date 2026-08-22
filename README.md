# Custom Music Player — Red World Edition 🎧🖤

Un reproductor de música de escritorio y móvil moderno, ultra liviano y personalizable (**Linux, Windows & Android**), diseñado con estética **Negro Azabache & Colores Neón Reactivos**, soporte integral de **traducción de letras en tiempo real (Online & Offline)**, visualizadores de audio reactivos al ritmo de la música, importación y descarga directa desde **YouTube y Spotify**, tocadiscos analógico animado con brazo fonocaptor interactivo, espectro de ondas radiales estilo *Trap Nation*, carátula nítida en alta resolución con formas geométricas personalizables (**Circular, Cuadrada, Corazón**), tipografías independientes por modo, persistencia relacional en **SQLite (WAL)**, motor de audio nativo de alto rendimiento y control total vía **MPRIS2 / Teclas Multimedia**.

---

## 📸 Tres Modos de Visualización Adaptables e Independientes

Cada modo cuenta con su **propia configuración de tema, color de acento, tipografía, fondo de pantalla y forma de carátula**, permitiendo alternar entre ellos al instante sin afectar la personalización de los demás.

| Modo | Dimensiones | Descripción & Características |
| :--- | :--- | :--- |
| **Modo Pequeño (Normal)** | `350 × 430 px` | Widget flotante vertical ideal para escritorio. Carátula centrada con barras de ecualizador vertical al ritmo de la música con degradado del tema activo, marquesina con título y artista, deslizador de volumen Y2K de alta precisión con control de rueda del ratón, botones de transporte circulares simétricos y menú unificado con lista de canciones y gestor de enlaces. |
| **Modo Compacto** | `640 × 260 px` | Layout horizontal elegante inspirado en reproductores Hi-Fi. Carátula de alta resolución (220×220px) con forma personalizable, visualizador de onda EKG interactivo, barra de progreso dual (`0:15` / `3:27`), acceso a lista `☰♪`, favoritos `♥`, aleatorio `⇄`, repetición `A→` y utilidades en cabecera `[⌄] ... [🔊] [📊] [⋮]`. |
| **Modo Expandido** | `Ventana Completa` | Vista de biblioteca inmersiva con barra lateral de navegación, explorador de biblioteca con buscador glassmorphic en tiempo real, gestión de playlists, sección dedicada **"En Reproducción"** con 3 estilos de visualizador seleccionables (Ondas Radiales, Tocadiscos Vinilo, Tarjeta Neón), visor de letras sincronizadas a 60 FPS y motor de traducción en vivo. |

---

## 🔗 Reproducción & Descarga desde YouTube y Spotify (Online & Offline)

El reproductor incorpora un motor integral de resolución y descarga de música online ([`online_stream_manager.py`](online_stream_manager.py), [`ui/add_link_dialog.py`](ui/add_link_dialog.py)):

* ⚡ **Reproducción Online Inmediata:** Transmite audio directo en alta calidad (AAC / M4A) sin consumir espacio en disco.
* 📥 **Descarga Offline Automatizada:** Descarga el audio, lo convierte a MP3 320 kbps mediante FFmpeg, incrusta metadatos ID3 completos y carátula en alta definición, y lo almacena automáticamente en la carpeta de música activa del usuario.
* 📋 **Detección Automática de Portapapeles:** Al abrir el diálogo (<kbd>Ctrl+L</kbd> o <kbd>Ctrl+U</kbd>), si tienes un enlace copiado de YouTube o Spotify, se detecta y valida al instante.
* 📁 **Selector de Carpeta de Destino:** Visualización clara de la carpeta destino de guardado con opción de cambio rápido.
* 🧹 **Limpieza Inteligente de Metadatos:** Analiza y normaliza automáticamente títulos de YouTube (eliminando etiquetas como `(Oficial Video)`, `(Traducida al Español)`, `[Audio]`, etc.) para permitir la búsqueda instantánea de letras sincronizadas.

---

## 🌊 Visualizadores de Audio en Modo Expandido

En la sección **En Reproducción** del Modo Expandido, puedes alternar entre tres estilos de visualización reactiva:

1. 🌌 **Ondas Radiales (*Trap Nation Style* — `radial_waves`):**
   * 72 barras de espectro de audio distribuidas radialmente alrededor de la carátula central.
   * Ondas de choque concéntricas expansivas que reaccionan al ritmo de los graves.
   * Degradado angular cromático suave adaptado a la paleta del tema seleccionado.
2. 📻 **Tocadiscos Hi-Fi Vinilo (`vinyl`):**
   * Disco de vinilo animado con surcos fotorealistas, reflejos de luz y carátula central rotatoria.
   * Brazo fonocaptor metálico articulado que se posiciona sobre el disco al reproducir y regresa al detenerse.
3. 🔲 **Tarjeta Neón Flotante (`card_glow`):**
   * Tarjeta de álbum suspendida con iluminación perimetral neón reactiva y barras de ecualización horizontales.

---

## 🔤 Tipografías Personalizables e Independientes por Modo

Mediante el módulo [`ui/font_manager.py`](ui/font_manager.py), cada modo puede utilizar una tipografía distinta:

* **Exploración Automática:** Escanea fuentes instaladas en el sistema operativo y fuentes locales en carpetas personalizadas (como `~/Documentos/tipografia`).
* **Aplicación en Cascada:** Al cambiar la tipografía, se actualizan dinámicamente todos los elementos de la interfaz: títulos, marquesinas, listas, botones, modales emergentes y letras de canciones.

---

## 🌐 Motor de Traducción de Letras Online & Offline

El reproductor incorpora un sistema inteligente de traducción y sincronización de letras ([`lyrics_translator.py`](lyrics_translator.py), [`ui/lyrics_view_widget.py`](ui/lyrics_view_widget.py)):

* **10 Idiomas Soportados:** Español (`es`), Inglés (`en`), Portugués (`pt`), Francés (`fr`), Italiano (`it`), Alemán (`de`), Japonés (`ja`), Chino (`zh`), Ruso (`ru`) y Coreano (`ko`).
* **Traducción Online Inteligente:** Motor Google Web GTX con batching delimitado y validación estricta de cardinalidad para asegurar correspondencia 1:1 con los timestamps LRC originales.
* **Traducción Offline (Argos Translate):** Soporte de modelos locales en disco para traducción sin conexión a internet.
* **Descarga Automática de Paquetes:** Si el usuario activa traducción a un idioma cuyo modelo offline no esté instalado, la aplicación descarga e instala el paquete `.argosmodel` en segundo plano con diálogo de progreso no bloqueante.
* **Caché Relacional SQLite:** Las letras traducidas se persisten en la tabla `lyrics_translations` para visualización instantánea en reproducciones futuras.
* **Sincronización & Scroll Suave:** Desplazamiento animado con curva cúbica hacia la frase en reproducción activa, resaltado visual y salto de tiempo al hacer clic en cualquier verso.

---

## 📐 Formas Geométricas de Carátula Personalizables

En los tres modos de visualización se puede seleccionar de manera **100% independiente** la forma estética de la carátula:

* 🔘 **Redonda / Circular (`circle`):** Recorte circular perfecto con borde perimetral iluminado en el color de acento del tema.
* 🔲 **Cuadrada con Esquinas Redondeadas (`rounded`):** Estilo moderno con curvas suaves y resplandor sutil.
* 💖 **Corazón (`heart`):** Silueta vectorial de curvas suaves simétricas para una estética personalizada.

---

## 🚀 Características Principales

### 🎵 Motor de Audio Nativo & Integración Multimedia
- **Motor de Audio Autónomo ([`audio_engine.py`](audio_engine.py)):** Basado en `PyQt6.QtMultimedia` con decodificación directa vía FFmpeg (soporta **FLAC, MP3, WAV, OGG, AAC, M4A, OPUS** y flujos directos HTTP/HTTPS).
- **Servidor y Cliente MPRIS2 (Linux DBus) ([`mpris_server.py`](mpris_server.py)):** Control total desde applets del sistema (GNOME, KDE Plasma, Waybar, etc.) con saneamiento estricto de Object Paths y respuesta inmediata a teclas multimedia de hardware.
- **Buscador Glassmorphic en Biblioteca y Música ([`ui/expanded_view.py`](ui/expanded_view.py)):** Barra de búsqueda con filtrado instantáneo por título, artista o álbum y selección de pistas con precisión de 100%.
- **Gestión Completa de Listas de Reproducción:** Creación, edición, eliminación y reproducción de playlists personalizadas.

### 💾 Base de Datos & Persistencia de Biblioteca ([`database_manager.py`](database_manager.py))
- **Base de Datos SQLite (WAL Mode):** Esquema versionado con Foreign Keys y transacciones ACID.
- **Worker de Escritura en Cola FIFO:** Hilo persistente en segundo plano para evitar bloqueos del hilo principal de audio y UI.
- **Gestión Canónica de Pistas:** Identificación persistente mediante hash SHA256 de metadatos normalizados (NFC) y resolución automática de duplicados o cambios de ruta.
- **Estadísticas de Uso:** Registro histórico de reproducciones, artistas más escuchados, álbumes más populares y pistas frecuentes.

### 🎨 Estética Neón & Personalización Visual
- **Temas Neón Reactivos e Independientes:** Extracción automática de paleta de color dominante a partir de la carátula o fondo activo, con degradados multi-parada fluidos.
- **Diálogo de Personalización Avanzado ([`ui/personalization_dialog.py`](ui/personalization_dialog.py)):** Panel unificado para configurar color de acento, degradados, fondos de pantalla, carátulas, tipografías y estilo de visualizador expandido.
- **Carrusel de Fondos con *Cross-Fade*:** Ciclo automático de imágenes de fondo personalizables con transición suave y monitoreo en tiempo real del directorio mediante `QFileSystemWatcher`.
- **Deslizador de Volumen Y2K Calibrado ([`ui/y2k_volume_slider.py`](ui/y2k_volume_slider.py)):** Control preciso de 0% a 100% con respuesta táctil y ajuste mediante scroll del ratón (±5%).
- **Fijación Flotante Opcional:** Ejecución normal por defecto o modo fijado (*Always on Top*) alternable con `Ctrl+T`.

---

## ⌨️ Atajos de Teclado y Controles Multimedia (Compatibilidad Gamer Sin Interferencias)

El reproductor está optimizado para responder a las **teclas multimedia de hardware y combinaciones Fn (`Fn + F5..F8`)** emitidas por teclados gamer y multimedia, funcionando en segundo plano sin interceptar teclas estándar en navegadores, editores ni juegos.

| Control / Tecla | Código de Hardware | Acción Ejecutada |
| :--- | :--- | :--- |
| **`Fn + F7`** (o ⏯️ Play-Pause) | `Key_MediaPlay` / `MediaTogglePlayPause` | **Reproducir / Pausar (alternar)** |
| **`Fn + F8`** (o ⏭️ Next) | `Key_MediaNext` | **Pista Siguiente** |
| **`Fn + F6`** (o ⏮️ Previous) | `Key_MediaPrevious` | **Pista Anterior** |
| **`Fn + F5`** (o ⏹️ Stop) | `Key_MediaStop` | **Detener Reproducción** |
| **Rueda / Dial / Roller de Volumen** | `Key_VolumeUp` / `Key_VolumeDown` | **Ajustar Volumen (±5%)** |
| **Click en Dial / Botón Mute** | `Key_VolumeMute` | **Silenciar / Restaurar Volumen** |
| **`Espacio`** | `Key_Space` | **Play / Pause** *(solo con ventana enfocada)* |
| **`Ctrl + Flecha Derecha` / `Ctrl + Flecha Izquierda`** | Modificador `Ctrl` | **Avance / Retroceso rápido (±5s)** |
| **`Ctrl + L` / `Ctrl + U`** | Modificador `Ctrl` | **🔗 Agregar / Descargar Link de YouTube o Spotify** |
| **`Ctrl + F`** | Modificador `Ctrl` | **Marcar / Desmarcar Canción como Favorita** |
| **`Ctrl + B`** | Modificador `Ctrl` | **Cambiar Fondo de Pantalla Inmediatamente** |
| **`Ctrl + T`** | Modificador `Ctrl` | **Alternar Fijación Superior (*Always on Top*)** |
| **`Ctrl + C`** | Modificador `Ctrl` | **Alternar Modo (*Pequeño / Compacto / Expandido*)** |
| **`Ctrl + H` / `F12` / `Esc`** | Modificador `Ctrl` | **Mostrar / Ocultar en Bandeja del Sistema** |
| **`Ctrl + O`** | Modificador `Ctrl` | **Abrir Selector de Carpeta de Música** |

---

## 📁 Estructura del Proyecto

```text
custom-music-player/
├── main.py                     # Punto de entrada principal (Inicialización Qt, servidor MPRIS/SMTC y bandeja)
├── audio_engine.py             # Motor de audio nativo (PyQt6 QMediaPlayer / FFmpeg / soporte local y streams)
├── database_manager.py         # Persistencia SQLite (WAL) para biblioteca, historial, playlists y letras
├── config_manager.py           # Gestor de configuración JSON multiplataforma (%APPDATA% / XDG)
├── library_manager.py          # Escaneo asíncrono y extracción de metadatos de biblioteca musical
├── lyrics_manager.py           # Gestor de letras (.lrc) con limpieza de metadatos y caché local
├── lyrics_translator.py        # Motor de traducción Online (GTX) y Offline (Argos Translate)
├── online_stream_manager.py    # Motor de resolución y descarga de audio para YouTube y Spotify (yt-dlp)
├── mpris_server.py             # Servidor D-Bus MPRIS2 con soporte de Object Paths saneados
├── mpris_client.py             # Cliente MPRIS base para integración de escritorio en Linux
├── win_media_client.py         # Módulo de integración preliminar con Windows SMTC
├── player.py                   # Ejecutable / wrapper CLI alternativo de reproducción
├── CustomMusicPlayer.spec       # Especificación PyInstaller para compilación y empaquetado de escritorio
├── build.sh                    # Script de compilación para binario ejecutable en Linux
├── build_windows.bat           # Script de compilación para ejecutable en Windows
├── requirements.txt            # Dependencias de Python para Linux
├── requirements-windows.txt    # Dependencias de Python para Windows
│
├── ui/                         # Interfaz Gráfica PyQt6 de Escritorio
│   ├── player_widget.py        # Widget principal flotante (Modo Pequeño y Modo Compacto)
│   ├── expanded_view.py        # Vista expandida con biblioteca, ondas radiales, tocadiscos y letras
│   ├── music_home_view.py      # Explorador de biblioteca, canciones, álbumes, artistas y playlists
│   ├── add_link_dialog.py      # Diálogo modal para reproducir y descargar enlaces de YouTube/Spotify
│   ├── font_manager.py         # Gestor dinámico de tipografías del sistema y locales
│   ├── context_menus.py        # Menús contextuales unificados para canciones, listas y opciones rápidas
│   ├── personalization_dialog.py # Diálogo unificado de personalización (colores, fuentes, fondos, visualizadores)
│   ├── small_playlist.py       # Lista de canciones ligera con delegado custom optimizado
│   ├── unified_mode_menu.py    # Menú unificado de cambio de modos y acceso rápido
│   ├── y2k_volume_slider.py    # Deslizador de volumen estilo Y2K con tirador de estrella de 4 puntas
│   ├── lyrics_view_widget.py   # Visualizador interactivo de letras sincronizadas con menú de traducción 🌐
│   ├── styles.py               # Tokens de diseño, constantes de dimensiones y generador de estilos QSS
│   ├── color_extractor.py      # Extractor de colores dominantes y generador de degradados
│   ├── marquee_label.py        # Etiqueta con desplazamiento horizontal animado para títulos largos
│   ├── equalizer_widget.py     # Indicador visual de barras de ecualización reactivas
│   ├── elided_label.py         # Etiqueta con truncado inteligente por elipsis (...) según ancho disponible
│   └── gradient_dialog.py      # [Código legado / sin uso activo en el flujo actual de personalización]
│
└── mobile/                     # 📱 Aplicación Móvil (React Native / Expo SDK)
    ├── android/                # Proyecto nativo Gradle para Android
    ├── src/app/                # Pantallas principales, pestañas y ajustes móviles
    ├── assets/                 # Recursos gráficos, carátulas y fondos
    └── package.json            # Dependencias y scripts de compilación móvil
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
   ```cmd
   build_windows.bat
   ```
   El ejecutable quedará listo en `dist\CustomMusicPlayer.exe`.

---

### 📱 En Android

1. **Compilación del APK desde código fuente:**
   ```bash
   cd mobile/android
   ./gradlew assembleRelease
   ```
   El APK compilado se genera en `mobile/android/app/build/outputs/apk/release/app-release.apk`.

2. **Instalación Directa:**
   * Copia el APK compilado a tu dispositivo Android o descarga el instalador desde los releases del repositorio.

3. **Entorno de Desarrollo Móvil:**
   ```bash
   cd mobile
   npx expo start
   ```

---

## 📄 Licencia

Este proyecto está distribuido bajo licencia abierta para uso personal y comunitario.

