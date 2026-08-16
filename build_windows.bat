@echo off
echo ========================================================
echo  Compilando CustomMusicPlayer para Windows...
echo ========================================================
python -m pip install -r requirements-windows.txt
pyinstaller --noconfirm CustomMusicPlayer.spec
echo ========================================================
echo  Compilacion finalizada exitosamente.
echo  Ejecutable unico listo en: dist\CustomMusicPlayer.exe
echo ========================================================
pause
