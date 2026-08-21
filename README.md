# Custom Music Player — Red World Edition 🎧🖤

Un reproductor de música de escritorio y móvil moderno, ultra liviano y personalizable (**Linux, Windows & Android**), diseñado con estética **Negro Azabache & Colores Neón Reactivos**, soporte integral de **traducción de letras en tiempo real (Online & Offline)**, visualizadores de audio reactivos al ritmo de la música, tocadiscos analógico animado con brazo fonocaptor interactivo, carátula nítida en alta resolución con formas geométricas personalizables (**Circular, Cuadrada, Corazón**), persistencia relacional en **SQLite (WAL)**, motor de audio nativo de alto rendimiento y control total vía **MPRIS2 / Teclas Multimedia**.

---

## 📸 Tres Modos de Visualización Adaptables e Independientes

Cada modo cuenta con su **propia configuración de tema, color de acento, fondo de pantalla y forma de carátula**, permitiendo alternar entre ellos al instante sin afectar la personalización de los demás.

| Modo | Dimensiones | Descripción & Características |
| :--- | :--- | :--- |
| **Modo Pequeño (Normal)** | `350 × 430 px` | Widget flotante vertical ideal para escritorio. Carátula centrada con barras de ecualizador vertical al ritmo de la música integradas, marquesina con título y artista, deslizador de volumen Y2K de alta precisión con control de rueda del ratón, botones de transporte circulares simétricos y menú unificado con lista de canciones. |
| **Modo Compacto** | `640 × 260 px` | Layout horizontal elegante inspirado en reproductores Hi-Fi. Carátula de alta resolución (220×220px) con forma personalizable, visualizador de onda EKG interactivo, barra de progreso dual (`0:15` / `3:27`), acceso a lista `☰♪`, favoritos `♥`, aleatorio `⇄`, repetición `A→` y utilidades en cabecera `[⌄] ... [🔊] [📊] [⋮]`. |
| **Modo Expandido** | `Ventana Completa` | Vista de biblioteca inmersiva con barra lateral colapsable, explorador de biblioteca con buscador en tiempo real, gestión completa de playlists, vista de tocadiscos animado con disco de vinilo y sección dedicada **"En Reproducción"** con visor de letras sincronizadas y motor de traducción en vivo. |

---

## 🌐 Motor de Traducción de Letras Online & Offline

El reproductor incorpora un sistema inteligente de traducción y sincronización de letras ([`lyrics_translator.py`](lyrics_translator.py), [`ui/lyrics_view_widget.py`](ui/lyrics_view_widget.py)):

* **10 Idiomas Soportados:** Español (`es`), Inglés (`en`), Portugués (`pt`), Francés (`fr`), Italiano (`it`), Alemán (`de`), Japonés (`ja`), Chino (`zh`), Ruso (`ru`) y Coreano (`ko`).
* **Traducción Online Inteligente:** Motor Google Web GTX con batching delimitado y validación estricta de cardinalidad para asegurar correspondencia 1:1 con los timestamps LRC originales.
* **Traducción Offline (Argos Translate):** Soporte de modelos locales en disco para traducción sin conexión a internet.
* **Descarga Automática de Paquetes (Opción A):** Si el usuario activa traducción a un idioma cuyo modelo offline no esté instalado, la aplicación descarga e instala el paquete `.argosmodel` en segundo plano mostrando un `QProgressDialog` no bloqueante con cancelación activa. Una vez completado, continúa la traducción automáticamente.
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
- **Motor de Audio Autónomo ([`audio_engine.py`](audio_engine.py)):** Basado en `PyQt6.QtMultimedia` con decodificación directa vía FFmpeg (soporta **FLAC, MP3, WAV, OGG, AAC, M4A, OPUS** y más).
- **Servidor y Cliente MPRIS2 (Linux DBus) ([`mpris_server.py`](mpris_server.py)):** Control total desde applets del sistema (GNOME, KDE Plasma, Waybar, etc.) y respuesta inmediata a teclas de hardware multimedia (`Play/Pause`, `Next`, `Prev`, `Stop`).
- **Lista de Canciones Instantánea ([`ui/small_playlist.py`](ui/small_playlist.py)):** Vista de lista ligera y optimizada con `QStyledItemDelegate` nativo para búsqueda y filtrado en tiempo real sin congelamiento de UI.
- **Gestión Completa de Listas de Reproducción:** Creación, edición, eliminación y reproducción de playlists personalizadas.

### 💾 Base de Datos & Persistencia de Biblioteca ([`database_manager.py`](database_manager.py))
- **Base de Datos SQLite (WAL Mode):** Esquema versionado con Foreign Keys y transacciones ACID.
- **Worker de Escritura en Cola FIFO:** Hilo persistente en segundo plano para evitar bloqueos del hilo principal de audio y UI.
- **Gestión Canónica de Pistas:** Identificación persistente mediante hash SHA256 de metadatos normalizados (NFC) y resolución automática de duplicados o cambios de ruta.
- **Estadísticas de Uso:** Registro histórico de reproducciones, artistas más escuchados, álbumes más populares y pistas frecuentes.

### 🎨 Estética Neón & Personalización Visual
- **Temas Neón Reactivos e Independientes:** Extracción automática de paleta de color dominante a partir de la carátula o fondo activo, con soporte para paletas sólidas o degradados multi-parada.
- **Diálogo de Personalización Avanzado ([`ui/personalization_dialog.py`](ui/personalization_dialog.py)):** Panel unificado para configurar color de acento, degradados, fondos de pantalla, carátulas y forma geométrica por cada modo.
- **Carrusel de Fondos con *Cross-Fade*:** Ciclo automático de imágenes de fondo personalizables con transición suave y monitoreo en tiempo real del directorio mediante `QFileSystemWatcher`.
- **Deslizador de Volumen Y2K Calibrado ([`ui/y2k_volume_slider.py`](ui/y2k_volume_slider.py)):** Control preciso de 0% a 100% con respuesta táctil y ajuste mediante scroll del ratón (±5%).
- **Fijación Flotante Opcional:** Ejecución normal por defecto o modo fijado (*Always on Top*) alternable con `Ctrl+T`.

---

## ⌨️ Atajos de Teclado y Controles (Compatibilidad Total con Teclados Gamer)

### 🎮 Distribuciones Gamer (60%, 65%, 75%, TKL, Full-Size & Teclas Multimedia)

| Categoría | Atajo / Tecla | Acción |
| :--- | :--- | :--- |
| **Multimedia & Dial Gamer** | ⏯️ `Media Play-Pause` / `Espacio` / `K` | Reproducir / Pausar (alternar) |
| | ⏭️ `Media Next` / `Flecha Der` / `L` / `]` / `>` / `.` | Pista Siguiente |
| | ⏮️ `Media Prev` / `Flecha Izq` / `J` / `[` / `<` / `,` | Pista Anterior |
| | ⏹️ `Media Stop` | Detener Reproducción |
| | 🔊 `Volume Up` (Rueda / Roller / Dial) / `Flecha Arr` / `+` / `=` / `PageUp` | Subir Volumen (+5%) |
| | 🔉 `Volume Down` (Rueda / Roller / Dial) / `Flecha Abj` / `-` / `_` / `PageDown` | Bajar Volumen (-5%) |
| | 🔇 `Volume Mute` / `M` | Silenciar / Restaurar Volumen |
| **Capa Gamer Fn (F5-F12)** | `F5` (o `Fn+F5`) | Detener Reproducción (Stop) |
| | `F6` (o `Fn+F6`) | Pista Anterior (Previous) |
| | `F7` (o `Fn+F7`) | Reproducir / Pausar (Play/Pause) |
| | `F8` (o `Fn+F8`) | Pista Siguiente (Next) |
| | `F9` (o `Fn+F9`) | Silenciar / Mute |
| | `F10` (o `Fn+F10`) | Bajar Volumen (-5%) |
| | `F11` (o `Fn+F11`) / `Ctrl+C` | Alternar Modos (**Compacto**, **Pequeño**, **Expandido**) |
| | `F12` (o `Fn+F12`) / `Ctrl+H` / `Esc` | Mostrar / Ocultar en Bandeja del Sistema |
| **Ráfagas & Seeking Gamer** | `Ctrl + Flecha Derecha` / `Shift + L` | Avance rápido (+5 segundos) |
| | `Ctrl + Flecha Izquierda` / `Shift + J` | Retroceso rápido (-5 segundos) |
| | `Shift + Flecha Arriba` | Subida rápida de volumen (+10%) |
| | `Shift + Flecha Abajo` | Bajada rápida de volumen (-10%) |
| | `Ctrl + Flecha Arriba` / `Ctrl + Flecha Abajo` | Volumen al Máximo (100%) / Silencio Total (0%) |
| | `Home` / `End` | Reiniciar pista desde 0:00 / Saltar al final |
| **Teclado Numérico (Numpad)** | `Numpad 5` / `Numpad 6` / `Numpad 4` | Play-Pause / Siguiente / Anterior |
| | `Numpad 8` / `Numpad 2` / `Numpad 0` | Subir Volumen / Bajar Volumen / Mute |
| | `Numpad *` / `Numpad /` | Avance (+5s) / Retroceso (-5s) |
| **Utilidades & Modos** | `S` / `Ctrl + Shift + S` | Alternar Modo Aleatorio (*Shuffle*) |
| | `R` / `Ctrl + Shift + R` | Alternar Bucle (*Repeat*) |
| | `Ctrl + F` | Marcar / Desmarcar Canción como Favorita |
| | `Ctrl + B` | Cambiar Fondo de Pantalla Inmediatamente |
| | `Ctrl + T` | Alternar Fijación Superior (*Always on Top*) |
| | `Ctrl + O` | Abrir Selector de Carpeta de Música |

---

## 📁 Estructura del Proyecto

```text
custom-music-player/
├── main.py                     # Punto de entrada principal (Inicialización Qt, MPRIS y Detección de SO)
├── audio_engine.py             # Motor de audio nativo (PyQt6 QMediaPlayer / FFmpeg / Slots MPRIS)
├── database_manager.py         # Persistencia SQLite con WAL, historial, playlists y traducciones
├── library_manager.py          # Escaneo asíncrono y metadatos de biblioteca musical
├── lyrics_manager.py           # Gestor y descargador de letras sincronizadas (.lrc) y planas
├── lyrics_translator.py        # Motor de traducción Online (GTX) y Offline (Argos Translate)
├── mpris_server.py             # Servidor DBus MPRIS2 (org.mpris.MediaPlayer2.CustomMusicPlayer)
├── mpris_client.py             # Cliente MPRIS para integración con Linux Desktop
├── win_media_client.py         # Integración con Windows System Media Transport Controls
├── config_manager.py           # Gestor de configuración persistente JSON (~/.config/custom-music-player/)
├── build.sh                    # Script de compilación para binario ejecutable en Linux
├── build_windows.bat           # Script de compilación para ejecutable en Windows
├── requirements.txt            # Dependencias de Python para Linux
├── requirements-windows.txt    # Dependencias de Python para Windows
├── CustomMusicPlayer.apk       # Instalador APK compilado para dispositivos Android
│
├── ui/                         # Interfaz Gráfica PyQt6 de Escritorio
│   ├── player_widget.py        # Widget principal flotante (Modo Pequeño y Compacto)
│   ├── expanded_view.py        # Vista expandida con biblioteca, tocadiscos animado y visor de letras
│   ├── lyrics_view_widget.py   # Visualizador interactivo de letras sincronizadas con traducción 🌐
│   ├── music_home_view.py      # Explorador de biblioteca, canciones, artistas, álbumes y playlists
│   ├── personalization_dialog.py # Diálogo unificado de temas, colores, fondos y formas
│   ├── small_playlist.py       # Lista de canciones ligera con delegado custom optimizado
│   ├── unified_mode_menu.py    # Menú contextual de selección de modos y controles rápidos
│   ├── styles.py               # Tokens de diseño, constantes de dimensiones y generador de estilos QSS
│   ├── color_extractor.py      # Extractor de colores dominantes y generador de degradados
│   ├── y2k_volume_slider.py    # Deslizador de volumen estilo Y2K con soporte para rueda de ratón
│   ├── marquee_label.py        # Etiqueta con desplazamiento horizontal animado para títulos largos
│   └── equalizer_widget.py     # Indicador de ecualización animado
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

1. **Instalación Directa:**
   * Instala el archivo `CustomMusicPlayer.apk` generado en la raíz del repositorio en tu teléfono Android.

2. **Compilación del APK desde código fuente:**
   ```bash
   cd mobile/android
   ./gradlew assembleRelease
   ```
   El APK compilado se genera en `mobile/android/app/build/outputs/apk/release/app-release.apk`.

3. **Entorno de Desarrollo Móvil:**
   ```bash
   cd mobile
   npx expo start
   ```

---

## 📄 Licencia

Este proyecto está distribuido bajo licencia abierta para uso personal y comunitario.
