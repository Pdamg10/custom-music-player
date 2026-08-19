import json
import os
from copy import deepcopy

CONFIG_DIR = os.path.expanduser("~/.config/custom-music-player")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_PERSONALIZATION = {
    "background_type": "gradient",
    "theme_mode": "gradient_auto",
    "manual_gradient_colors": ["#ff1744", "#7b1fa2", "#0c0c10"],
    "auto_gradient_colors": ["#2b0b10", "#180718", "#08060c"],
    "custom_btn_gradient_colors": ["#ff1744", "#00e5ff", "#e040fb"],
    "custom_button_swatches": ["#ff1744", "#00e5ff", "#e040fb", "#00e676", "#ff9100", "#ff4081"],
    "accent_color": "#ff1744",
    "button_color_source": "gradient",
    "btn_gradient_effect": True,
    "wallpaper_btn_gradient_effect": False,
    "auto_extract_wallpaper_color": True,
    "background_image": "",
    "bg_folder": "",
    "bg_slideshow_enabled": True,
    "bg_slideshow_interval_sec": 15,
    "bg_aspect_mode": "stretch",
    "bg_theme_colors": {},
    "inner_art_mode": "auto",
    "custom_inner_image": "",
    "cover_shape": "rounded",
    "brand_name": "RED WORLD",
    "stays_on_top": False,
    "preferred_translation_lang": "es",
    "translation_mode": "auto",
}

PERSONALIZATION_KEYS = tuple(DEFAULT_PERSONALIZATION.keys())

DEFAULT_CONFIG = {
    "pos_x": None,
    "pos_y": None,
    "width": 350,
    "height": 430,
    "normal_width": 350,
    "normal_height": 430,
    "compact_width": 640,
    "compact_height": 260,
    "expanded_width": 1200,
    "expanded_height": 760,
    "preferred_player": None,
    "view_mode": "normal",
    "volume": 1.0,
    "favorites": [],
    "user_playlists": {"Lista 1": [], "Lista 2": []},
    "music_folder": os.path.expanduser("~/Música") if os.path.exists(os.path.expanduser("~/Música")) else os.path.expanduser("~/Music"),
    "loop_mode": "None",
    "shuffle": False,
    "current_index": 0,
    "recent_tracks": [],
    "personalization": {
        "normal": deepcopy(DEFAULT_PERSONALIZATION),
        "compact": deepcopy(DEFAULT_PERSONALIZATION),
        "expanded": deepcopy(DEFAULT_PERSONALIZATION),
    },
}


class ConfigManager:
    def __init__(self):
        self._ensure_dir()
        self.config = self.load()

    def _ensure_dir(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def _migrate_personalization(self, data: dict) -> dict:
        """Migra de forma segura un config plano hacia el esquema anidado por modo (normal, compact, expanded) y limpia las claves planas viejas de la raíz."""
        p_section = data.get("personalization")
        target_modes = ("normal", "compact", "expanded")

        needs_migration = not (isinstance(p_section, dict) and all(isinstance(p_section.get(m), dict) for m in target_modes))

        if needs_migration:
            base_personalization = {}
            for key in PERSONALIZATION_KEYS:
                if key in data:
                    base_personalization[key] = deepcopy(data[key])
                else:
                    base_personalization[key] = deepcopy(DEFAULT_PERSONALIZATION[key])

            new_personalization = {
                "normal": deepcopy(base_personalization),
                "compact": deepcopy(base_personalization),
                "expanded": deepcopy(base_personalization),
            }

            if isinstance(p_section, dict):
                for mode in target_modes:
                    if isinstance(p_section.get(mode), dict):
                        new_personalization[mode].update(deepcopy(p_section[mode]))

            data["personalization"] = new_personalization

        # Limpiar las 20 claves planas viejas de la raíz de data para garantizar cero datos muertos
        for key in PERSONALIZATION_KEYS:
            data.pop(key, None)

        return data

    def load(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return deepcopy(DEFAULT_CONFIG)

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = self._migrate_personalization(data)
            else:
                data = {}

            config = deepcopy(DEFAULT_CONFIG)
            config.update(data)

            # Asegurar que cada modo contenga todas las claves requeridas
            p_section = config.setdefault("personalization", {})
            for m in ("normal", "compact", "expanded"):
                if m not in p_section or not isinstance(p_section[m], dict):
                    p_section[m] = deepcopy(DEFAULT_PERSONALIZATION)
                else:
                    merged = deepcopy(DEFAULT_PERSONALIZATION)
                    merged.update(p_section[m])
                    p_section[m] = merged

            if config.get("view_mode") not in ("normal", "compact", "expanded"):
                config["view_mode"] = "normal"

            if isinstance(config.get("recent_tracks"), list):
                config["recent_tracks"] = [
                    track for track in config["recent_tracks"]
                    if isinstance(track, dict)
                    and (track.get("title", "") or "").strip().lower() not in (
                        "test title", "sin reproducción", "sin título", "no playback"
                    )
                    and (track.get("artist", "") or "").strip().lower() not in (
                        "test artist", "cargando metadatos..."
                    )
                ]

            return config
        except (OSError, json.JSONDecodeError) as e:
            print(f"[ConfigManager] Error cargando configuración: {e}")
            return deepcopy(DEFAULT_CONFIG)

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"[ConfigManager] Error guardando configuración: {e}")

    def _canonical_mode(self, mode: str | None) -> str:
        """Resuelve de forma estricta los alias de entrada ('small' -> 'normal')."""
        if not mode or mode in ("normal", "small"):
            return "normal"
        if mode in ("compact", "expanded"):
            return mode
        return "normal"

    def get_personalization(self, mode: str | None = None) -> dict:
        c_mode = self._canonical_mode(mode)
        p_section = self.config.setdefault("personalization", {})
        if c_mode not in p_section or not isinstance(p_section[c_mode], dict):
            p_section[c_mode] = deepcopy(DEFAULT_PERSONALIZATION)
        return p_section[c_mode]

    def set_personalization(self, mode: str | None, key: str, value: Any) -> None:
        c_mode = self._canonical_mode(mode)
        p_section = self.config.setdefault("personalization", {})
        if c_mode not in p_section or not isinstance(p_section[c_mode], dict):
            p_section[c_mode] = deepcopy(DEFAULT_PERSONALIZATION)
        p_section[c_mode][key] = value
        self.save()

    def set_personalization_dict(self, mode: str | None, new_dict: dict) -> None:
        c_mode = self._canonical_mode(mode)
        p_section = self.config.setdefault("personalization", {})
        if c_mode not in p_section or not isinstance(p_section[c_mode], dict):
            p_section[c_mode] = deepcopy(DEFAULT_PERSONALIZATION)
        for k, v in new_dict.items():
            if k in PERSONALIZATION_KEYS:
                p_section[c_mode][k] = deepcopy(v)
        self.save()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def is_favorite(self, title: str, artist: str) -> bool:
        favs = self.config.get("favorites", [])
        t_clean = (title or "").strip().lower()
        a_clean = (artist or "").strip().lower()
        if not t_clean or t_clean == "sin reproducción":
            return False
        return any(
            (fav.get("title", "") or "").strip().lower() == t_clean
            and (fav.get("artist", "") or "").strip().lower() == a_clean
            for fav in favs
        )

    def toggle_favorite(self, metadata: dict) -> bool:
        favs = list(self.config.get("favorites", []))
        title = metadata.get("title", "")
        artist = metadata.get("artist", "")
        t_clean = (title or "").strip().lower()
        a_clean = (artist or "").strip().lower()
        if not t_clean or t_clean == "sin reproducción":
            return False

        existing_index = next(
            (
                idx for idx, fav in enumerate(favs)
                if (fav.get("title", "") or "").strip().lower() == t_clean
                and (fav.get("artist", "") or "").strip().lower() == a_clean
            ),
            None,
        )

        if existing_index is not None:
            favs.pop(existing_index)
            is_fav = False
        else:
            favs.append({
                "title": title.strip(),
                "artist": artist.strip() if artist else "",
                "album": metadata.get("album", ""),
                "art_url": metadata.get("art_url", ""),
            })
            is_fav = True

        self.config["favorites"] = favs
        self.save()
        return is_fav

    def add_recent_track(self, metadata: dict, max_items: int = 10) -> None:
        title = (metadata.get("title") or "").strip()
        artist = (metadata.get("artist") or "").strip()
        invalid_titles = {"sin reproducción", "no playback", "sin título", "test title"}
        invalid_artists = {"cargando metadatos...", "test artist"}
        if not title or title.lower() in invalid_titles or artist.lower() in invalid_artists:
            return

        recents = list(self.config.get("recent_tracks", []))
        t_clean = title.lower()
        a_clean = artist.lower()
        if recents and (recents[0].get("title", "") or "").strip().lower() == t_clean and (recents[0].get("artist", "") or "").strip().lower() == a_clean:
            return

        recents = [
            track for track in recents
            if not (
                (track.get("title", "") or "").strip().lower() == t_clean
                and (track.get("artist", "") or "").strip().lower() == a_clean
            )
        ]

        recents.insert(0, {
            "title": title,
            "artist": artist,
            "album": metadata.get("album", ""),
            "art_url": metadata.get("art_url", ""),
            "file_path": metadata.get("file_path", ""),
        })
        self.config["recent_tracks"] = recents[:max_items]
        self.save()

    def get_recent_tracks(self) -> list:
        return list(self.config.get("recent_tracks", []))

    def get_theme_color_for_image(self, image_path: str, mode: str | None = "normal"):
        if not image_path:
            return None
        mode_cfg = self.get_personalization(mode)
        return mode_cfg.get("bg_theme_colors", {}).get(image_path)

    def set_theme_color_for_image(self, image_path: str, color_hex: str, mode: str | None = "normal"):
        if not image_path or not color_hex:
            return
        c_mode = self._canonical_mode(mode)
        mode_cfg = self.get_personalization(c_mode)
        bg_colors = dict(mode_cfg.get("bg_theme_colors", {}))
        bg_colors[image_path] = color_hex
        self.set_personalization(c_mode, "bg_theme_colors", bg_colors)

    def get_user_playlists(self) -> dict:
        return self.config.get("user_playlists", {"Lista 1": [], "Lista 2": []})

    def add_user_playlist(self, name: str) -> bool:
        playlists = self.get_user_playlists()
        if name in playlists:
            return False
        playlists[name] = []
        self.config["user_playlists"] = playlists
        self.save()
        return True

    def remove_user_playlist(self, name: str) -> None:
        playlists = self.get_user_playlists()
        if name in playlists:
            del playlists[name]
            self.config["user_playlists"] = playlists
            self.save()
