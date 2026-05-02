import os
import unicodedata
from functools import lru_cache

try:
    import winreg
except ImportError:
    winreg = None

from fontTools.ttLib import TTCollection, TTFont
from PyQt6.QtGui import QFontDatabase

SYSTEM_FONT_PREFIX = "sysfont:"
SYSTEM_FONT_DIR = r"C:\Windows\Fonts"
SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
FONT_NAME_IDS = {1, 4, 6, 16, 17, 21}


def is_system_font_value(value: str) -> bool:
    return isinstance(value, str) and value.startswith(SYSTEM_FONT_PREFIX)


def encode_system_font_value(font_name: str) -> str:
    return f"{SYSTEM_FONT_PREFIX}{font_name.strip()}"


def decode_system_font_value(value: str) -> str:
    if not is_system_font_value(value):
        return value
    return value[len(SYSTEM_FONT_PREFIX):].strip()


def list_all_system_font_families() -> list[str]:
    try:
        families = list(QFontDatabase.families())
    except Exception:
        families = []
    return sorted(dict.fromkeys(family.strip() for family in families if family and family.strip()), key=str.lower)


def _normalize_font_key(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKC", str(name)).strip().casefold()
    normalized = " ".join(normalized.split())
    return normalized


def _trim_registry_font_name(name: str) -> str:
    return name.split("(", 1)[0].strip()


def _split_registry_font_names(name: str) -> list[str]:
    trimmed = _trim_registry_font_name(name)
    if not trimmed:
        return []

    aliases = []
    for part in trimmed.split("&"):
        alias = part.strip(" ,;　")
        if alias:
            aliases.append(alias)
    if trimmed and trimmed not in aliases:
        aliases.append(trimmed)
    return aliases


def _extract_names_from_name_table(font) -> set[str]:
    names = set()
    name_table = font.get("name")
    if not name_table:
        return names

    for record in getattr(name_table, "names", []):
        if getattr(record, "nameID", None) not in FONT_NAME_IDS:
            continue
        try:
            text = record.toUnicode().strip()
        except Exception:
            continue
        if text:
            names.add(text)
    return names


def _extract_font_entries_from_file(font_path: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    ext = os.path.splitext(font_path)[1].lower()

    try:
        if ext == ".ttc":
            collection = TTCollection(font_path)
            try:
                for index, font in enumerate(collection.fonts):
                    names = _extract_names_from_name_table(font)
                    if names:
                        entries.append({"path": font_path, "font_number": index, "names": names})
            finally:
                collection.close()
        else:
            font = TTFont(font_path)
            try:
                names = _extract_names_from_name_table(font)
                if names:
                    entries.append({"path": font_path, "font_number": 0, "names": names})
            finally:
                font.close()
    except Exception:
        return entries

    return entries


def _register_font_alias(font_map: dict[str, dict[str, object]], normalized_map: dict[str, dict[str, object]], alias: str, font_spec: dict[str, object]) -> None:
    alias = (alias or "").strip()
    font_path = str((font_spec or {}).get("path") or "").strip()
    if not alias or not font_path:
        return

    spec = {
        "path": font_path,
        "font_number": int((font_spec or {}).get("font_number", 0) or 0),
        "family": alias,
    }

    if alias not in font_map:
        font_map[alias] = spec

    normalized = _normalize_font_key(alias)
    if normalized and normalized not in normalized_map:
        normalized_map[normalized] = spec


@lru_cache(maxsize=1)
def build_system_font_map() -> dict[str, dict[str, object]]:
    font_map: dict[str, dict[str, object]] = {}
    normalized_map: dict[str, dict[str, object]] = {}

    if winreg is None:
        return font_map

    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    scanned_files: dict[str, list[dict[str, object]]] = {}

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as fonts_key:
            index = 0
            while True:
                try:
                    value_name, value_data, _ = winreg.EnumValue(fonts_key, index)
                    index += 1
                except OSError:
                    break

                if not isinstance(value_data, str):
                    continue

                font_path = value_data
                if not os.path.isabs(font_path):
                    font_path = os.path.join(SYSTEM_FONT_DIR, value_data)
                font_path = os.path.normpath(font_path)

                if not os.path.exists(font_path):
                    continue

                if os.path.splitext(font_path)[1].lower() not in SUPPORTED_FONT_EXTENSIONS:
                    continue

                registry_spec = {"path": font_path, "font_number": 0}
                for reg_name in _split_registry_font_names(value_name):
                    _register_font_alias(font_map, normalized_map, reg_name, registry_spec)

                if font_path not in scanned_files:
                    scanned_files[font_path] = _extract_font_entries_from_file(font_path)

                for entry in scanned_files[font_path]:
                    for internal_name in entry.get("names", set()):
                        _register_font_alias(font_map, normalized_map, internal_name, entry)
    except OSError:
        return font_map

    for family in list_all_system_font_families():
        normalized = _normalize_font_key(family)
        resolved = normalized_map.get(normalized)
        if resolved:
            _register_font_alias(font_map, normalized_map, family, resolved)

    return dict(sorted({k: v for k, v in font_map.items() if k and v}.items(), key=lambda item: item[0].lower()))


def resolve_font_spec(font_value: str) -> dict[str, object]:
    if not font_value:
        return {"path": font_value, "font_number": 0, "family": ""}

    if not is_system_font_value(font_value):
        return {"path": font_value, "font_number": 0, "family": ""}

    family = decode_system_font_value(font_value)
    font_map = build_system_font_map()

    if family in font_map:
        resolved = dict(font_map[family])
        resolved["family"] = family
        return resolved

    normalized_family = _normalize_font_key(family)
    for name, spec in font_map.items():
        if _normalize_font_key(name) == normalized_family:
            resolved = dict(spec)
            resolved["family"] = family
            return resolved

    raise FileNotFoundError(f"未找到系统字体对应文件: {family}")


def resolve_font_path(font_value: str) -> str:
    return str(resolve_font_spec(font_value).get("path") or "")