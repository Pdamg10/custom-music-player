"""Servidor de integración con System Media Transport Controls (SMTC) de Windows 10/11 para PyQt6."""

import asyncio
import os
import queue
import sys
import urllib.parse
from typing import Any, Dict, Optional

from PyQt6.QtCore import QMetaObject, QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot

HAS_WINSDK = False
try:
    if sys.platform == "win32":
        import winsdk.windows.media as wmedia
        import winsdk.windows.storage as wstorage
        import winsdk.windows.storage.streams as wstreams
        HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


def get_smtc_for_hwnd(hwnd: int) -> Optional[Any]:
    """Obtiene la instancia de SystemMediaTransportControls para un HWND Win32 vía ISystemMediaTransportControlsInterop."""
    if sys.platform != "win32" or not HAS_WINSDK:
        return None

    try:
        import ctypes
        from ctypes import (
            HRESULT,
            POINTER,
            Structure,
            WINFUNCTYPE,
            byref,
            c_uint8,
            c_uint16,
            c_uint32,
            c_void_p,
            cast,
            wintypes,
        )

        class GUID(Structure):
            _fields_ = [
                ("Data1", c_uint32),
                ("Data2", c_uint16),
                ("Data3", c_uint16),
                ("Data4", c_uint8 * 8),
            ]

            def __repr__(self) -> str:
                return f"{{{self.Data1:08X}-{self.Data2:04X}-{self.Data3:04X}-{bytes(self.Data4).hex()}}}"

        # IID_ISystemMediaTransportControlsInterop: {74871768-00BC-4024-8EEF-9C4DC2A0AE63}
        IID_ISystemMediaTransportControlsInterop = GUID(
            0x74871768,
            0x00BC,
            0x4024,
            (c_uint8 * 8)(0x8E, 0xEF, 0x9C, 0x4D, 0xC2, 0xA0, 0xAE, 0x63),
        )

        # IID_ISystemMediaTransportControls: {99FA124B-DD32-4766-95BA-2352949F4040}
        IID_ISystemMediaTransportControls = GUID(
            0x99FA124B,
            0xDD32,
            0x4766,
            (c_uint8 * 8)(0x95, 0xBA, 0x23, 0x52, 0x94, 0x9F, 0x40, 0x40),
        )

        try:
            combase = ctypes.windll.combase
        except Exception:
            combase = ctypes.windll.ole32

        RO_INIT_MULTITHREADED = 1
        if hasattr(combase, "RoInitialize"):
            combase.RoInitialize(RO_INIT_MULTITHREADED)
        else:
            ctypes.windll.ole32.CoInitialize(None)

        class HSTRING_HEADER(Structure):
            _fields_ = [("Reserved", c_void_p * 4)]

        hstring = c_void_p()
        hstring_header = HSTRING_HEADER()
        class_name = "Windows.Media.SystemMediaTransportControls"

        if hasattr(combase, "WindowsCreateStringReference"):
            hr = combase.WindowsCreateStringReference(
                ctypes.c_wchar_p(class_name),
                ctypes.c_uint32(len(class_name)),
                byref(hstring_header),
                byref(hstring),
            )
        else:
            hr = combase.WindowsCreateString(
                ctypes.c_wchar_p(class_name),
                ctypes.c_uint32(len(class_name)),
                byref(hstring),
            )

        if hr != 0 or not hstring:
            print(f"[WindowsMediaServer] Error creando HSTRING para SMTC (hr=0x{hr & 0xFFFFFFFF:08X})")
            return None

        factory_ptr = c_void_p()
        hr = combase.RoGetActivationFactory(
            hstring,
            byref(IID_ISystemMediaTransportControlsInterop),
            byref(factory_ptr),
        )

        if hasattr(combase, "WindowsDeleteString") and not hasattr(combase, "WindowsCreateStringReference"):
            combase.WindowsDeleteString(hstring)

        if hr != 0 or not factory_ptr.value:
            print(f"[WindowsMediaServer] Error en RoGetActivationFactory para SMTC Interop (hr=0x{hr & 0xFFFFFFFF:08X})")
            return None

        # VTable de ISystemMediaTransportControlsInterop (hereda de IInspectable -> IUnknown):
        # 0: QueryInterface, 1: AddRef, 2: Release
        # 3: GetIids, 4: GetRuntimeClassName, 5: GetTrustLevel
        # 6: GetForWindow(HWND, REFIID, void**)
        vtable = cast(factory_ptr, POINTER(POINTER(c_void_p))).contents

        RELEASE_PROTO = WINFUNCTYPE(c_uint32, c_void_p)
        release_factory = RELEASE_PROTO(vtable[2])

        GET_FOR_WINDOW_PROTO = WINFUNCTYPE(
            HRESULT,
            c_void_p,
            wintypes.HWND,
            POINTER(GUID),
            POINTER(c_void_p),
        )
        get_for_window = GET_FOR_WINDOW_PROTO(vtable[6])

        smtc_raw_ptr = c_void_p()
        hr_get = get_for_window(
            factory_ptr,
            wintypes.HWND(hwnd),
            byref(IID_ISystemMediaTransportControls),
            byref(smtc_raw_ptr),
        )

        release_factory(factory_ptr)

        if hr_get != 0 or not smtc_raw_ptr.value:
            print(f"[WindowsMediaServer] Error en ISystemMediaTransportControlsInterop::GetForWindow (hr=0x{hr_get & 0xFFFFFFFF:08X})")
            return None

        import winsdk.windows.media as wmedia
        if hasattr(wmedia.SystemMediaTransportControls, "_from"):
            smtc = wmedia.SystemMediaTransportControls._from(smtc_raw_ptr.value)
        else:
            smtc = wmedia.SystemMediaTransportControls._from(smtc_raw_ptr)

        return smtc

    except Exception as e:
        print(f"[WindowsMediaServer] Excepción al obtener SMTC vía Interop: {e}")
        return None


class SMTCArtworkWorker(QThread):
    """Hilo de trabajo secundario para la carga asíncrona de carátulas sin congelar la UI de PyQt6."""

    artwork_ready = pyqtSignal(str, object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._queue: queue.Queue = queue.Queue()
        self._running: bool = True

    def request_artwork(self, track_id: str, file_path: str) -> None:
        self._queue.put((track_id, file_path))

    def stop(self) -> None:
        self._running = False
        self._queue.put((None, None))
        self.wait(1000)

    def run(self) -> None:
        if sys.platform != "win32":
            return

        try:
            import ctypes
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                track_id, file_path = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue

            if not self._running or track_id is None:
                break

            # Descartar solicitudes intermedias si el usuario cambia rápidamente de canción
            while not self._queue.empty():
                try:
                    next_item = self._queue.get_nowait()
                    if next_item[0] is not None:
                        track_id, file_path = next_item
                    else:
                        self._running = False
                        break
                except queue.Empty:
                    break

            if not self._running or not file_path or not os.path.exists(file_path):
                continue

            try:
                import winsdk.windows.storage as wstorage
                import winsdk.windows.storage.streams as wstreams

                async def _load():
                    norm_path = os.path.abspath(file_path)
                    storage_file = await wstorage.StorageFile.get_file_from_path_async(norm_path)
                    return wstreams.RandomAccessStreamReference.create_from_file(storage_file)

                stream_ref = loop.run_until_complete(_load())
                if stream_ref and self._running:
                    self.artwork_ready.emit(track_id, stream_ref)
            except Exception as e:
                print(f"[WindowsMediaServer] Advertencia cargando carátula en background: {e}")

        try:
            loop.close()
            ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass


class WindowsMediaServer(QObject):
    """Servidor de integración con System Media Transport Controls (SMTC) de Windows."""

    metadata_changed = pyqtSignal(dict)
    playback_status_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)
    volume_changed = pyqtSignal(float)
    loop_status_changed = pyqtSignal(str)
    shuffle_status_changed = pyqtSignal(bool)

    def __init__(self, audio_engine: Any, window: Optional[QObject] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.engine = audio_engine
        self.window = window
        self.smtc = None
        self.display_updater = None
        self._current_track_id: Optional[str] = None
        self._is_initialized = False
        self._pending_metadata: Optional[Dict[str, Any]] = None
        self._pending_status: Optional[str] = None

        self._art_worker = SMTCArtworkWorker(self)
        self._art_worker.artwork_ready.connect(self._on_artwork_loaded)
        if sys.platform == "win32" and HAS_WINSDK:
            self._art_worker.start()

        self.engine.playback_status_changed.connect(self._on_status_changed)
        self.engine.metadata_changed.connect(self._on_metadata_changed)
        self.engine.volume_changed.connect(self._on_volume_changed)
        if hasattr(self.engine, "position_changed"):
            self.engine.position_changed.connect(self._on_position_changed)

        if sys.platform == "win32":
            QTimer.singleShot(50, self._deferred_init)

    def _get_hwnd(self) -> Optional[int]:
        if self.window is None:
            return None
        try:
            wid = self.window.winId()
            return int(wid)
        except Exception as e:
            print(f"[WindowsMediaServer] Error obteniendo HWND de la ventana: {e}")
            return None

    def _deferred_init(self) -> None:
        if self._is_initialized or self.smtc is not None:
            return
        self._init_smtc()
        if self._pending_metadata:
            self._on_metadata_changed(self._pending_metadata)
            self._pending_metadata = None
        if self._pending_status:
            self._on_status_changed(self._pending_status)
            self._pending_status = None

    def _init_smtc(self) -> None:
        if sys.platform != "win32":
            return
        if not HAS_WINSDK:
            print("[WindowsMediaServer] winsdk no disponible en el entorno. SMTC deshabilitado.")
            return

        hwnd = self._get_hwnd()
        if not hwnd:
            print("[WindowsMediaServer] HWND no disponible para inicializar SMTC.")
            return

        print(f"[WindowsMediaServer] Inicializando SMTC para HWND: 0x{hwnd:X}")
        try:
            self.smtc = get_smtc_for_hwnd(hwnd)
            if self.smtc:
                self.smtc.is_play_enabled = True
                self.smtc.is_pause_enabled = True
                self.smtc.is_next_enabled = True
                self.smtc.is_previous_enabled = True
                self.smtc.is_stop_enabled = True
                self.smtc.is_enabled = True
                self.smtc.add_button_pressed(self._on_button_pressed)
                self.display_updater = self.smtc.display_updater
                self._is_initialized = True
                print("[WindowsMediaServer] SMTC inicializado exitosamente mediante ISystemMediaTransportControlsInterop.")
            else:
                print("[WindowsMediaServer] Advertencia: No se pudo obtener SMTC vía ISystemMediaTransportControlsInterop.")
        except Exception as e:
            print(f"[WindowsMediaServer] Advertencia: Error inicializando SMTC en Windows: {e}")

    def _on_button_pressed(self, sender: Any, args: Any) -> None:
        try:
            import winsdk.windows.media as wmedia
            btn = args.button
            btn_enum = wmedia.SystemMediaTransportControlsButton

            if btn == btn_enum.PLAY:
                QMetaObject.invokeMethod(self.engine, "play", Qt.ConnectionType.QueuedConnection)
            elif btn == btn_enum.PAUSE:
                QMetaObject.invokeMethod(self.engine, "pause", Qt.ConnectionType.QueuedConnection)
            elif btn == btn_enum.PLAY_PAUSE:
                QMetaObject.invokeMethod(self.engine, "play_pause", Qt.ConnectionType.QueuedConnection)
            elif btn == btn_enum.NEXT:
                QMetaObject.invokeMethod(self.engine, "next", Qt.ConnectionType.QueuedConnection)
            elif btn == btn_enum.PREVIOUS:
                QMetaObject.invokeMethod(self.engine, "previous", Qt.ConnectionType.QueuedConnection)
            elif btn == btn_enum.STOP:
                QMetaObject.invokeMethod(self.engine, "stop", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            print(f"[WindowsMediaServer] Error procesando botón en SMTC: {e}")

    def _on_status_changed(self, status: str) -> None:
        if not self.smtc:
            self._pending_status = status
            return

        try:
            import winsdk.windows.media as wmedia
            status_map = {
                "Playing": wmedia.MediaPlaybackStatus.PLAYING,
                "Paused": wmedia.MediaPlaybackStatus.PAUSED,
                "Stopped": wmedia.MediaPlaybackStatus.STOPPED,
            }
            mapped = status_map.get(status, wmedia.MediaPlaybackStatus.STOPPED)
            self.smtc.playback_status = mapped
            self.playback_status_changed.emit(status)
        except Exception as e:
            print(f"[WindowsMediaServer] Error actualizando playback_status en SMTC: {e}")

    @pyqtSlot(str, object)
    def _on_artwork_loaded(self, track_id: str, stream_ref: Any) -> None:
        if not self.smtc or not self.display_updater:
            return
        if track_id != self._current_track_id:
            return

        try:
            self.display_updater.thumbnail = stream_ref
            self.display_updater.update()
        except Exception as e:
            print(f"[WindowsMediaServer] Advertencia: Error asignando thumbnail en SMTC: {e}")

    def _on_metadata_changed(self, meta: dict) -> None:
        if not self.smtc or not self.display_updater:
            self._pending_metadata = meta
            return

        try:
            import winsdk.windows.media as wmedia

            title = meta.get("title") or "Sin título"
            artist = meta.get("artist") or "Artista desconocido"
            album = meta.get("album") or "Álbum desconocido"
            track_id = str(meta.get("track_id") or meta.get("file_path") or f"{title}_{artist}")

            self._current_track_id = track_id

            self.display_updater.type = wmedia.MediaPlaybackType.MUSIC
            props = self.display_updater.music_properties
            props.title = str(title)
            props.artist = str(artist)
            props.album_title = str(album)

            # Limpiar thumbnail previo mientras se carga el nuevo
            self.display_updater.thumbnail = None
            self.display_updater.update()

            art_url = meta.get("art_url", "")
            local_path = ""
            if art_url:
                if art_url.startswith("file://"):
                    parsed = urllib.parse.urlparse(art_url).path
                    if sys.platform == "win32" and parsed.startswith("/"):
                        parsed = parsed.lstrip("/")
                    local_path = urllib.parse.unquote(parsed)
                else:
                    local_path = art_url

            if local_path and os.path.exists(local_path):
                if self._art_worker and self._art_worker.isRunning():
                    self._art_worker.request_artwork(track_id, local_path)

            self.metadata_changed.emit(meta)
        except Exception as e:
            print(f"[WindowsMediaServer] Error actualizando metadatos en SMTC: {e}")

    def _on_position_changed(self, pos_sec: int, dur_sec: int) -> None:
        if not self.smtc:
            return
        try:
            import winsdk.windows.media as wmedia
            import winsdk.windows.foundation as wfoundation

            if hasattr(wmedia, "SystemMediaTransportControlsTimelineProperties"):
                timeline = wmedia.SystemMediaTransportControlsTimelineProperties()
                timeline.start_time = wfoundation.TimeSpan(0)
                timeline.end_time = wfoundation.TimeSpan(int(max(0, dur_sec) * 10_000_000))
                timeline.position = wfoundation.TimeSpan(int(max(0, pos_sec) * 10_000_000))
                timeline.min_seek_time = wfoundation.TimeSpan(0)
                timeline.max_seek_time = wfoundation.TimeSpan(int(max(0, dur_sec) * 10_000_000))
                self.smtc.update_timeline_properties(timeline)
            self.position_changed.emit(pos_sec, dur_sec)
        except Exception:
            pass

    def _on_volume_changed(self, volume: float) -> None:
        """SMTC de Windows no expone control de volumen bidireccional directo."""
        self.volume_changed.emit(volume)

    def shutdown(self) -> None:
        """Cierre ordenado de recursos de SMTC."""
        if self._art_worker:
            try:
                self._art_worker.stop()
            except Exception:
                pass

        if self.smtc:
            try:
                import winsdk.windows.media as wmedia
                self.smtc.playback_status = wmedia.MediaPlaybackStatus.CLOSED
                self.smtc.is_enabled = False
            except Exception:
                pass
            self.smtc = None
            self.display_updater = None
        print("[WindowsMediaServer] SMTC detenido correctamente.")


WindowsMediaClient = WindowsMediaServer
