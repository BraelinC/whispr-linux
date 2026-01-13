import sounddevice as sd
import numpy as np
import tempfile
import wave
import threading

class Recorder:
    def __init__(self):
        # Use DMIC (device 2) with correct settings for HP laptop
        self.device = 2  # acp DMIC
        self.sample_rate = 48000
        self.channels = 2  # DMIC requires stereo
        self.recording = False
        self.audio_data = []
        self.stream = None
        self._lock = threading.Lock()

        print(f"[DEBUG] Recorder initialized: device={self.device}, rate={self.sample_rate}, channels={self.channels}")

    def start(self):
        """Start recording from microphone"""
        with self._lock:
            self.audio_data = []
            self.recording = True

        def callback(indata, frames, time, status):
            if status:
                print(f"[DEBUG] Recording status: {status}")
            if self.recording:
                self.audio_data.append(indata.copy())

        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            callback=callback
        )
        self.stream.start()

    def stop(self) -> str:
        """Stop recording and return path to WAV file"""
        with self._lock:
            self.recording = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_data:
            print("[DEBUG] No audio data captured!")
            return None

        # Combine all audio chunks
        audio = np.concatenate(self.audio_data, axis=0)

        # Convert stereo to mono by averaging channels
        if len(audio.shape) > 1 and audio.shape[1] == 2:
            audio = np.mean(audio, axis=1)

        print(f"[DEBUG] Audio samples: {len(audio)}, duration: {len(audio)/self.sample_rate:.2f}s, sample_rate: {self.sample_rate}")

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

        # Save as 16-bit WAV (standard format for speech APIs)
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        return temp_file.name

    @property
    def is_recording(self):
        return self.recording
