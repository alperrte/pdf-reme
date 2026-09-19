from PySide6.QtCore import QSettings

COMPRESS_LEVELS = ("light", "balanced", "strong")

_KEY_STARTUP_ANIMATION = "startup/animation"
_KEY_THEME_ANIMATION = "appearance/theme_animation"
_KEY_LANGUAGE_ANIMATION = "appearance/language_animation"
_KEY_COMPRESS_LEVEL = "defaults/compress_level"
_KEY_SPLIT_KEEP_REST = "defaults/split_keep_rest"
_KEY_AUTO_UPDATE_CHECK = "updates/auto_check"


def _as_bool(value, default: bool) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ("1", "true", "yes")


def _settings() -> QSettings:
    # Tema ve dil ile aynı (uygulama düzeyi) QSettings deposu.
    return QSettings()


def startup_animation() -> bool:
    return _as_bool(_settings().value(_KEY_STARTUP_ANIMATION), True)


def set_startup_animation(enabled: bool) -> None:
    _settings().setValue(_KEY_STARTUP_ANIMATION, bool(enabled))


def theme_animation() -> bool:
    return _as_bool(_settings().value(_KEY_THEME_ANIMATION), True)


def set_theme_animation(enabled: bool) -> None:
    _settings().setValue(_KEY_THEME_ANIMATION, bool(enabled))


def language_animation() -> bool:
    return _as_bool(_settings().value(_KEY_LANGUAGE_ANIMATION), True)


def set_language_animation(enabled: bool) -> None:
    _settings().setValue(_KEY_LANGUAGE_ANIMATION, bool(enabled))


def default_compress_level() -> str:
    value = _settings().value(_KEY_COMPRESS_LEVEL)

    return value if value in COMPRESS_LEVELS else "balanced"


def set_default_compress_level(level: str) -> None:
    if level in COMPRESS_LEVELS:
        _settings().setValue(_KEY_COMPRESS_LEVEL, level)


def split_keep_rest() -> bool:
    return _as_bool(_settings().value(_KEY_SPLIT_KEEP_REST), True)


def set_split_keep_rest(enabled: bool) -> None:
    _settings().setValue(_KEY_SPLIT_KEEP_REST, bool(enabled))


def auto_update_check() -> bool:
    return _as_bool(_settings().value(_KEY_AUTO_UPDATE_CHECK), False)


def set_auto_update_check(enabled: bool) -> None:
    _settings().setValue(_KEY_AUTO_UPDATE_CHECK, bool(enabled))
