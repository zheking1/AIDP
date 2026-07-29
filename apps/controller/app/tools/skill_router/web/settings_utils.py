import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")

def get_all_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"allow_registration": True}

def set_setting(key, value):
    settings = get_all_settings()
    settings[key] = value
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    return settings