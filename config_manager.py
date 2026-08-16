import json
import os
from copy import deepcopy

CONFIG_DIR = os.path.expanduser("~/.config/custom-music-player")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

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
    "stays_on_top": False,
    "view_mode": "normal",
    "volume": 1.0,
    "favorites": [],
    "background_image": "",
    "bg_slideshow_enabled": True,
    "bg_slideshow_interval_sec": 15,
    "bg_folder": "",
    "bg_aspect_mode": "stretch",
    "accent_color": "#ff1744",
    "background_type": "gradient",
    "theme_mode": "gradient_auto",
    "btn_gradient_effect": True,
    "auto_extract_wallpaper_color": True,
    "manual_gradient_colors": ["#ff1744", "#7b1fa2", "#0c0c10"],
    "auto_gradient_colors": ["#2b0b10", "#180718", "#08060c"],
    "bg_theme_colors": {},
    "user_playlists": {"Lista 1": [], "Lista 2": []},
    "custom_inner_image": "",
    "inner_art_mode": "auto",
    "music_folder": os.path.expanduser("~/Música") if os.path.exists(os.path.expanduser("~/Música")) else os.path.expanduser("~/Music"),
    "loop_mode": "None",
    "shuffle": False,
    "current_index": 0,
    "recent_tracks": [],
    "brand_name": "RED WORLD",
}


class ConfigManager:
    def __init__(self):
        self._ensure_dir()
        self.config = self.load()

    def _ensure_dir(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def load(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return deepcopy(DEFAULT_CONFIG)

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = deepcopy(DEFAULT_CONFIG)
            if isinstance(data, dict):
                config.update(data)

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

    def get_theme_color_for_image(self, image_path: str):
        if not image_path:
            return None
        return self.config.get("bg_theme_colors", {}).get(image_path)

    def set_theme_color_for_image(self, image_path: str, color_hex: str):
        if not image_path or not color_hex:
            return
        bg_colors = self.config.get("bg_theme_colors", {})
        bg_colors[image_path] = color_hex
        self.config["bg_theme_colors"] = bg_colors
        self.save()

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
