import os
from functools import lru_cache

try:
    import winreg
except ImportError:
    winreg = None

from PyQt6.QtGui import QFontDatabase

SYSTEM_FONT_PREFIX = "sysfont:"
SYSTEM_FONT_DIR = r"C:\Windows\Fonts"


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


def _trim_registry_font_name(name: str) -> str:
    return name.split("(", 1)[0].strip()


@lru_cache(maxsize=1)
def build_system_font_map() -> dict[str, str]:
    font_map = {}

    if winreg is None:
        return font_map

    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

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

                if not os.path.exists(font_path):
                    continue

                if os.path.splitext(font_path)[1].lower() not in {".ttf", ".otf", ".ttc"}:
                    continue

                reg_name = _trim_registry_font_name(value_name)
                if reg_name and reg_name not in font_map:
                    font_map[reg_name] = font_path
    except OSError:
        return font_map

    lowered_map = {name.lower(): path for name, path in font_map.items()}
    for family in list_all_system_font_families():
        lowered_family = family.lower()
        if family not in font_map and lowered_family in lowered_map:
            font_map[family] = lowered_map[lowered_family]

    return dict(sorted(font_map.items(), key=lambda item: item[0].lower()))


def resolve_font_path(font_value: str) -> str:
    if not font_value:
        return font_value

    if not is_system_font_value(font_value):
        return font_value

    family = decode_system_font_value(font_value)
    font_map = build_system_font_map()

    if family in font_map:
        return font_map[family]

    lowered = {name.lower(): path for name, path in font_map.items()}
    resolved = lowered.get(family.lower())
    if resolved:
        return resolved

    raise FileNotFoundError(f"未找到系统字体对应文件: {family}")