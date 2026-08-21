"""
ui/context_menus.py - Menús contextuales unificados para el Modo Expandido.

Provee funciones centralizadas para desplegar menús de canciones y playlists con
el estilo visual de referencia de 'En Reproducción' y sin duplicación de lógica.
"""

import os
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QWidget,
)

from config_manager import get_config_manager
from database_manager import get_database_manager


def get_context_menu_style(accent_color: str = "#ff1744") -> str:
    """Retorna el estilo visual estándar QSS para los menús contextuales."""
    clean_accent = accent_color.split(";")[0].strip() or "#ff1744"
    qc = QColor(clean_accent)
    if not qc.isValid():
        qc = QColor("#ff1744")
    r, g, b = qc.red(), qc.green(), qc.blue()

    return f"""
        QMenu {{
            background-color: rgba(20, 24, 38, 0.96);
            border: 1.5px solid rgba(255, 255, 255, 0.20);
            border-radius: 12px;
            padding: 6px;
            color: #ffffff;
        }}
        QMenu::item {{
            padding: 8px 18px;
            border-radius: 6px;
            font-size: 13px;
            color: #ffffff;
        }}
        QMenu::item:selected {{
            background-color: rgba({r}, {g}, {b}, 0.28);
            border: 1px solid {clean_accent};
            color: #ffffff;
        }}
        QMenu::separator {{
            height: 1px;
            background: rgba(255, 255, 255, 0.12);
            margin: 4px 8px;
        }}
    """


def show_track_context_menu(
    track_meta: Dict[str, Any],
    parent_widget: QWidget,
    global_pos: QPoint,
    audio_engine: Optional[Any] = None,
    current_playlist_id: Optional[int] = None,
    is_active_queue: bool = False,
    queue_index: Optional[int] = None,
    accent_color: str = "#ff1744",
    on_queue_changed: Optional[Callable[[], None]] = None,
    on_playlist_changed: Optional[Callable[[], None]] = None,
    on_track_play_requested: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    """Construye y ejecuta el menú contextual estándar para una canción.

    Opciones en orden estricto:
      1. ▶ Reproducir
      2. ⏭ Reproducir a continuación
      3. ── separador ──
      4. ♥ Agregar a Favoritos / 💔 Quitar de Favoritos
      5. ＋ Agregar a lista (Submenú con 'Nueva lista...' + playlists existentes)
      6. 🗑 Quitar de esta lista (si current_playlist_id) O 🗑 Quitar de la cola (si is_active_queue)
    """
    if not track_meta or not isinstance(track_meta, dict):
        return

    db = get_database_manager()
    cfg = get_config_manager()

    title = (track_meta.get("title") or "").strip()
    artist = (track_meta.get("artist") or "").strip()
    track_id = track_meta.get("track_id", "")
    file_path = track_meta.get("file_path") or track_meta.get("path") or ""

    menu = QMenu(parent_widget)
    menu.setStyleSheet(get_context_menu_style(accent_color))

    # 1. ▶ Reproducir
    act_play = menu.addAction("▶  Reproducir")

    # 2. ⏭ Reproducir a continuación
    act_play_next = menu.addAction("⏭  Reproducir a continuación")

    # 3. Separador
    menu.addSeparator()

    # 4. Favoritos (Consultar fuente canónica en config_manager)
    is_fav = cfg.is_favorite(title, artist)
    fav_label = "💔  Quitar de Favoritos" if is_fav else "♥  Agregar a Favoritos"
    act_fav = menu.addAction(fav_label)

    # 5. ＋ Agregar a lista (Submenú)
    sub_add_pl = menu.addMenu("＋  Agregar a lista")
    sub_add_pl.setStyleSheet(get_context_menu_style(accent_color))

    act_new_pl = sub_add_pl.addAction("＋  Nueva lista...")
    sub_add_pl.addSeparator()

    playlists = db.get_playlists_summary()
    pl_action_map = {}
    for pl in playlists:
        pl_act = sub_add_pl.addAction(f"📋  {pl['name']} ({pl.get('track_count', 0)})")
        pl_action_map[pl_act] = pl["id"]

    # 6. Opción de eliminación contextual (Mutuamente excluyentes)
    act_remove_from_pl = None
    act_remove_from_queue = None

    if current_playlist_id is not None:
        menu.addSeparator()
        act_remove_from_pl = menu.addAction("🗑  Quitar de esta lista")
    elif is_active_queue:
        menu.addSeparator()
        act_remove_from_queue = menu.addAction("🗑  Quitar de la cola")

    # Desplegar menú
    chosen_action = menu.exec(global_pos)
    if not chosen_action:
        return

    # ── Manejo de Acciones ──
    if chosen_action == act_play:
        if on_track_play_requested:
            on_track_play_requested(track_meta)
        elif audio_engine:
            if hasattr(audio_engine, "play_track"):
                audio_engine.play_track(track_meta)
            elif hasattr(audio_engine, "playlist"):
                # Buscar en la cola o agregarlo
                found_idx = -1
                for idx, t in enumerate(audio_engine.playlist):
                    if (track_id and t.get("track_id") == track_id) or (
                        file_path and (t.get("file_path") or t.get("path")) == file_path
                    ):
                        found_idx = idx
                        break
                if found_idx != -1:
                    audio_engine.play_index(found_idx)
                else:
                    audio_engine.playlist.append(track_meta)
                    if hasattr(audio_engine, "playlist_updated"):
                        audio_engine.playlist_updated.emit(audio_engine.playlist)
                    audio_engine.play_index(len(audio_engine.playlist) - 1)

    elif chosen_action == act_play_next:
        if audio_engine:
            if hasattr(audio_engine, "insert_next"):
                audio_engine.insert_next(track_meta)
            elif hasattr(audio_engine, "playlist"):
                cur_idx = getattr(audio_engine, "current_index", 0)
                ins_pos = (
                    cur_idx + 1
                    if (0 <= cur_idx < len(audio_engine.playlist))
                    else len(audio_engine.playlist)
                )
                audio_engine.playlist.insert(ins_pos, track_meta)
                if hasattr(audio_engine, "_rebuild_shuffle_indices"):
                    audio_engine._rebuild_shuffle_indices()
                if hasattr(audio_engine, "playlist_updated"):
                    audio_engine.playlist_updated.emit(audio_engine.playlist)
        if on_queue_changed:
            on_queue_changed()

    elif chosen_action == act_fav:
        meta_to_save = dict(track_meta)
        if "file_path" not in meta_to_save and file_path:
            meta_to_save["file_path"] = file_path
        cfg.toggle_favorite(meta_to_save)
        if on_playlist_changed:
            on_playlist_changed()

    elif chosen_action == act_new_pl:
        from ui.music_home_view import CreatePlaylistDialog

        top_parent = parent_widget.window() if parent_widget else None
        dlg = CreatePlaylistDialog(accent_color=accent_color, parent=top_parent)
        if dlg.exec() == QDialog.DialogCode.Accepted or getattr(dlg, "result", lambda: 0)() == 1:
            pl_name = dlg.get_playlist_name()
            if pl_name:
                new_pl_id = db.create_playlist(pl_name)
                if new_pl_id:
                    meta_to_add = dict(track_meta)
                    if "file_path" not in meta_to_add and file_path:
                        meta_to_add["file_path"] = file_path
                    db.add_track_to_playlist(new_pl_id, meta_to_add)
                    if on_playlist_changed:
                        on_playlist_changed()
                else:
                    QMessageBox.warning(
                        parent_widget,
                        "Nombre duplicado",
                        f"Ya existe una lista llamada '{pl_name}'. Elegí otro nombre.",
                    )

    elif chosen_action in pl_action_map:
        target_pl_id = pl_action_map[chosen_action]
        meta_to_add = dict(track_meta)
        if "file_path" not in meta_to_add and file_path:
            meta_to_add["file_path"] = file_path
        db.add_track_to_playlist(target_pl_id, meta_to_add)
        if on_playlist_changed:
            on_playlist_changed()

    elif chosen_action == act_remove_from_pl:
        if current_playlist_id is not None and track_id:
            db.remove_track_from_playlist(current_playlist_id, track_id)
            if on_playlist_changed:
                on_playlist_changed()

    elif chosen_action == act_remove_from_queue:
        if audio_engine and hasattr(audio_engine, "remove_track_at"):
            target_idx = queue_index
            if target_idx is None or not (0 <= target_idx < len(getattr(audio_engine, "playlist", []))):
                for idx, t in enumerate(getattr(audio_engine, "playlist", [])):
                    if (track_id and t.get("track_id") == track_id) or (
                        file_path and (t.get("file_path") or t.get("path")) == file_path
                    ):
                        target_idx = idx
                        break
            if target_idx is not None and 0 <= target_idx < len(getattr(audio_engine, "playlist", [])):
                audio_engine.remove_track_at(target_idx)
            if on_queue_changed:
                on_queue_changed()
        else:
            QMessageBox.warning(
                parent_widget,
                "Motor de audio no disponible",
                "No se pudo remover la pista: el motor de audio no está disponible o no soporta remoción de cola.",
            )


def show_playlist_context_menu(
    playlist_data: Dict[str, Any],
    parent_widget: QWidget,
    global_pos: QPoint,
    audio_engine: Optional[Any] = None,
    accent_color: str = "#ff1744",
    on_play_all_requested: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    on_playlist_changed: Optional[Callable[[], None]] = None,
) -> None:
    """Construye y ejecuta el menú contextual estándar para una tarjeta de Playlist.

    Opciones:
      1. ▶ Reproducir toda la lista
      2. 🖼 Cambiar portada
      3. ✏️ Renombrar
      4. 🗑 Eliminar lista (con QMessageBox de confirmación)
    """
    if not playlist_data or not isinstance(playlist_data, dict):
        return

    db = get_database_manager()
    playlist_id = playlist_data.get("id")
    if playlist_id is None:
        return

    pl_name = playlist_data.get("name", "Lista")

    menu = QMenu(parent_widget)
    menu.setStyleSheet(get_context_menu_style(accent_color))

    # 1. ▶ Reproducir toda la lista
    act_play_all = menu.addAction("▶  Reproducir toda la lista")

    # 2. 🖼 Cambiar portada
    act_change_cover = menu.addAction("🖼  Cambiar portada...")

    # 3. ✏️ Renombrar
    act_rename = menu.addAction("✏️  Renombrar...")

    menu.addSeparator()

    # 4. 🗑 Eliminar lista
    act_delete = menu.addAction("🗑  Eliminar lista")

    chosen = menu.exec(global_pos)
    if not chosen:
        return

    if chosen == act_play_all:
        tracks = db.get_playlist_tracks(playlist_id)
        if tracks:
            if on_play_all_requested:
                on_play_all_requested(tracks)
            elif audio_engine:
                audio_engine.playlist = list(tracks)
                if hasattr(audio_engine, "_rebuild_shuffle_indices"):
                    audio_engine._rebuild_shuffle_indices()
                if hasattr(audio_engine, "playlist_updated"):
                    audio_engine.playlist_updated.emit(audio_engine.playlist)
                if hasattr(audio_engine, "play_index"):
                    audio_engine.play_index(0)

    elif chosen == act_change_cover:
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            f"Cambiar Portada — {pl_name}",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if file_path and os.path.exists(file_path):
            db.set_playlist_cover(playlist_id, file_path)
            if on_playlist_changed:
                on_playlist_changed()

    elif chosen == act_rename:
        new_name, ok = QInputDialog.getText(
            parent_widget,
            "Renombrar Lista",
            "Nuevo nombre de la lista:",
            text=pl_name,
        )
        clean_new = (new_name or "").strip()
        if ok and clean_new and clean_new != pl_name:
            success = db.rename_playlist(playlist_id, clean_new)
            if success:
                if on_playlist_changed:
                    on_playlist_changed()
            else:
                QMessageBox.warning(
                    parent_widget,
                    "Nombre duplicado",
                    f"Ya existe una lista llamada '{clean_new}'. Elegí otro nombre.",
                )

    elif chosen == act_delete:
        reply = QMessageBox.question(
            parent_widget,
            "Eliminar Lista",
            f"¿Estás seguro de eliminar la lista '{pl_name}'?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_playlist(playlist_id)
            if on_playlist_changed:
                on_playlist_changed()
