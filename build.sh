#!/usr/bin/env bash
set -e
echo "🚀 Compilando ejecutable binario portable con PyInstaller..."
pyinstaller --noconfirm --onefile --windowed --name "CustomMusicPlayer" main.py
echo "✅ ¡Compilación completada! El ejecutable único se encuentra en: dist/CustomMusicPlayer"
