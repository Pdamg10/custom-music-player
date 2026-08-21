import os
import re
import json
import logging
import urllib.parse
from typing import List, Optional, Dict, Any, Callable
import requests

from lyrics_manager import LyricLine, parse_lrc_content
from database_manager import get_database_manager

_logger = logging.getLogger("custom_music_player.lyrics_translator")

SUPPORTED_LANGUAGES = {
    "es": "Español",
    "en": "Inglés",
    "pt": "Portugués",
    "fr": "Francés",
    "it": "Italiano",
    "de": "Alemán",
    "ja": "Japonés",
    "zh": "Chino",
    "ru": "Ruso",
    "ko": "Coreano",
}


def _format_time_ms_to_lrc_tag(time_ms: int) -> str:
    if time_ms < 0:
        return ""
    total_sec = time_ms / 1000.0
    mins = int(total_sec // 60)
    secs = total_sec % 60
    return f"[{mins:02d}:{secs:05.2f}]"


class LyricsTranslator:
    """Motor de traducción de letras con soporte Online (Google Translate / DeepL) y Offline (Argos Translate)."""

    _instance: Optional["LyricsTranslator"] = None

    def __new__(cls) -> "LyricsTranslator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            from config_manager import get_platform_base_dir
            cls._instance._models_dir = get_platform_base_dir("data", "models")
            os.makedirs(cls._instance._models_dir, exist_ok=True)
        return cls._instance

    def get_cached_translation(self, track_id: str, target_lang: str) -> Optional[List[LyricLine]]:
        """Recupera la traducción serializada desde SQLite si ya fue traducida previamente."""
        if not track_id or not target_lang:
            return None

        db = get_database_manager()
        row = db.get_lyrics_translation(track_id, target_lang)
        if row and row.get("translated_lrc"):
            lines, _ = parse_lrc_content(row["translated_lrc"])
            if lines:
                return lines
        return None

    def translate_and_cache(
        self,
        track_id: str,
        lines: List[LyricLine],
        target_lang: str,
        mode: str = "auto",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[LyricLine]:
        """Traduce una lista de LyricLines al idioma destino, valida la integridad de líneas y persiste en caché."""
        if not lines or (is_cancelled and is_cancelled()):
            return []

        target_lang_clean = target_lang.lower().strip()
        lines_text = [l.text or "" for l in lines]

        translated_texts: List[str] = []
        engine_used = "online"

        if mode == "auto":
            try:
                translated_texts = self._translate_online_batch_safe(lines_text, target_lang_clean, is_cancelled=is_cancelled)
                if is_cancelled and is_cancelled():
                    return []
                engine_used = "google_web"
            except Exception as e_online:
                if is_cancelled and is_cancelled():
                    return []
                _logger.warning("Fallo en traducción online en modo auto (%s). Intentando offline...", e_online)
                try:
                    translated_texts = self._translate_offline_batch_safe(lines_text, target_lang_clean, progress_callback, is_cancelled=is_cancelled)
                    if is_cancelled and is_cancelled():
                        return []
                    engine_used = "argos_offline"
                except Exception as e_offline:
                    if is_cancelled and is_cancelled():
                        return []
                    _logger.error("Doble fallo en modo auto: Online (%s), Offline (%s)", e_online, e_offline)
                    raise RuntimeError("No se pudo traducir: sin conexión a internet y sin modelo offline instalado para este idioma.") from e_online
        elif mode == "online_only":
            try:
                translated_texts = self._translate_online_batch_safe(lines_text, target_lang_clean, is_cancelled=is_cancelled)
                if is_cancelled and is_cancelled():
                    return []
                engine_used = "google_web"
            except Exception as exc:
                if is_cancelled and is_cancelled():
                    return []
                _logger.error("Error en traducción online: %s", exc)
                raise RuntimeError(f"Error en traducción online: {exc}") from exc
        elif mode == "offline_only":
            try:
                translated_texts = self._translate_offline_batch_safe(lines_text, target_lang_clean, progress_callback, is_cancelled=is_cancelled)
                if is_cancelled and is_cancelled():
                    return []
                engine_used = "argos_offline"
            except Exception as exc:
                if is_cancelled and is_cancelled():
                    return []
                _logger.error("Error en traducción offline: %s", exc)
                raise RuntimeError(f"Error en traducción offline: {exc}") from exc
        else:
            raise ValueError(f"Modo de traducción desconocido: {mode}")

        if is_cancelled and is_cancelled():
            return []

        # 3. Reconstruir lista preservando los timestamps [mm:ss.xx]
        translated_lines: List[LyricLine] = []
        lrc_rows: List[str] = []

        for idx, orig_line in enumerate(lines):
            t_text = translated_texts[idx] if idx < len(translated_texts) else orig_line.text
            translated_lines.append(LyricLine(time_ms=orig_line.time_ms, text=t_text))

            if orig_line.time_ms >= 0:
                tag = _format_time_ms_to_lrc_tag(orig_line.time_ms)
                lrc_rows.append(f"{tag}{t_text}")
            else:
                lrc_rows.append(t_text)

        # 4. Serializar y guardar en SQLite
        full_lrc_str = "\n".join(lrc_rows)
        db = get_database_manager()
        db.save_lyrics_translation(
            track_id=track_id,
            target_lang=target_lang_clean,
            source_lang="auto",
            engine_used=engine_used,
            translated_lrc=full_lrc_str,
        )

        return translated_lines

    # ══════════════════════════════════════════════════════════════════════════
    # MOTOR ONLINE CON BATCHING Y VALIDACIÓN ESTRICTA DE INTEGRIDAD
    # ══════════════════════════════════════════════════════════════════════════

    def _translate_single_online(self, text: str, target_lang: str) -> str:
        """Traduce una sola frase vía endpoint web de traducción."""
        if not text or not text.strip():
            return text
        url = (
            f"https://translate.googleapis.com/translate_a/single?"
            f"client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            return "".join([part[0] for part in data[0] if part and len(part) > 0 and part[0]]).strip()
        return text

    def _translate_online_batch_safe(
        self,
        lines_text: List[str],
        target_lang: str,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """Traduce un bloque de líneas validando la correspondencia exacta de elementos."""
        total_expected = len(lines_text)
        if total_expected == 0 or (is_cancelled and is_cancelled()):
            return []

        # Si son muy pocas líneas, traducir directo
        if total_expected <= 3:
            res = []
            for t in lines_text:
                if is_cancelled and is_cancelled():
                    return []
                res.append(self._translate_single_online(t, target_lang))
            return res

        # INTENTO 1: Batching con token delimitador
        if is_cancelled and is_cancelled():
            return []
        delimiter_1 = "\n<<<SYNC_LRC_BREAK>>>\n"
        combined_text_1 = delimiter_1.join(lines_text)
        try:
            raw_res_1 = self._translate_single_online(combined_text_1, target_lang)
            if is_cancelled and is_cancelled():
                return []
            chunks_1 = [c.strip() for c in re.split(r'<<< ?SYNC_LRC_BREAK ?>>>', raw_res_1)]
            if len(chunks_1) == total_expected:
                return chunks_1
        except Exception as e:
            _logger.debug("Intento 1 de batch falló: %s", e)

        # INTENTO 2: Batching con delimitador alternativo
        if is_cancelled and is_cancelled():
            return []
        delimiter_2 = "\n[--LRC_LINE--]\n"
        combined_text_2 = delimiter_2.join(lines_text)
        try:
            raw_res_2 = self._translate_single_online(combined_text_2, target_lang)
            if is_cancelled and is_cancelled():
                return []
            chunks_2 = [c.strip() for c in re.split(r'\[-- ?LRC_LINE ?--\]', raw_res_2)]
            if len(chunks_2) == total_expected:
                return chunks_2
        except Exception as e:
            _logger.debug("Intento 2 de batch falló: %s", e)

        # FALLBACK SEGURO: Traducción individual línea por línea con chequeo de cancelación
        _logger.info("Batch desalineado. Ejecutando fallback seguro línea por línea...")
        safe_results: List[str] = []
        for line_t in lines_text:
            if is_cancelled and is_cancelled():
                _logger.debug("Traducción online abortada por cancelación.")
                return []
            if not line_t.strip():
                safe_results.append("")
            else:
                try:
                    safe_results.append(self._translate_single_online(line_t, target_lang))
                except Exception:
                    safe_results.append(line_t)
        return safe_results

    # ══════════════════════════════════════════════════════════════════════════
    # MOTOR OFFLINE (ARGOS TRANSLATE) CON DESCARGA AUTOMÁTICA
    # ══════════════════════════════════════════════════════════════════════════

    def _translate_offline_batch_safe(
        self,
        lines_text: List[str],
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """Traduce usando modelos locales Argos Translate. Descarga el paquete automáticamente si no existe."""
        if is_cancelled and is_cancelled():
            return []

        try:
            import argostranslate.package
            import argostranslate.translate
        except ImportError as exc:
            raise RuntimeError("El paquete 'argostranslate' no está instalado en el entorno.") from exc

        # 1. Buscar si existe modelo instalado para auto -> target_lang (o en -> target_lang)
        installed_languages = argostranslate.translate.get_installed_languages()
        target_lang_obj = next((lang for lang in installed_languages if lang.code == target_lang), None)

        if not target_lang_obj:
            if is_cancelled and is_cancelled():
                return []

            # Descarga automática del modelo
            if progress_callback:
                progress_callback(10, 100, f"Buscando modelo offline para {target_lang}...")

            argostranslate.package.update_package_index()
            if is_cancelled and is_cancelled():
                return []

            available_packages = argostranslate.package.get_available_packages()

            # Intentar encontrar paquete desde inglés al destino o directamente
            pkg_to_install = next(
                (pkg for pkg in available_packages if pkg.to_code == target_lang),
                None,
            )

            if not pkg_to_install:
                raise RuntimeError(f"No se encontró un modelo Argos Translate disponible para el idioma '{target_lang}'.")

            if is_cancelled and is_cancelled():
                return []

            if progress_callback:
                progress_callback(30, 100, f"Descargando modelo offline ({pkg_to_install.package_version})...")

            download_path = pkg_to_install.download()

            if is_cancelled and is_cancelled():
                return []

            if progress_callback:
                progress_callback(80, 100, "Instalando modelo offline en disco...")

            argostranslate.package.install_from_path(download_path)

            if is_cancelled and is_cancelled():
                return []

            if progress_callback:
                progress_callback(100, 100, "Modelo offline listo.")

            installed_languages = argostranslate.translate.get_installed_languages()

        if is_cancelled and is_cancelled():
            return []

        # Encontrar traducción disponible
        from_lang = next((lang for lang in installed_languages if lang.code == "en"), installed_languages[0] if installed_languages else None)
        to_lang = next((lang for lang in installed_languages if lang.code == target_lang), None)

        if not from_lang or not to_lang:
            raise RuntimeError(f"No se pudo inicializar la traducción local para '{target_lang}'.")

        translation = from_lang.get_translation(to_lang)
        if not translation:
            raise RuntimeError(f"No hay ruta de traducción local directa hacia '{target_lang}'.")

        # Traducir líneas con chequeo de cancelación en cada iteración
        results = []
        for line in lines_text:
            if is_cancelled and is_cancelled():
                _logger.debug("Traducción offline abortada por cancelación.")
                return []
            if not line.strip():
                results.append("")
            else:
                try:
                    results.append(translation.translate(line))
                except Exception:
                    results.append(line)
        return results


_global_translator_instance: Optional[LyricsTranslator] = None


def get_lyrics_translator() -> LyricsTranslator:
    global _global_translator_instance
    if _global_translator_instance is None:
        _global_translator_instance = LyricsTranslator()
    return _global_translator_instance
