import re
import json
import html
import urllib.request
import urllib.parse
import logging
from typing import List, Tuple, Optional, Dict, Any

_logger = logging.getLogger("custom_music_player.letras_provider")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SOLR_SEARCH_URL = "https://solr.sscdn.co/letras/m5/?q={query}&wt=json"


def _clean_word_set(text: str) -> set:
    return set(re.findall(r'\w+', (text or "").lower()))


def search_letras(query: str, artist: str = "") -> List[Dict[str, Any]]:
    """
    Realiza una búsqueda en la API Solr de letras.com / letras.mus.br.
    Retorna una lista de documentos candidatos ordenados por relevancia.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    url = SOLR_SEARCH_URL.format(query=urllib.parse.quote(clean_q))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                return []
            raw = resp.read().decode("utf-8", errors="ignore").strip()
            if raw.endswith(";"):
                raw = raw[:-1].strip()
            if raw.startswith("s(") and raw.endswith(")"):
                raw = raw[2:-1]
            data = json.loads(raw)
            docs = data.get("response", {}).get("docs", [])
            valid_docs = [d for d in docs if d.get("dns") and d.get("url")]

            if artist and artist.strip() and valid_docs:
                clean_artist_norm = re.sub(r'[^a-zA-Z0-9]', '', artist).lower()
                def artist_rank(d: dict) -> int:
                    d_art = re.sub(r'[^a-zA-Z0-9]', '', d.get("art", "")).lower()
                    d_dns = re.sub(r'[^a-zA-Z0-9]', '', d.get("dns", "")).lower()
                    if clean_artist_norm in d_art or clean_artist_norm in d_dns:
                        return 0
                    if d_art in clean_artist_norm or d_dns in clean_artist_norm:
                        return 1
                    return 2
                valid_docs.sort(key=artist_rank)

            return valid_docs
    except Exception as exc:
        _logger.warning("Error buscando en letras.com para query '%s': %s", clean_q, exc)
        return []


def get_song_lyrics(dns: str, url_id: str) -> Optional[str]:
    """
    Descarga y extrae la letra original de una canción en https://www.letras.com/{dns}/{url_id}/.
    """
    if not dns or not url_id:
        return None

    page_url = f"https://www.letras.com/{dns}/{url_id}/"
    req = urllib.request.Request(page_url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status != 200:
                return None
            html_doc = resp.read().decode("utf-8", errors="ignore")

            m = re.search(r'''<div[^>]*class=["'][^"']*lyric-original[^"']*["']>(.*?)</div>''', html_doc, re.DOTALL)
            if not m:
                m = re.search(r'''<div[^>]*class=["'][^"']*lyric[^"']*["']>(.*?)</div>''', html_doc, re.DOTALL)
            if not m:
                return None

            inner = m.group(1)
            inner = re.sub(r'<script.*?</script>', '', inner, flags=re.DOTALL)
            inner = re.sub(r'</p>\s*<p[^>]*>', '\n\n', inner, flags=re.IGNORECASE)
            inner = re.sub(r'<p[^>]*>', '', inner, flags=re.IGNORECASE)
            inner = re.sub(r'</p>', '', inner, flags=re.IGNORECASE)
            inner = re.sub(r'<br\s*/?>', '\n', inner, flags=re.IGNORECASE)
            inner = re.sub(r'<[^>]+>', '', inner)

            raw_lines = [html.unescape(l).strip() for l in inner.split('\n')]
            lines = [l for l in raw_lines if l]
            if lines:
                return "\n".join(lines)
    except Exception as exc:
        _logger.warning("Error extrayendo letra de letras.com (%s/%s): %s", dns, url_id, exc)

    return None


def get_song_translation_pairs(dns: str, url_id: str, lang: str = "es") -> List[Tuple[str, str]]:
    """
    Descarga y extrae los pares (verso_original, verso_traducido) desde la página de traducción.
    En letras.com el idioma principal es español ('es').
    En letras.mus.br el idioma principal es portugués ('pt').
    """
    if not dns or not url_id:
        return []

    if lang == "pt":
        trad_url = f"https://www.letras.mus.br/{dns}/{url_id}/traducao.html"
    else:
        trad_url = f"https://www.letras.com/{dns}/{url_id}/traduccion.html"

    req = urllib.request.Request(trad_url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status != 200:
                return []
            html_doc = resp.read().decode("utf-8", errors="ignore")

            pattern = re.compile(
                r'''<span\s+class\s*=\s*["']verse["']>\s*<span>(.*?)</span>\s*<span\s+class\s*=\s*["']romanization["']>(.*?)</span>\s*</span>''',
                re.DOTALL
            )
            matches = pattern.findall(html_doc)
            pairs: List[Tuple[str, str]] = []
            for trans_html, orig_html in matches:
                clean_trans = html.unescape(re.sub(r'<[^>]+>', '', trans_html)).strip()
                clean_orig = html.unescape(re.sub(r'<[^>]+>', '', orig_html)).strip()
                if clean_trans:
                    pairs.append((clean_orig, clean_trans))

            return pairs
    except Exception as exc:
        _logger.debug("Sin traducción en letras.com para %s/%s (%s): %s", dns, url_id, lang, exc)
        return []


def align_lyrics_with_translation(lyrics_lines_texts: List[str], pairs: List[Tuple[str, str]]) -> List[str]:
    """
    Alinea inteligentemente una lista de oraciones (originales) con los pares de traducción de letras.com.
    Maneja diferencias donde un timestamp LRC abarca múltiples versos de letras.com.
    """
    if not lyrics_lines_texts or not pairs:
        return []

    aligned: List[str] = []
    pair_idx = 0
    num_pairs = len(pairs)

    for line in lyrics_lines_texts:
        line_clean = re.sub(r'[^a-zA-Z0-9\s]', '', line).lower().strip()
        matched_translations: List[str] = []

        while pair_idx < num_pairs:
            orig_p, trans_p = pairs[pair_idx]
            orig_p_clean = re.sub(r'[^a-zA-Z0-9\s]', '', orig_p).lower().strip()

            if not orig_p_clean:
                pair_idx += 1
                continue

            # 1. Coincidencia de subcadena exacta
            if orig_p_clean in line_clean or line_clean in orig_p_clean:
                matched_translations.append(trans_p)
                pair_idx += 1
            else:
                # 2. Coincidencia por conjunto de palabras con umbral >= 65%
                words_p = _clean_word_set(orig_p)
                words_l = _clean_word_set(line)
                if words_p and words_l and (len(words_p.intersection(words_l)) / len(words_p)) >= 0.65:
                    matched_translations.append(trans_p)
                    pair_idx += 1
                else:
                    break

        if matched_translations:
            aligned.append(" ".join(matched_translations))
        else:
            # Búsqueda global de rescate si el cursor secuencial se desfasó
            best_t: Optional[str] = None
            for p_orig, p_trans in pairs:
                p_clean = re.sub(r'[^a-zA-Z0-9\s]', '', p_orig).lower().strip()
                if p_clean and (p_clean in line_clean or line_clean in p_clean):
                    best_t = p_trans
                    break
            aligned.append(best_t or line)

    return aligned


def fetch_letras_com_lyrics(title: str, artist: str = "") -> Optional[str]:
    """
    Punto de entrada de respaldo para obtener letras de letras.com cuando el motor original falla.
    """
    from lyrics_manager import clean_song_metadata
    clean_t, clean_a = clean_song_metadata(title, artist)

    queries = []
    if clean_a and clean_a.lower() not in ("online", "desconocido", "youtube", "unknown", "various artists"):
        queries.append(f"{clean_a} {clean_t}")
    if clean_t:
        queries.append(clean_t)
    if (title or "").strip() and (title or "").strip() not in queries:
        queries.append((title or "").strip())

    for q in queries:
        docs = search_letras(q, artist=clean_a)
        if docs:
            for d in docs[:3]:
                dns = d.get("dns")
                uid = d.get("url")
                if dns and uid:
                    lyr = get_song_lyrics(dns, uid)
                    if lyr and lyr.strip():
                        _logger.info("Letra obtenida exitosamente desde letras.com para: %s - %s", dns, uid)
                        return lyr.strip()

    return None


def fetch_letras_com_translation(
    title: str,
    artist: str,
    lyrics_lines_texts: List[str],
    target_lang: str = "es",
) -> Optional[List[str]]:
    """
    Punto de entrada como segunda opción de traducción humana desde letras.com / letras.mus.br.
    Retorna la lista de textos traducidos alineados 1-a-1 con las líneas de entrada.
    """
    lang_clean = target_lang.lower().strip()
    if lang_clean not in ("es", "pt"):
        return None

    from lyrics_manager import clean_song_metadata
    clean_t, clean_a = clean_song_metadata(title, artist)

    queries = []
    if clean_a and clean_a.lower() not in ("online", "desconocido", "youtube", "unknown", "various artists"):
        queries.append(f"{clean_a} {clean_t}")
    if clean_t:
        queries.append(clean_t)

    for q in queries:
        docs = search_letras(q, artist=clean_a)
        if docs:
            for d in docs[:3]:
                dns = d.get("dns")
                uid = d.get("url")
                if dns and uid:
                    pairs = get_song_translation_pairs(dns, uid, lang=lang_clean)
                    if pairs:
                        aligned = align_lyrics_with_translation(lyrics_lines_texts, pairs)
                        if aligned and len(aligned) == len(lyrics_lines_texts):
                            _logger.info("Traducción humana obtenida desde letras.com para: %s - %s (%d versos)", dns, uid, len(pairs))
                            return aligned

    return None
