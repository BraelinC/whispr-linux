import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "whisper-dictate"
CONFIG_FILE = CONFIG_DIR / "config.json"

AVAILABLE_MODELS = {
    # Moonshine models (sherpa-onnx) - very fast, good accuracy
    "moonshine-tiny":   {"ram": "~210MB",  "speed": "fastest", "accuracy": "~87%", "engine": "sherpa"},
    "moonshine-base":   {"ram": "~430MB",  "speed": "very fast", "accuracy": "~92%", "engine": "sherpa"},
    # Whisper models (faster-whisper)
    "distil-small.en":  {"ram": "~300MB",  "speed": "fast",    "accuracy": "87%", "engine": "whisper"},
    "distil-medium.en": {"ram": "~500MB",  "speed": "fast",    "accuracy": "88%", "engine": "whisper"},
    "small.en":         {"ram": "~500MB",  "speed": "moderate", "accuracy": "92%", "engine": "whisper"},
}

DEFAULT_CONFIG = {
    "model": "distil-medium.en",
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
