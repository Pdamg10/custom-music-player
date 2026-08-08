# Custom Floating Music Player (PyQt6 + MPRIS2) — Red World Edition 🎧🖤

Un reproductor de música flotante, compacto y moderno para Linux (Wayland & X11) con estética **Negro Azabache & Rojo Carmesí**, fondo animado de audífonos con barras de ecualizador en tiempo real, sistema de carrusel de fondos con transiciones *cross-fade* y control multimedia completo mediante DBus/MPRIS2.

---

## 🚀 Características Principales

### 🎨 Experiencia Visual & Estética Red World
- **Fondo Animado & Barras EKG:** Capa de audífonos semi-transparente con **18 barras de ecualizador superpuestas** que oscilan al ritmo de la música en tiempo real.
- **Carrusel de Fondos con Transición Suave (Cross-Fade):** Galería rotativa de fondos (intervalo configurable, por defecto 15s) con transiciones progresivas a ~50 FPS.
- **Detección de Fondos en Tiempo Real:** Integración con `QFileSystemWatcher` para detectar automáticamente archivos `.jpg`, `.jpeg`, `.png` o `.webp` agregados, renombrados o eliminados en la carpeta de fondos.
- **Modos Adaptativos de Imagen (Aspect Mode):**
  - **Ajustar (`fit`):** Escala la imagen para verse 100% completa sin recortar ningún detalle.
  - **Llenar (`fill`):** Rellena la ventana recortando bordes sobrantes.
  - **Estirar (`stretch`):** Adapta la imagen exacto al tamaño y proporciones del reproductor.
- **Barra de Reproducción con Tirador de Corazón (`♥`):** La barra de tiempo (*Seekbar*) incorpora un tirador gráfico en forma de corazón neón.
- **Barra de Volumen con Tirador Circular (`⚪/🔴`):** Tirador circular perfecto anti-alias para ajustar el volumen.
- **Disposición de Controles Simétricos:** Controles completos con **Favorito (`♥`)**, **Pista Anterior (`⏮`)**, **Botón Central Circular de Play/Pausa (`▶` / `⏸`)**, **Pista Siguiente (`⏭`)** y **Repetición (`↻`)**.
- **Efecto Marquesina (*Marquee Scroll*):** Títulos y artistas largos se desplazan suavemente en texto continuo.
- **Modo Compacto & Normal:** Alterna dinámicamente entre la vista completa (280x360) y la barra mini (280x68) con el botón `⤢` o las teclas `Ctrl+C` / `F11`.

---

### 🎛️ Integración DBus / MPRIS2 & Detección Automática
- **Detección Instantánea de Reproductores:** Escaneo y captura en tiempo real de reproductores o navegadores compatibles con el estándar MPRIS2 en Linux (*Spotify, Strawberry, Rhythmbox, Amberol, Audacious, Firefox, Chrome, VLC*, etc.).
- **Reconexión Autónoma:** Sistema de *heartbeat* y monitoreo continuo de conexión DBus con reconexión automática en caso de caídas.
- **Barra de Progreso Interactiva & Tiempo Dual:** Muestra el tiempo transcurrido (`1:27`) y el tiempo restante (`-3:22`) permitiendo arrastrar para saltar de segundo (*Seek*).
- **Lista de Favoritos (`♥`):** Guarda tus canciones preferidas en `~/.config/custom-music-player/config.json`.
- **Control de Volumen con Rueda del Ratón:** Ajusta el volumen deslizando la rueda del ratón sobre la ventana flotante.

---

### ⌨️ Atajos de Teclado & Menú en Bandeja (System Tray)

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
├── main.py                    # Punto de entrada principal (QApplication & Ventana)
├── player.py                  # Wrapper ejecutable retrocompatible
├── mpris_client.py            # Adaptador DBus / MPRIS2 event-driven resiliente
├── config_manager.py          # Gestor de ajustes JSON (~/.config/custom-music-player/)
├── ui/
│   ├── __init__.py
│   ├── player_widget.py       # FloatingMusicPlayer, HeadphoneEKGWidget & BackgroundContainer
│   ├── marquee_label.py       # Control de scroll continuo de texto (Marquee)
│   ├── equalizer_widget.py    # Indicador de ecualizador animado de cabecera
│   ├── elided_label.py        # Etiqueta con truncado de texto elíptico (ElideRight)
│   ├── color_extractor.py     # Extractor de paletas de color en espacio HSV
│   └── styles.py              # Hoja de estilos QSS & Generador de tiradores PNG
├── requirements.txt           # Dependencias del proyecto (PyQt6)
└── README.md                  # Documentación actualizada del proyecto
```

---

## 🛠️ Instalación y Ejecución

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar el reproductor:**
   ```bash
   python3 main.py
   ```
