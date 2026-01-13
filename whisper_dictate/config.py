import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "whisper-dictate"
CONFIG_FILE = CONFIG_DIR / "config.json"

AVAILABLE_MODELS = {
    "moonshine-base":   {"ram": "~430MB",  "speed": "very fast", "accuracy": "~92%", "engine": "sherpa"},
}

DEFAULT_CONFIG = {
    "model": "moonshine-base",
    "compute_type": "int8",
    "hotkey": "f9",
    "auto_paste": True,
    "paste_command": "ctrl+shift+v",  # For terminal
}

class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                self._data = {**DEFAULT_CONFIG, **json.load(f)}
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    @property
    def model(self):
        return self._data["model"]

    @model.setter
    def model(self, value):
        self.set("model", value)
