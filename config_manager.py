import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/custom-music-player")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "pos_x": None,
    "pos_y": None,
    "width": 280,
    "height": 340,
    "compact_width": 280,
    "compact_height": 68,
    "preferred_player": None,
    "stays_on_top": True,
    "compact_mode": False,
    "volume": 1.0,
    "favorites": [],
    "background_image": "/home/phame/Imágenes/fondo para mi reproducctor/Cain , Break My Heart.jpeg",
    "bg_slideshow_enabled": True,
    "bg_slideshow_interval_sec": 15,
    "bg_folder": "/home/phame/Imágenes/fondo para mi reproducctor"
}

class ConfigManager:
    def __init__(self):
        self._ensure_dir()
        self.config = self.load()

    def _ensure_dir(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)

    def load(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"[ConfigManager] Error cargando configuración: {e}")
            return DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error guardando configuración: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def is_favorite(self, title: str, artist: str) -> bool:
        favs = self.config.get("favorites", [])
        return any(f.get("title") == title and f.get("artist") == artist for f in favs)

    def toggle_favorite(self, metadata: dict) -> bool:
        favs = self.config.get("favorites", [])
        title = metadata.get("title", "")
        artist = metadata.get("artist", "")
        if not title or title == "Sin reproducción":
            return False

        existing_index = None
        for idx, f in enumerate(favs):
            if f.get("title") == title and f.get("artist") == artist:
                existing_index = idx
                break

        if existing_index is not None:
            favs.pop(existing_index)
            is_fav = False
        else:
            favs.append({
                "title": title,
                "artist": artist,
                "album": metadata.get("album", ""),
                "art_url": metadata.get("art_url", "")
            })
            is_fav = True

        self.config["favorites"] = favs
        self.save()
        return is_fav
