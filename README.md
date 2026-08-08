# Custom Floating Music Player (PyQt6 + MPRIS2) — Red World Edition 🎧🖤

Un reproductor de música flotante, compacto y moderno para Linux (Wayland & X11) con estética **Negro Azabache & Rojo Carmesí**, fondo animado de audífonos con barras de ecualizador en tiempo real y control multimedia completo mediante DBus/MPRIS2.

---

## 🚀 Características Principales

### 🎨 Experiencia Visual & Estética Red World
- **Fondo Personalizado & Barras EKG Animadas:** Fondo semi-transparente personalizado (`Cain , Break My Heart.jpeg`) con **18 barras de ecualizador superpuestas** que oscilan al ritmo de la música en tiempo real.
- **Barra de Reproducción con Tirador de Corazón (`♥`):** La barra de tiempo (*Seekbar*) incorpora un tirador gráfico en forma de corazón neón.
- **Barra de Volumen con Tirador Circular (`⚪/🔴`):** Tirador circular perfecto anti-alias para ajustar el volumen.
- **Disposición de 5 Controles Simétricos:** Fila centrada con **Favorito (`♥`)**, **Pista Anterior (`⏮`)**, **Botón Central Circular de Play/Pausa (`▶` / `⏸`)**, **Pista Siguiente (`⏭`)** y **Repetición (`↻`)**.
- **Efecto Marquesina (*Marquee Scroll*):** Títulos y artistas largos se desplazan suavemente en texto continuo.
- **Modo Compacto & Normal:** Alterna dinámicamente entre la vista completa (280x360) y la barra mini (280x68) con el botón `⤢` o la tecla `F11`.

---

### 🎛️ Integración DBus / MPRIS2 & Detección Automática
- **Detección Instantánea de Reproductores:** Detecta en tiempo real cualquier reproductor o navegador compatible con el estándar MPRIS2 en Linux (*Spotify, Strawberry, Rhythmbox, Amberol, Audacious, Firefox, Chrome, VLC*, etc.).
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
│   ├── player_widget.py       # Ventana flotante principal & HeadphoneEKGWidget
│   ├── marquee_label.py       # Control de scroll continuo de texto
│   ├── equalizer_widget.py    # Indicador de ecualizador de cabecera
│   ├── color_extractor.py     # Extractor de paletas de color
│   └── styles.py              # Hoja de estilos QSS & Generador de tiradores PNG
├── requirements.txt           # Dependencias del proyecto (PyQt6)
└── README.md                  # Documentación del proyecto
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
