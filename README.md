# Custom Music Player — Red World & STRAWBERRY Edition 🎧🖤

Un reproductor de música y widget flotante, moderno, compacto y **multiplataforma (Linux, Windows & Android Mobile)** con estética **Negro Azabache & Colores Neón Personalizables**, fondo animado de audífonos con barras de ecualizador EKG en tiempo real, recuadro de carátula personalizable, carrusel de fondos con transiciones *cross-fade*, motor de audio nativo y panel completo de personalización.

---

## 🚀 Características Principales

### 🌐 Soporte Multiplataforma Nativo
- **Linux (Wayland & X11):** Integración *event-driven* con el estándar **DBus / MPRIS2** (*Spotify, Strawberry, Rhythmbox, Amberol, Audacious, Firefox, Chrome, VLC*, etc.).
- **Windows (10 / 11):** Integración nativa con **System Media Transport Controls (SMTC / WinRT)** (*Spotify para Windows, Microsoft Edge, Chrome, Windows Media Player, iTunes*, etc.).
- **Android Mobile (`CustomMusicPlayer.apk`):** Aplicación autónoma ejecutable construida en **Expo / React Native (SDK 54)** con reproductor de audio nativo real (`expo-av`), réplica exacta del widget de PC, soporte *offline* completo y panel de ajustes neón.

---

### 🎨 Experiencia Visual & Personalización Completa

- **🎨 Paleta de Colores Neón Personalizable:** Elige entre múltiples temas neón (🔴 Rojo Neón / STRAWBERRY, 🔵 Cian Ciberpunk, 🟣 Violeta Lilas, 🟢 Verde Esmeralda, 🟡 Dorado Neón, 💗 Rosa Neón) o selecciona colores personalizados. Todos los bordes, botones, ecualizador y tiradores (`♥` y `⚪`) se adaptan al instante.
- **🖼️ Recuadro Central & Modos de Carátula:**
  - **Modo Automático:** Muestra la carátula oficial del álbum cuando hay una canción activa.
  - **Modo Fijo / Decorativo:** Mantiene fija tu imagen personalizada semi-transparente (ej. tocadiscos lila, anime neón).
- **🎧 Fondo Animado & Ecualizador EKG:** Barras verticales dinámicas superpuestas que oscilan al ritmo de la música.
- **♥ Barra de Reproducción & Volumen:** Tirador gráfico en forma de corazón (`❤️`) para la posición de la canción y tiempo restante con signo negativo (ej. `-1:45`).
- **🎛️ Disposición de Controles Simétricos:** Favorito (`♥`), Pista Anterior (`⏮`), Botón Central Circular Play/Pausa (`▶` / `⏸`), Pista Siguiente (`⏭`) y Repetición (`↻`).
- **📐 Modos de Tamaño & Comportamiento Adaptable:** 
  - **Comportamiento Estándar de Ventana:** Se ejecuta por defecto como una aplicación normal de escritorio (no forzada encima de otras ventanas), integrándose limpiamente con el gestor de ventanas del sistema. Se puede alternar la fijación superior (*Always on Top*) en cualquier momento con `Ctrl+T`.
  - **Modo Normal:** Tamaño predeterminado optimizado (350 × 410 px) con proporciones ideales para carátula, ecualizador EKG, título y controles de reproducción.
  - **Vistas Adaptables:** Alterna fácilmente entre **Modo Normal**, **Widget Flotante Compacto** y **Vista Expandida / Pantalla Completa** (`⤢` / `🗖`).

---

## ⌨️ Atajos de Teclado (Escritorio)

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
├── CustomMusicPlayer.apk      # 📱 Instalador ejecutable autónomo para Android (180 MB)
├── CustomMusicPlayer.spec     # Especificación PyInstaller para compilación ejecutable PC
├── main.py                    # Punto de entrada principal Escritorio (Detección de SO & Ventana)
├── player.py                  # Wrapper ejecutable de compatibilidad
├── mpris_client.py            # Adaptador Linux DBus / MPRIS2 event-driven
├── win_media_client.py        # Adaptador Windows SMTC / WinRT
├── config_manager.py          # Gestor de ajustes JSON (~/.config/custom-music-player/)
├── build.sh                   # Script de compilación ejecutable portátil Linux
├── ui/                        # Interfaz gráfica PyQt6 para Escritorio (Linux/Windows)
│   ├── player_widget.py       # FloatingMusicPlayer, HeadphoneEKGWidget & BackgroundContainer
│   ├── marquee_label.py       # Scroll continuo de texto en marquesina
│   ├── equalizer_widget.py    # Indicador animado de cabecera
│   ├── elided_label.py        # Etiqueta con truncado elíptico
│   ├── color_extractor.py     # Extractor de paletas de color HSV
│   └── styles.py              # Hoja de estilos QSS & Generador de tiradores PNG
├── mobile/                    # 📱 Aplicación Móvil Nativa (Expo SDK 54 / React Native)
│   ├── src/
│   │   ├── app/
│   │   │   ├── index.tsx      # Reproductor Móvil Completo, Motor Audio Real & Panel ⚙️ Personalizar
│   │   │   └── _layout.tsx    # Layout Raíz & Configuración de Status Bar
│   │   └── components/
│   │       └── EKGVisualizer.tsx # Canvas EKG Animado Nativo
│   ├── assets/images/         # Carátulas, Ícono Lilac Record Player & Fondos Neón
│   ├── android/               # Proyecto Android Gradle Autónomo (Export Embed Bundle)
│   └── package.json
├── requirements.txt           # Dependencias Python (PyQt6, dbus-python, etc.)
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

2. **Generar Ejecutable Portátil Binario:**
   ```bash
   ./build.sh
   ```
   El ejecutable portátil quedará listo en `dist/CustomMusicPlayer` para llevar a cualquier PC con Linux.

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
   El ejecutable quedará en `dist\CustomMusicPlayer.exe`.

---

### 📱 En Android (Teléfono)

1. **Instalación Directa vía APK:**
   - Transfiere e instala directamente el ejecutable [`CustomMusicPlayer.apk`](file:///home/phame/.local/bin/custom-music-player/CustomMusicPlayer.apk) en tu teléfono Android.
2. **Compilación / Desarrollo Local:**
   - Dentro de la carpeta `mobile/`:
     ```bash
     cd mobile
     npx expo start
     ```
   - Para recompilar el instalador APK ejecutable con cambios locales:
     ```bash
     cd mobile/android
     export JAVA_HOME=/home/phame/.local/jdk17
     export ANDROID_HOME=/home/phame/Android/Sdk
     ./gradlew assembleDebug
     ```
