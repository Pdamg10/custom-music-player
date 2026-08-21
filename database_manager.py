import hashlib
import logging
import os
import queue
import re
import sqlite3
import threading
import time
import unicodedata
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from config_manager import CONFIG_DIR
from library_manager import LOADING_METADATA, UNKNOWN_ALBUM, UNKNOWN_ARTIST

DB_PATH = os.path.join(CONFIG_DIR, "userdata.db")
LOG_FILE_PATH = os.path.join(CONFIG_DIR, "database.log")
CURRENT_SCHEMA_VERSION = 3

# Configuración del logger de base de datos con rotación (512 KB, 1 backup)
_logger = logging.getLogger("custom_music_player.database")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        _handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=512 * 1024,
            backupCount=1,
            encoding="utf-8",
        )
        _formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        _handler.setFormatter(_formatter)
        _logger.addHandler(_handler)
    except Exception as _e:
        print(f"[DatabaseManager] Error inicializando logging: {_e}")

UNKNOWN_TITLES = {
    "sin reproducción",
    "sin reproduccion",
    "sin título",
    "sin titulo",
    "no playback",
    "test title",
    "desconocido",
    "cargando metadatos...",
}


def normalize_meta_string(text: Any) -> str:
    """Normaliza un texto eliminando espacios redundantes y unificando Unicode en NFC."""
    if text is None:
        return ""
    # Convertir a string y unificar codificación Unicode (NFC para acentos en español)
    normalized = unicodedata.normalize("NFC", str(text).strip())
    # Colapsar espacios múltiples internos a uno solo
    collapsed = re.sub(r"\s+", " ", normalized)
    return collapsed.lower()


def compute_canonical_track_id(
    artist: str, album: str, title: str, fallback_path: str = ""
) -> str:
    """Genera un identificador persistente e invariable para una canción.

    Si tiene artista y título válidos, usa SHA256(artista|álbum|título normalizado).
    Si los metadatos son genéricos o desconocidos, usa MD5 de la ruta absoluta.
    """
    norm_artist = normalize_meta_string(artist)
    norm_album = normalize_meta_string(album)
    norm_title = normalize_meta_string(title)

    unknown_artist_norm = normalize_meta_string(UNKNOWN_ARTIST)
    loading_norm = normalize_meta_string(LOADING_METADATA)
    unknown_album_norm = normalize_meta_string(UNKNOWN_ALBUM)

    is_artist_valid = bool(
        norm_artist and norm_artist not in (unknown_artist_norm, loading_norm)
    )
    is_title_valid = bool(
        norm_title and norm_title not in UNKNOWN_TITLES and norm_title != loading_norm
    )

    if is_artist_valid and is_title_valid:
        album_part = norm_album if norm_album != unknown_album_norm else ""
        composite = f"{norm_artist}|{album_part}|{norm_title}"
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()

    if fallback_path:
        norm_path = os.path.abspath(fallback_path)
        return hashlib.md5(norm_path.encode("utf-8")).hexdigest()

    return ""


class DatabaseManager:
    """Gestor de persistencia SQLite para historial, estadísticas y playlists."""

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: Optional[str] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._thread_local = threading.local()
        self._init_db()

        # Worker persistente en segundo plano con cola FIFO para escrituras asíncronas
        self._write_queue: queue.Queue = queue.Queue()
        self._write_worker = threading.Thread(
            target=self._write_worker_loop,
            daemon=True,
            name="DatabaseWriteWorker",
        )
        self._write_worker.start()

        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna una conexión SQLite por hilo con Foreign Keys y WAL habilitados."""
        conn = getattr(self._thread_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            # Bloqueante 3: PRAGMA foreign_keys = ON en cada nueva conexión
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            self._thread_local.conn = conn
        return conn

    def _write_worker_loop(self) -> None:
        """Hilo de fondo persistente que procesa escrituras en cola secuencialmente."""
        self._get_connection()
        while True:
            try:
                task = self._write_queue.get()
                if task is None:
                    break
                func, args, kwargs = task
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    _logger.exception("Error ejecutando escritura en worker: %s", e)
                finally:
                    self._write_queue.task_done()
            except Exception as e:
                _logger.exception("Excepción en worker loop: %s", e)

    def enqueue_write(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Encola una operación de escritura para ejecución asíncrona sin bloquear el hilo emisor."""
        self._write_queue.put((func, args, kwargs))

    def shutdown(self, timeout: float = 3.0) -> None:
        """Cierre ordenado del worker de escritura asegurando que no se pierdan datos pendientes."""
        if not getattr(self, "_write_worker", None) or not self._write_worker.is_alive():
            return
        try:
            # Enviar centinela de parada al worker persistente
            self._write_queue.put(None)
            self._write_worker.join(timeout=timeout)
        except Exception as e:
            _logger.error("Error durante shutdown: %s", e)
        finally:
            conn = getattr(self._thread_local, "conn", None)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                self._thread_local.conn = None

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self) -> None:
        """Inicializa y versiona el esquema de la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA user_version;")
        version_row = cursor.fetchone()
        current_version = version_row[0] if version_row else 0

        if current_version < 1:
            with self._transaction() as cur:
                # 1. Tabla de canciones (Catálogo maestro)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tracks (
                        track_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL UNIQUE,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT NOT NULL,
                        length_sec INTEGER DEFAULT 0,
                        art_url TEXT DEFAULT '',
                        play_count INTEGER DEFAULT 0,
                        last_played_at INTEGER DEFAULT 0
                    );
                """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks(file_path);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tracks_play_count ON tracks(play_count DESC);"
                )

                # 2. Historial de reproducciones ("Recién escuchados")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS play_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        track_id TEXT NOT NULL,
                        played_at INTEGER NOT NULL,
                        FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON UPDATE CASCADE ON DELETE CASCADE
                    );
                """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_play_history_track_id ON play_history(track_id);"
                )

                # 3. Playlists de usuario
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        cover_path TEXT DEFAULT '',
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                """
                )

                # 4. Canciones dentro de cada playlist
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlist_tracks (
                        playlist_id INTEGER NOT NULL,
                        track_id TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        added_at INTEGER NOT NULL,
                        PRIMARY KEY (playlist_id, track_id),
                        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                        FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON UPDATE CASCADE ON DELETE CASCADE
                    );
                """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_playlist_tracks_pos ON playlist_tracks(playlist_id, position);"
                )

                # Actualizar versionado de esquema inicial
                cur.execute("PRAGMA user_version = 1;")

        if current_version < 2:
            with self._transaction() as cur:
                # 5. Traducciones de letras cacheadas con llave foránea a tracks
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS lyrics_translations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        track_id TEXT NOT NULL,
                        target_lang TEXT NOT NULL,
                        source_lang TEXT DEFAULT 'auto',
                        engine_used TEXT NOT NULL,
                        translated_lrc TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON UPDATE CASCADE ON DELETE CASCADE,
                        UNIQUE(track_id, target_lang)
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lyrics_trans_track_lang ON lyrics_translations(track_id, target_lang);"
                )
                cur.execute("PRAGMA user_version = 2;")

        if current_version < 3:
            with self._transaction() as cur:
                # 6. Portada personalizable de playlists (Migración segura sin recrear tabla)
                cur.execute("PRAGMA table_info(playlists);")
                columns = [row["name"] for row in cur.fetchall()]
                if "cover_path" not in columns:
                    cur.execute(
                        "ALTER TABLE playlists ADD COLUMN cover_path TEXT DEFAULT '';"
                    )
                cur.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION};")

    # ══════════════════════════════════════════════════════════════════════════
    # UPSERT & MIGRACIÓN DE TRACK_ID (BLOQUEANTE 2)
    # ══════════════════════════════════════════════════════════════════════════

    def upsert_or_migrate_track(self, track_meta: Dict[str, Any]) -> str:
        """Inserta o actualiza una canción. Si el archivo ya existía con un track_id basado

        en ruta y ahora tiene metadatos válidos, migra el track_id en tracks, play_history
        y playlist_tracks sin perder historial ni contadores.
        """
        file_path = track_meta.get("file_path", "")
        if not file_path:
            return ""

        title = track_meta.get("title") or os.path.splitext(os.path.basename(file_path))[0]
        artist = track_meta.get("artist") or UNKNOWN_ARTIST
        album = track_meta.get("album") or UNKNOWN_ALBUM
        length_sec = int(track_meta.get("length_sec") or 0)
        art_url = track_meta.get("art_url") or ""

        new_track_id = compute_canonical_track_id(artist, album, title, file_path)

        with self._transaction() as cur:
            # Comprobar si ya existe la ruta en la base de datos
            cur.execute("SELECT track_id, play_count, last_played_at FROM tracks WHERE file_path = ?;", (file_path,))
            existing_by_path = cur.fetchone()

            if existing_by_path:
                old_track_id = existing_by_path["track_id"]
                old_play_count = existing_by_path["play_count"]
                old_last_played = existing_by_path["last_played_at"]

                if old_track_id == new_track_id:
                    # El track_id coincide, solo refrescar metadatos
                    cur.execute(
                        """
                        UPDATE tracks
                        SET title = ?, artist = ?, album = ?, length_sec = ?, art_url = ?
                        WHERE track_id = ?;
                        """,
                        (title, artist, album, length_sec, art_url, new_track_id),
                    )
                    return new_track_id

                # El track_id cambió (ej. de fallback de ruta a hash canónico por metadatos)
                cur.execute("SELECT track_id, play_count, last_played_at FROM tracks WHERE track_id = ?;", (new_track_id,))
                existing_canonical = cur.fetchone()

                if existing_canonical:
                    # CASO DE FUSIÓN (track_id nuevo ya existía por otro archivo o scan previo):
                    merged_plays = old_play_count + existing_canonical["play_count"]
                    merged_last_played = max(old_last_played, existing_canonical["last_played_at"])

                    # 1. Re-apuntar historial a new_track_id
                    cur.execute("UPDATE play_history SET track_id = ? WHERE track_id = ?;", (new_track_id, old_track_id))

                    # 2. Re-apuntar playlist_tracks con UPDATE OR IGNORE para evitar colisión de PRIMARY KEY (playlist_id, track_id)
                    # Si la playlist ya contenía new_track_id, UPDATE OR IGNORE omite la fila duplicada sin fallar
                    cur.execute("UPDATE OR IGNORE playlist_tracks SET track_id = ? WHERE track_id = ?;", (new_track_id, old_track_id))

                    # 3. Eliminar cualquier fila de old_track_id que quedó sin actualizar por conflicto de duplicado
                    cur.execute("DELETE FROM playlist_tracks WHERE track_id = ?;", (old_track_id,))

                    # 4. Re-indexar posiciones contiguas en las playlists afectadas
                    cur.execute("SELECT DISTINCT playlist_id FROM playlist_tracks WHERE track_id = ?;", (new_track_id,))
                    affected_pls = [r["playlist_id"] for r in cur.fetchall()]
                    for pl_id in affected_pls:
                        cur.execute(
                            "SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position ASC, added_at ASC;",
                            (pl_id,),
                        )
                        rows = cur.fetchall()
                        for idx, r in enumerate(rows):
                            cur.execute(
                                "UPDATE playlist_tracks SET position = ? WHERE playlist_id = ? AND track_id = ?;",
                                (idx, pl_id, r["track_id"]),
                            )

                    # 5. Eliminar el registro antiguo de tracks y actualizar el registro canónico consolidado
                    cur.execute("DELETE FROM tracks WHERE track_id = ?;", (old_track_id,))
                    cur.execute(
                        """
                        UPDATE tracks
                        SET file_path = ?, title = ?, artist = ?, album = ?, length_sec = ?,
                            art_url = ?, play_count = ?, last_played_at = ?
                        WHERE track_id = ?;
                        """,
                        (file_path, title, artist, album, length_sec, art_url, merged_plays, merged_last_played, new_track_id),
                    )
                else:
                    # No existía new_track_id: actualizar la PK directamente.
                    # Gracias a ON UPDATE CASCADE en play_history y playlist_tracks,
                    # SQLite actualiza automáticamente las tablas hijas en cascada.
                    cur.execute(
                        """
                        UPDATE tracks
                        SET track_id = ?, title = ?, artist = ?, album = ?, length_sec = ?, art_url = ?
                        WHERE file_path = ?;
                        """,
                        (new_track_id, title, artist, album, length_sec, art_url, file_path),
                    )
                return new_track_id

            # No existía por ruta. Comprobar si ya existe por track_id canónico
            cur.execute("SELECT track_id FROM tracks WHERE track_id = ?;", (new_track_id,))
            existing_by_id = cur.fetchone()

            if existing_by_id:
                # Actualizar ruta y metadatos
                cur.execute(
                    """
                    UPDATE tracks
                    SET file_path = ?, title = ?, artist = ?, album = ?, length_sec = ?, art_url = ?
                    WHERE track_id = ?;
                    """,
                    (file_path, title, artist, album, length_sec, art_url, new_track_id),
                )
            else:
                # Registro completamente nuevo
                cur.execute(
                    """
                    INSERT INTO tracks (track_id, file_path, title, artist, album, length_sec, art_url, play_count, last_played_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0);
                    """,
                    (new_track_id, file_path, title, artist, album, length_sec, art_url),
                )

            return new_track_id

    # ══════════════════════════════════════════════════════════════════════════
    # HISTORIAL & CONTADORES (RECIÉN ESCUCHADOS / MÁS ESCUCHADOS)
    # ══════════════════════════════════════════════════════════════════════════

    def record_playback(
        self, track_meta: Dict[str, Any], timestamp: Optional[int] = None
    ) -> str:
        """Registra síncronamente una reproducción validada (>10s) en el historial y contadores."""
        if not track_meta or not track_meta.get("file_path"):
            return ""

        now = int(timestamp or time.time())
        track_id = self.upsert_or_migrate_track(track_meta)
        if not track_id:
            return ""

        with self._transaction() as cur:
            # Incrementar contador y última reproducción en tabla tracks
            cur.execute(
                """
                UPDATE tracks
                SET play_count = play_count + 1,
                    last_played_at = ?
                WHERE track_id = ?;
                """,
                (now, track_id),
            )
            # Insertar registro en el historial temporal
            cur.execute(
                """
                INSERT INTO play_history (track_id, played_at)
                VALUES (?, ?);
                """,
                (track_id, now),
            )

        return track_id

    def record_playback_async(
        self, track_meta: Dict[str, Any], timestamp: Optional[int] = None
    ) -> None:
        """Despacha el registro de reproducción hacia el worker persistente en segundo plano."""
        self.enqueue_write(self.record_playback, track_meta, timestamp)

    def get_recently_played(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retorna las últimas pistas reproducidas únicas, ordenadas por reproducción más reciente."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT t.track_id, t.file_path, t.title, t.artist, t.album,
                   t.length_sec, t.art_url, t.play_count, MAX(h.played_at) AS last_played
            FROM play_history h
            JOIN tracks t ON h.track_id = t.track_id
            GROUP BY t.track_id
            ORDER BY last_played DESC
            LIMIT ?;
            """,
            (max(1, limit),),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_top_artists(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retorna los artistas más reproducidos sumando los contadores de sus canciones."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT artist,
                   SUM(play_count) AS total_plays,
                   COUNT(track_id) AS track_count,
                   MAX(art_url) AS art_url
            FROM tracks
            WHERE artist != ? AND artist != ? AND artist != '' AND play_count > 0
            GROUP BY artist
            ORDER BY total_plays DESC, track_count DESC
            LIMIT ?;
            """,
            (UNKNOWN_ARTIST, LOADING_METADATA, max(1, limit)),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_top_albums(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retorna los álbumes más reproducidos sumando los contadores de sus canciones."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT album,
                   artist,
                   SUM(play_count) AS total_plays,
                   COUNT(track_id) AS track_count,
                   MAX(art_url) AS art_url
            FROM tracks
            WHERE album != ? AND album != '' AND play_count > 0
            GROUP BY album, artist
            ORDER BY total_plays DESC, track_count DESC
            LIMIT ?;
            """,
            (UNKNOWN_ALBUM, max(1, limit)),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_top_tracks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retorna las canciones individuales más escuchadas."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT track_id, file_path, title, artist, album, length_sec, art_url, play_count, last_played_at
            FROM tracks
            WHERE play_count > 0
            ORDER BY play_count DESC, last_played_at DESC
            LIMIT ?;
            """,
            (max(1, limit),),
        )
        return [dict(row) for row in cur.fetchall()]

    # ══════════════════════════════════════════════════════════════════════════
    # PLAYLISTS PERSONALIZADAS (CRUD & CONTEOS INSTANTÁNEOS)
    # ══════════════════════════════════════════════════════════════════════════

    def create_playlist(self, name: str) -> Optional[int]:
        """Crea una nueva playlist y retorna su ID."""
        clean_name = (name or "").strip()
        if not clean_name:
            return None

        now = int(time.time())
        try:
            with self._transaction() as cur:
                cur.execute(
                    """
                    INSERT INTO playlists (name, created_at, updated_at)
                    VALUES (?, ?, ?);
                    """,
                    (clean_name, now, now),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def rename_playlist(self, playlist_id: int, new_name: str) -> bool:
        """Renombra una playlist existente."""
        clean_name = (new_name or "").strip()
        if not clean_name:
            return False

        now = int(time.time())
        try:
            with self._transaction() as cur:
                cur.execute(
                    """
                    UPDATE playlists
                    SET name = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (clean_name, now, playlist_id),
                )
                return cur.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def delete_playlist(self, playlist_id: int) -> bool:
        """Elimina una playlist y sus relaciones en cascada."""
        with self._transaction() as cur:
            cur.execute("DELETE FROM playlists WHERE id = ?;", (playlist_id,))
            return cur.rowcount > 0

    def get_playlist(self, playlist_id: int) -> Optional[Dict[str, Any]]:
        """Retorna la información completa de una playlist incluyendo su portada personalizada."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id, p.name, p.cover_path, p.created_at, p.updated_at,
                   COUNT(pt.track_id) AS track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            WHERE p.id = ?
            GROUP BY p.id;
            """,
            (playlist_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def set_playlist_cover(self, playlist_id: int, cover_path: str) -> bool:
        """Actualiza la ruta de la portada personalizada de una playlist."""
        now = int(time.time())
        with self._transaction() as cur:
            cur.execute(
                "UPDATE playlists SET cover_path = ?, updated_at = ? WHERE id = ?;",
                (cover_path, now, playlist_id),
            )
            return cur.rowcount > 0

    def get_playlists_summary(self) -> List[Dict[str, Any]]:
        """Retorna el listado de playlists con el recuento instantáneo de canciones

        sin cargar los objetos de canciones completos en memoria (Costo O(1)).
        """
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id, p.name, p.cover_path, p.created_at, p.updated_at,
                   COUNT(pt.track_id) AS track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            GROUP BY p.id
            ORDER BY p.updated_at DESC, p.created_at DESC;
            """
        )
        return [dict(row) for row in cur.fetchall()]

    def add_track_to_playlist(
        self, playlist_id: int, track_meta: Dict[str, Any]
    ) -> bool:
        """Agrega una pista a una playlist, asegurando persistencia de metadatos."""
        track_id = self.upsert_or_migrate_track(track_meta)
        if not track_id:
            return False

        now = int(time.time())
        try:
            with self._transaction() as cur:
                # Determinar la siguiente posición disponible
                cur.execute(
                    "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM playlist_tracks WHERE playlist_id = ?;",
                    (playlist_id,),
                )
                next_pos = cur.fetchone()["next_pos"]

                cur.execute(
                    """
                    INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position, added_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (playlist_id, track_id, next_pos, now),
                )
                inserted = cur.rowcount > 0
                if inserted:
                    cur.execute(
                        "UPDATE playlists SET updated_at = ? WHERE id = ?;",
                        (now, playlist_id),
                    )
                return inserted
        except Exception:
            return False

    def remove_track_from_playlist(self, playlist_id: int, track_id: str) -> bool:
        """Quita una canción de una playlist y reordena las posiciones restantes."""
        now = int(time.time())
        with self._transaction() as cur:
            cur.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?;",
                (playlist_id, track_id),
            )
            deleted = cur.rowcount > 0
            if deleted:
                # Re-indexar posiciones
                cur.execute(
                    "SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position ASC, added_at ASC;",
                    (playlist_id,),
                )
                rows = cur.fetchall()
                for idx, row in enumerate(rows):
                    cur.execute(
                        "UPDATE playlist_tracks SET position = ? WHERE playlist_id = ? AND track_id = ?;",
                        (idx, playlist_id, row["track_id"]),
                    )
                cur.execute(
                    "UPDATE playlists SET updated_at = ? WHERE id = ?;",
                    (now, playlist_id),
                )
            return deleted

    def get_playlist_tracks(self, playlist_id: int) -> List[Dict[str, Any]]:
        """Retorna la lista ordenada de canciones con todos sus metadatos para una playlist dada."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT t.track_id, t.file_path, t.title, t.artist, t.album,
                   t.length_sec, t.art_url, t.play_count, pt.position, pt.added_at
            FROM playlist_tracks pt
            JOIN tracks t ON pt.track_id = t.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position ASC, pt.added_at ASC;
            """,
            (playlist_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ══════════════════════════════════════════════════════════════════════════
    # BÚSQUEDA GLOBAL MULTI-ENTIDAD (FASE 2 SUPPORT)
    # ══════════════════════════════════════════════════════════════════════════

    def search_library(
        self, query: str, limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Búsqueda global sobre canciones, artistas, álbumes y playlists."""
        clean = (query or "").strip()
        if not clean:
            return {"tracks": [], "artists": [], "albums": [], "playlists": []}

        pattern = f"%{clean}%"
        conn = self._get_connection()
        cur = conn.cursor()

        # Canciones
        cur.execute(
            """
            SELECT track_id, file_path, title, artist, album, length_sec, art_url
            FROM tracks
            WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
            ORDER BY play_count DESC
            LIMIT ?;
            """,
            (pattern, pattern, pattern, limit),
        )
        tracks = [dict(r) for r in cur.fetchall()]

        # Artistas
        cur.execute(
            """
            SELECT artist, SUM(play_count) AS total_plays, COUNT(track_id) AS track_count, MAX(art_url) AS art_url
            FROM tracks
            WHERE artist LIKE ? AND artist != ?
            GROUP BY artist
            ORDER BY total_plays DESC
            LIMIT ?;
            """,
            (pattern, UNKNOWN_ARTIST, limit),
        )
        artists = [dict(r) for r in cur.fetchall()]

        # Álbumes
        cur.execute(
            """
            SELECT album, artist, SUM(play_count) AS total_plays, COUNT(track_id) AS track_count, MAX(art_url) AS art_url
            FROM tracks
            WHERE album LIKE ? AND album != ? AND album != ''
            GROUP BY album, artist
            ORDER BY total_plays DESC
            LIMIT ?;
            """,
            (pattern, UNKNOWN_ALBUM, limit),
        )
        albums = [dict(r) for r in cur.fetchall()]

        # Playlists
        cur.execute(
            """
            SELECT p.id, p.name, p.cover_path, COUNT(pt.track_id) AS track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            WHERE p.name LIKE ?
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            LIMIT ?;
            """,
            (pattern, limit),
        )
        playlists = [dict(r) for r in cur.fetchall()]

        return {
            "tracks": tracks,
            "artists": artists,
            "albums": albums,
            "playlists": playlists,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # TRADUCCIÓN DE LETRAS (FRENTE 2)
    # ══════════════════════════════════════════════════════════════════════════

    def get_lyrics_translation(self, track_id: str, target_lang: str) -> Optional[Dict[str, Any]]:
        """Obtiene la traducción cacheada para un track y un idioma destino."""
        if not track_id or not target_lang:
            return None
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT track_id, target_lang, source_lang, engine_used, translated_lrc, updated_at
            FROM lyrics_translations
            WHERE track_id = ? AND target_lang = ?
            LIMIT 1;
            """,
            (track_id, target_lang.lower().strip()),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def save_lyrics_translation(
        self,
        track_id: str,
        target_lang: str,
        source_lang: str,
        engine_used: str,
        translated_lrc: str,
    ) -> bool:
        """Guarda o actualiza la traducción de letras de un track."""
        if not track_id or not target_lang or not translated_lrc:
            return False
        now = int(time.time())
        try:
            with self._transaction() as cur:
                # Asegurar que el track_id existe en tracks para satisfacer la Foreign Key
                cur.execute(
                    """
                    INSERT OR IGNORE INTO tracks (track_id, file_path, title, artist, album, length_sec, art_url, play_count, last_played_at)
                    VALUES (?, ?, 'Desconocido', 'Desconocido', 'Desconocido', 0, '', 0, 0);
                    """,
                    (track_id, f"unknown_path_{track_id}"),
                )

                cur.execute(
                    """
                    INSERT INTO lyrics_translations (
                        track_id, target_lang, source_lang, engine_used, translated_lrc, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(track_id, target_lang) DO UPDATE SET
                        source_lang = excluded.source_lang,
                        engine_used = excluded.engine_used,
                        translated_lrc = excluded.translated_lrc,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        track_id,
                        target_lang.lower().strip(),
                        source_lang,
                        engine_used,
                        translated_lrc,
                        now,
                        now,
                    ),
                )
            return True
        except Exception as e:
            _logger.exception("Error guardando traducción en BD: %s", e)
            return False


_global_db_instance: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    global _global_db_instance
    if _global_db_instance is None:
        _global_db_instance = DatabaseManager()
    return _global_db_instance
