import os
import re
import time
import logging
import urllib.parse
from typing import List, Optional, Callable
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
        title: str = "",
        artist: str = "",
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
            # Opción 1: Traducción online primaria (Google Web)
            try:
                translated_texts = self._translate_online_batch_safe(lines_text, target_lang_clean, progress_callback=progress_callback, is_cancelled=is_cancelled)
                if is_cancelled and is_cancelled():
                    return []
                engine_used = "google_web"
            except Exception as e_online:
                if is_cancelled and is_cancelled():
                    return []
                _logger.warning("Fallo en traducción online primaria (%s). Probando opción 2: Letras.com...", e_online)

                # Opción 2: Letras.com (traducción humana colaborativa)
                try:
                    if progress_callback:
                        progress_callback(30, 100, "Consultando traducción en Letras.com...")
                    from letras_provider import fetch_letras_com_translation
                    letras_texts = fetch_letras_com_translation(title, artist, lines_text, target_lang_clean)
                    if letras_texts and len(letras_texts) == len(lines_text):
                        translated_texts = letras_texts
                        engine_used = "letras_com"
                    else:
                        raise RuntimeError("Sin traducción disponible en Letras.com para este tema")
                except Exception as e_letras:
                    if is_cancelled and is_cancelled():
                        return []
                    _logger.warning("Fallo en Letras.com (%s). Probando opción 3: Offline (Argos)...", e_letras)

                    # Opción 3: Argos Translate Offline
                    try:
                        translated_texts = self._translate_offline_batch_safe(lines_text, target_lang_clean, progress_callback, is_cancelled=is_cancelled)
                        if is_cancelled and is_cancelled():
                            return []
                        engine_used = "argos_offline"
                    except Exception as e_offline:
                        if is_cancelled and is_cancelled():
                            return []
                        _logger.error("Fallo en todos los motores: Online (%s), Letras.com (%s), Offline (%s)", e_online, e_letras, e_offline)
                        raise RuntimeError("No se pudo traducir: sin conexión a internet ni modelo offline instalado.") from e_online

        elif mode == "letras":
            # Modo explícito: Priorizar Letras.com humana, con fallback automático a Google Online
            if progress_callback:
                progress_callback(10, 100, "Buscando traducción en Letras.com...")
            try:
                from letras_provider import fetch_letras_com_translation
                letras_texts = fetch_letras_com_translation(title, artist, lines_text, target_lang_clean)
                if letras_texts and len(letras_texts) == len(lines_text):
                    translated_texts = letras_texts
                    engine_used = "letras_com"
                else:
                    raise RuntimeError("No se encontró traducción en Letras.com")
            except Exception as exc_letras:
                if is_cancelled and is_cancelled():
                    return []
                _logger.info("Letras.com sin traducción directa (%s). Usando fallback online...", exc_letras)
                if progress_callback:
                    progress_callback(35, 100, "Usando fallback online...")
                translated_texts = self._translate_online_batch_safe(lines_text, target_lang_clean, progress_callback=progress_callback, is_cancelled=is_cancelled)
                engine_used = "google_web"

        elif mode == "online_only":
            try:
                translated_texts = self._translate_online_batch_safe(lines_text, target_lang_clean, progress_callback=progress_callback, is_cancelled=is_cancelled)
                if is_cancelled and is_cancelled():
                    return []
                engine_used = "google_web"
            except Exception as exc:
                if is_cancelled and is_cancelled():
                    return []
                _logger.warning("Fallo en Google web (%s). Intentando segunda opción online (Letras.com)...", exc)
                try:
                    from letras_provider import fetch_letras_com_translation
                    letras_texts = fetch_letras_com_translation(title, artist, lines_text, target_lang_clean)
                    if letras_texts and len(letras_texts) == len(lines_text):
                        translated_texts = letras_texts
                        engine_used = "letras_com"
                    else:
                        raise exc
                except Exception:
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

    def _translate_single_online(
        self,
        text: str,
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> str:
        """Traduce una sola frase vía endpoint web de traducción con reintento progresivo en caso de rate limit 429."""
        if not text or not text.strip():
            return text

        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={target_lang}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }
        data = [("q", text)]

        max_retries = 3
        backoffs = [1.5, 3.0, 6.0]

        for attempt in range(max_retries + 1):
            if is_cancelled and is_cancelled():
                return text

            try:
                resp = requests.post(url, data=data, headers=headers, timeout=10)
                if resp.status_code == 429:
                    if attempt < max_retries:
                        sleep_time = backoffs[attempt]
                        _logger.warning("Rate limit 429 en Google Translate. Reintentando en %ss (intento %d/%d)...", sleep_time, attempt + 1, max_retries)
                        if progress_callback:
                            progress_callback(0, 0, f"Reintentando traducción ({attempt + 1}/{max_retries})...")
                        elapsed = 0.0
                        while elapsed < sleep_time:
                            if is_cancelled and is_cancelled():
                                return text
                            time.sleep(0.2)
                            elapsed += 0.2
                        continue
                    else:
                        _logger.error("Rate limit 429 en Google Translate persistente tras %d reintentos.", max_retries)
                        resp.raise_for_status()

                resp.raise_for_status()
                res_data = resp.json()
                if isinstance(res_data, list) and len(res_data) > 0:
                    first = res_data[0]
                    if isinstance(first, list) and len(first) > 0:
                        if isinstance(first[0], str):
                            return str(first[0]).strip()
                        elif isinstance(first[0], list):
                            return "".join([part[0] for part in first[0] if part and len(part) > 0 and part[0]]).strip()
                    elif isinstance(first, str) and first:
                        return first.strip()
                return text
            except Exception as e:
                # Fallback secundario a GET si POST diera algún problema
                if attempt >= max_retries or (is_cancelled and is_cancelled()):
                    try:
                        get_url = f"{url}&q={urllib.parse.quote(text)}"
                        get_resp = requests.get(get_url, headers=headers, timeout=8)
                        if get_resp.status_code == 200:
                            g_data = get_resp.json()
                            if isinstance(g_data, list) and len(g_data) > 0:
                                g_first = g_data[0]
                                if isinstance(g_first, list) and len(g_first) > 0 and isinstance(g_first[0], str):
                                    return str(g_first[0]).strip()
                                elif isinstance(g_first, str):
                                    return g_first.strip()
                    except Exception:
                        pass
                    return text
                time.sleep(1.0)
        return text

    def _translate_online_chunk_post(
        self,
        chunk: List[str],
        target_lang: str,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """Traduce un bloque de líneas enviando múltiples parámetros 'q' vía POST.

        Google Translate detecta de manera autónoma el idioma de origen para CADA línea,
        permitiendo que canciones multilingües (ej: japonés/inglés, coreano/español)
        se traduzcan con total precisión verso por verso sin pérdidas de sincronía.
        """
        if not chunk or (is_cancelled and is_cancelled()):
            return []

        non_empty = [(i, t) for i, t in enumerate(chunk) if t and t.strip()]
        if not non_empty:
            return list(chunk)

        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={target_lang}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }
        data = [("q", t) for _, t in non_empty]

        max_retries = 3
        backoffs = [1.5, 3.0, 6.0]

        for attempt in range(max_retries + 1):
            if is_cancelled and is_cancelled():
                return []
            try:
                resp = requests.post(url, data=data, headers=headers, timeout=12)
                if resp.status_code == 429:
                    if attempt < max_retries:
                        sleep_time = backoffs[attempt]
                        _logger.warning("Rate limit 429 en batch POST. Esperando %ss...", sleep_time)
                        elapsed = 0.0
                        while elapsed < sleep_time:
                            if is_cancelled and is_cancelled():
                                return []
                            time.sleep(0.2)
                            elapsed += 0.2
                        continue
                    else:
                        resp.raise_for_status()

                resp.raise_for_status()
                res_data = resp.json()

                result = list(chunk)
                if isinstance(res_data, list):
                    # Cuando se envía 1 solo elemento no vacío
                    if len(non_empty) == 1:
                        raw_item = res_data[0] if len(res_data) > 0 else ""
                        if isinstance(raw_item, list) and len(raw_item) > 0:
                            t_val = str(raw_item[0]).strip()
                        elif isinstance(raw_item, str):
                            t_val = raw_item.strip()
                        else:
                            t_val = non_empty[0][1]
                        result[non_empty[0][0]] = t_val
                        return result

                    # Cuando la respuesta tiene exactamente la cantidad de líneas enviadas
                    if len(res_data) == len(non_empty):
                        for (orig_idx, orig_text), item in zip(non_empty, res_data):
                            if isinstance(item, list) and len(item) > 0:
                                t_val = str(item[0]).strip() if item[0] is not None else orig_text
                            elif isinstance(item, str):
                                t_val = item.strip()
                            else:
                                t_val = orig_text
                            result[orig_idx] = t_val
                        return result
                    else:
                        _logger.warning("Discrepancia en cantidad de resultados batch: %d recibidos, %d esperados", len(res_data), len(non_empty))
                        raise ValueError("Discrepancia en longitud de respuesta batch POST")
                else:
                    raise ValueError(f"Formato inesperado en respuesta POST: {type(res_data)}")

            except Exception as exc:
                if attempt < max_retries and not (is_cancelled and is_cancelled()):
                    _logger.debug("Reintentando chunk POST tras error: %s", exc)
                    time.sleep(1.0)
                    continue
                _logger.warning("Fallo en batch POST para chunk (%s). Activando fallback individual...", exc)
                break

        # Fallback individual seguro para este bloque con detección automática individual
        result = list(chunk)
        for orig_idx, orig_text in non_empty:
            if is_cancelled and is_cancelled():
                return []
            try:
                result[orig_idx] = self._translate_single_online(orig_text, target_lang, is_cancelled=is_cancelled)
            except Exception:
                result[orig_idx] = orig_text
        return result

    def _translate_online_batch_safe(
        self,
        lines_text: List[str],
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[str]:
        """Traduce un bloque de líneas por lotes en bloques POST independientes.

        Garantiza preservación 1 a 1 de timestamps y detección autónoma de idiomas mezclados.
        """
        total_lines = len(lines_text)
        if total_lines == 0 or (is_cancelled and is_cancelled()):
            return []

        # Bloques de 35 líneas por petición (optimiza latencia y respeta límites de payload)
        chunk_size = 35
        all_translated: List[str] = []

        for start_idx in range(0, total_lines, chunk_size):
            if is_cancelled and is_cancelled():
                return []
            chunk = lines_text[start_idx : start_idx + chunk_size]
            current_done = min(start_idx + len(chunk), total_lines)
            if progress_callback:
                pct = int((current_done / total_lines) * 90)
                progress_callback(pct, 100, f"Traduciendo versos ({current_done}/{total_lines})...")

            chunk_result = self._translate_online_chunk_post(chunk, target_lang, is_cancelled=is_cancelled)
            if is_cancelled and is_cancelled():
                return []
            all_translated.extend(chunk_result)

        if progress_callback:
            progress_callback(100, 100, "Traducción completada")

        return all_translated

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
