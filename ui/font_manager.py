import os
import sys
import zipfile
import logging
from typing import Optional, List, Dict, Tuple
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtWidgets import QApplication, QWidget

from config_manager import get_platform_base_dir

_logger = logging.getLogger("custom_music_player.font_manager")

_LOADED_FONTS: Dict[str, str] = {}  # {path_or_zip: family_name}


def get_fonts_storage_dir() -> str:
    """Directorio persistente para fuentes personalizadas extraídas o instaladas."""
    fonts_dir = get_platform_base_dir("data", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    return fonts_dir


def load_custom_font(file_path: str) -> Optional[str]:
    """
    Carga un archivo de fuente (.ttf, .otf) o un archivo .zip que contenga fuentes.
    Registra la fuente en QFontDatabase y retorna el nombre de la familia tipográfica.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    clean_path = os.path.abspath(os.path.expanduser(file_path))

    if clean_path in _LOADED_FONTS:
        return _LOADED_FONTS[clean_path]

    target_font_path = clean_path

    # Si es un archivo ZIP, extraer los archivos .ttf o .otf
    if clean_path.lower().endswith(".zip"):
        try:
            fonts_dir = get_fonts_storage_dir()
            with zipfile.ZipFile(clean_path, "r") as z:
                font_entries = [n for n in z.namelist() if n.lower().endswith((".ttf", ".otf")) and not n.startswith("__MACOSX")]
                if not font_entries:
                    _logger.warning("No se encontraron fuentes .ttf o .otf en el archivo zip: %s", clean_path)
                    return None
                
                # Extraer la primera fuente encontrada
                extracted_name = font_entries[0]
                target_font_path = os.path.join(fonts_dir, os.path.basename(extracted_name))
                with z.open(extracted_name) as source, open(target_font_path, "wb") as dest:
                    dest.write(source.read())
        except Exception as e:
            _logger.error("Error al procesar zip de fuentes '%s': %s", clean_path, e)
            return None

    # Registrar en QFontDatabase
    try:
        font_id = QFontDatabase.addApplicationFont(target_font_path)
        if font_id == -1:
            _logger.warning("QFontDatabase no pudo cargar la fuente desde: %s", target_font_path)
            return None

        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family_name = families[0]
            _LOADED_FONTS[clean_path] = family_name
            _LOADED_FONTS[target_font_path] = family_name
            _logger.info("Fuente registrada con éxito: '%s' desde '%s'", family_name, file_path)
            return family_name
    except Exception as exc:
        _logger.error("Excepción al cargar fuente '%s': %s", file_path, exc)

    return None


def discover_available_fonts() -> Tuple[List[str], Dict[str, str]]:
    """
    Descubre fuentes del sistema y escanea directorios conocidos de fuentes personalizadas.
    Retorna una tupla con (lista de nombres de familias para combo, mapa {family: path}).
    """
    discovered_map: Dict[str, str] = {}  # {family_name: source_path}

    # 1. Escanear carpetas de fuentes personalizadas del usuario
    candidate_dirs = [
        get_fonts_storage_dir(),
        os.path.expanduser("~/Documentos/tipografia"),
        os.path.expanduser("~/Documents/tipografia"),
        os.path.expanduser("~/Documents/fonts"),
        os.path.expanduser("~/Documentos/fuentes"),
    ]

    for cdir in candidate_dirs:
        if os.path.exists(cdir) and os.path.isdir(cdir):
            try:
                for fname in sorted(os.listdir(cdir)):
                    fpath = os.path.join(cdir, fname)
                    if fname.lower().endswith((".ttf", ".otf", ".zip")) and not fname.startswith("."):
                        if "gradle" in fname.lower():
                            continue
                        fam = load_custom_font(fpath)
                        if fam:
                            discovered_map[fam] = fpath
            except Exception as e:
                _logger.debug("Error escaneando directorio de fuentes '%s': %s", cdir, e)

    # 2. Fuentes populares estándar del sistema
    popular_system_defaults = [
        "Sans Serif",
        "Cantarell",
        "DejaVu Sans",
        "Liberation Sans",
        "Ubuntu",
        "Roboto",
        "Inter",
        "Segoe UI",
        "Arial",
        "Helvetica",
        "Monospace",
        "DejaVu Sans Mono",
        "Consolas",
    ]

    system_families = set(QFontDatabase.families()) if QApplication.instance() is not None else set()

    available_list: List[str] = ["Sans Serif"]

    # Agregar fuentes personalizadas descubiertas
    for custom_fam in sorted(discovered_map.keys()):
        if custom_fam not in available_list:
            available_list.append(custom_fam)

    # Agregar fuentes estándar instaladas en el sistema
    for sys_fam in popular_system_defaults:
        if sys_fam in system_families and sys_fam not in available_list:
            available_list.append(sys_fam)

    return available_list, discovered_map


def apply_font_family_to_tree(root_widget: Optional[QWidget], font_family: str) -> None:
    """
    Aplica una familia tipográfica a un widget raíz y a todos sus hijos directos e indirectos,
    preservando los tamaños (pt/px), peso (Bold/Medium) e inclinación (Italic) de cada elemento.
    """
    if not root_widget or not font_family:
        return

    clean_fam = font_family.strip()
    if not clean_fam:
        clean_fam = "Sans Serif"

    targets = [root_widget] + root_widget.findChildren(QWidget)
    for w in targets:
        try:
            curr = w.font()
            pt_size = curr.pointSize()
            px_size = curr.pixelSize()
            weight = curr.weight()
            italic = curr.italic()

            new_font = QFont(clean_fam)
            if pt_size > 0:
                new_font.setPointSize(pt_size)
            elif px_size > 0:
                new_font.setPixelSize(px_size)
            else:
                new_font.setPointSize(10)
            new_font.setWeight(weight)
            new_font.setItalic(italic)

            w.setFont(new_font)
        except Exception:
            pass
