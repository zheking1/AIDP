import json
import os
import re
from functools import lru_cache

_TRANSLATIONS = {}
_FALLBACK = {}


def load_translations():
    base = os.path.join(os.path.dirname(__file__))
    for lang in ("en", "zh"):
        path = os.path.join(base, f"{lang}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                _TRANSLATIONS[lang] = json.load(f)
    # English is fallback (keys are English)
    _FALLBACK.update(_TRANSLATIONS.get("en", {}))


def get_translator(lang: str = "en"):
    lang = lang if lang in _TRANSLATIONS else "en"
    table = _TRANSLATIONS.get(lang, {})

    def _(key: str) -> str:
        return table.get(key, _FALLBACK.get(key, key))

    return _


load_translations()
