from faster_whisper import WhisperModel
from huggingface_hub import scan_cache_dir
from pathlib import Path
import os
import wave
import numpy as np
from .config import Config, AVAILABLE_MODELS

# Moonshine model paths
MODELS_DIR = Path(__file__).parent.parent / "models"
MOONSHINE_MODELS = {
    "moonshine-tiny": "sherpa-onnx-moonshine-tiny-en-int8",
    "moonshine-base": "sherpa-onnx-moonshine-base-en-int8",
}

class Transcriber:
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._current_model_name = None
        self.on_status = None  # Callback for status updates
        self._sherpa_recognizer = None  # For Moonshine models

    def _get_engine(self, model_name: str) -> str:
        """Get the engine type for a model"""
        if model_name in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[model_name].get("engine", "whisper")
        return "whisper"

    def is_model_downloaded(self, model_name: str) -> bool:
        """Check if model is already downloaded"""
        # Moonshine models - check local directory
        if model_name in MOONSHINE_MODELS:
            model_dir = MODELS_DIR / MOONSHINE_MODELS[model_name]
            return model_dir.exists()

        # Whisper models - check HuggingFace cache
        try:
            cache_info = scan_cache_dir()
            for repo in cache_info.repos:
                if model_name in repo.repo_id:
                    return True
                if f"faster-whisper-{model_name}" in repo.repo_id:
                    return True
        except Exception:
            pass
        return False

    def _update_status(self, msg: str):
        """Send status update"""
        print(f"[STATUS] {msg}")
        if self.on_status:
            self.on_status(msg)

    def load_model(self, model_name: str = None):
        """Load or switch model"""
        model_name = model_name or self.config.model

        if self._current_model_name == model_name:
            return  # Already loaded

        engine = self._get_engine(model_name)

        if engine == "sherpa":
            self._load_moonshine(model_name)
        else:
            self._load_whisper(model_name)

    def _load_moonshine(self, model_name: str):
        """Load a Moonshine model via sherpa-onnx"""
        import sherpa_onnx

        if model_name not in MOONSHINE_MODELS:
            raise ValueError(f"Unknown Moonshine model: {model_name}")

        model_dir = MODELS_DIR / MOONSHINE_MODELS[model_name]

        if not model_dir.exists():
            self._update_status(f"Model {model_name} not found. Please download it first.")
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        self._update_status(f"Loading {model_name}...")

        self._sherpa_recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
            preprocessor=str(model_dir / "preprocess.onnx"),
            encoder=str(model_dir / "encode.int8.onnx"),
            uncached_decoder=str(model_dir / "uncached_decode.int8.onnx"),
            cached_decoder=str(model_dir / "cached_decode.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=4,
        )

        self.model = None  # Clear whisper model
        self._current_model_name = model_name
        self._update_status(f"Ready ({model_name})")

    def _load_whisper(self, model_name: str):
        """Load a Whisper model via faster-whisper"""
        if not self.is_model_downloaded(model_name):
            self._update_status(f"Downloading {model_name}...")
        else:
            self._update_status(f"Loading {model_name}...")

        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type=self.config.get("compute_type")
        )
        self._sherpa_recognizer = None  # Clear sherpa model
        self._current_model_name = model_name
        self._update_status(f"Ready ({model_name})")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        model_name = self._current_model_name or self.config.model

        if not self.model and not self._sherpa_recognizer:
            self.load_model()

        engine = self._get_engine(model_name)

        if engine == "sherpa":
            return self._transcribe_moonshine(audio_path)
        else:
            return self._transcribe_whisper(audio_path)

    def _transcribe_moonshine(self, audio_path: str) -> str:
        """Transcribe using Moonshine via sherpa-onnx"""
        model_name = self._current_model_name
        self._update_status(f"Transcribing with {model_name}...")

        # Read audio file
        with wave.open(audio_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            num_frames = wf.getnframes()
            audio_bytes = wf.readframes(num_frames)

        # Convert to float32
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # Transcribe
        stream = self._sherpa_recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio)
        self._sherpa_recognizer.decode_stream(stream)

        text = stream.result.text.strip()
        print(f"[DEBUG] Moonshine result: '{text}'")
        return text

    def _transcribe_whisper(self, audio_path: str) -> str:
        """Transcribe using faster-whisper"""
        model_name = self._current_model_name
        self._update_status(f"Transcribing with {model_name}...")

        segments, _ = self.model.transcribe(audio_path)
        text = "".join(seg.text for seg in segments).strip()
        return text

    def switch_model(self, model_name: str):
        """Switch to a different model"""
        self.config.model = model_name
        self.model = None  # Force reload
        self._sherpa_recognizer = None
        self._current_model_name = None

    @property
    def current_model(self) -> str:
        return self._current_model_name
