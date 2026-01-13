import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu,
                             QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
                             QPushButton, QDialog, QCheckBox, QLineEdit)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from pynput import keyboard

from .config import Config, AVAILABLE_MODELS
from .transcriber import Transcriber
from .recorder import Recorder


# Map pynput keys to readable names
KEY_NAMES = {
    keyboard.Key.f1: "F1", keyboard.Key.f2: "F2", keyboard.Key.f3: "F3",
    keyboard.Key.f4: "F4", keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
    keyboard.Key.f7: "F7", keyboard.Key.f8: "F8", keyboard.Key.f9: "F9",
    keyboard.Key.f10: "F10", keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
    keyboard.Key.media_previous: "Media Prev",
    keyboard.Key.media_next: "Media Next",
    keyboard.Key.media_play_pause: "Media Play",
    keyboard.Key.scroll_lock: "Scroll Lock",
    keyboard.Key.pause: "Pause",
    keyboard.Key.insert: "Insert",
}


def get_key_name(key):
    """Get readable name for a key"""
    if key in KEY_NAMES:
        return KEY_NAMES[key]
    if hasattr(key, 'char') and key.char:
        return key.char.upper()
    return str(key)


def key_matches_config(key, config_hotkey: str) -> bool:
    """Check if a pressed key matches the configured hotkey"""
    config_hotkey = config_hotkey.lower()

    # Check function keys
    if config_hotkey.startswith("f") and config_hotkey[1:].isdigit():
        fkey = getattr(keyboard.Key, config_hotkey, None)
        if fkey and key == fkey:
            return True

    # Check special keys
    special_map = {
        "alt": keyboard.Key.alt,
        "alt_l": keyboard.Key.alt_l,
        "alt_r": keyboard.Key.alt_r,
        "ctrl": keyboard.Key.ctrl,
        "ctrl_l": keyboard.Key.ctrl_l,
        "ctrl_r": keyboard.Key.ctrl_r,
        "shift": keyboard.Key.shift,
        "shift_l": keyboard.Key.shift_l,
        "shift_r": keyboard.Key.shift_r,
        "media_prev": keyboard.Key.media_previous,
        "media_previous": keyboard.Key.media_previous,
        "media_next": keyboard.Key.media_next,
        "media_play": keyboard.Key.media_play_pause,
        "scroll_lock": keyboard.Key.scroll_lock,
        "pause": keyboard.Key.pause,
        "insert": keyboard.Key.insert,
    }
    if config_hotkey in special_map and key == special_map[config_hotkey]:
        return True

    # Alt matches both alt_l and alt_r
    if config_hotkey == "alt" and key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
        return True

    # HP laptops map F9 to media_previous
    if config_hotkey == "f9" and key == keyboard.Key.media_previous:
        return True

    # Check character keys
    if hasattr(key, 'char') and key.char and key.char.lower() == config_hotkey:
        return True

    return False


class HotkeySignal(QObject):
    """Signal bridge for hotkey from pynput thread to Qt main thread"""
    pressed = pyqtSignal()
    released = pyqtSignal()


class StatusSignal(QObject):
    """Signal bridge for status updates from worker threads"""
    updated = pyqtSignal(str)


class TranscribeWorker(QThread):
    """Background thread for transcription"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, transcriber, audio_path):
        super().__init__()
        self.transcriber = transcriber
        self.audio_path = audio_path

    def run(self):
        try:
            text = self.transcriber.transcribe(self.audio_path)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class HotkeyCapture(QDialog):
    """Dialog to capture a new hotkey"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Hotkey")
        self.setMinimumWidth(300)
        self.captured_key = None
        self.captured_key_name = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Press any key to set as hotkey..."))

        self.key_label = QLabel("Waiting...")
        self.key_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px;")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.key_label)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Set")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Start listening for keys
        self.listener = keyboard.Listener(on_press=self._on_key)
        self.listener.start()

    def _on_key(self, key):
        """Called when a key is pressed"""
        self.captured_key = key
        self.captured_key_name = get_key_name(key)

        # Update UI (need to do this thread-safe)
        self.key_label.setText(self.captured_key_name)
        self.ok_btn.setEnabled(True)

    def get_hotkey_config(self) -> str:
        """Get the config string for the captured key"""
        if self.captured_key is None:
            return None

        # Convert to config format
        if self.captured_key in KEY_NAMES:
            # It's a special key
            key_str = str(self.captured_key).replace("Key.", "")
            return key_str
        elif hasattr(self.captured_key, 'char') and self.captured_key.char:
            return self.captured_key.char.lower()
        return None

    def closeEvent(self, event):
        self.listener.stop()
        super().closeEvent(event)

    def reject(self):
        self.listener.stop()
        super().reject()

    def accept(self):
        self.listener.stop()
        super().accept()


class SettingsDialog(QDialog):
    """Settings window"""
    def __init__(self, config, on_model_change, on_hotkey_change):
        super().__init__()
        self.config = config
        self.on_model_change = on_model_change
        self.on_hotkey_change = on_hotkey_change
        self.setWindowTitle("Whisper Dictate Settings")
        self.setMinimumWidth(350)

        layout = QVBoxLayout()

        # Model selector
        layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        for model, info in AVAILABLE_MODELS.items():
            self.model_combo.addItem(
                f"{model} ({info['ram']}, {info['accuracy']})",
                model
            )

        # Set current model
        current = self.config.model
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == current:
                self.model_combo.setCurrentIndex(i)
                break

        self.model_combo.currentIndexChanged.connect(self._on_model_change)
        layout.addWidget(self.model_combo)

        # Auto-paste checkbox
        self.auto_paste = QCheckBox("Auto-paste after transcription")
        self.auto_paste.setChecked(self.config.get("auto_paste"))
        self.auto_paste.stateChanged.connect(
            lambda s: self.config.set("auto_paste", s == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.auto_paste)

        # Hotkey configuration
        layout.addWidget(QLabel("\nHotkey (hold to record):"))
        hotkey_layout = QHBoxLayout()

        self.hotkey_display = QLineEdit()
        self.hotkey_display.setReadOnly(True)
        self.hotkey_display.setText(self.config.get("hotkey").upper())
        hotkey_layout.addWidget(self.hotkey_display)

        self.set_hotkey_btn = QPushButton("Change...")
        self.set_hotkey_btn.clicked.connect(self._change_hotkey)
        hotkey_layout.addWidget(self.set_hotkey_btn)

        layout.addLayout(hotkey_layout)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _on_model_change(self, index):
        model = self.model_combo.itemData(index)
        self.on_model_change(model)

    def _change_hotkey(self):
        dialog = HotkeyCapture(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_hotkey = dialog.get_hotkey_config()
            if new_hotkey:
                self.config.set("hotkey", new_hotkey)
                self.hotkey_display.setText(dialog.captured_key_name)
                self.on_hotkey_change()


class WhisperDictateApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = Config()
        self.transcriber = Transcriber(self.config)
        self.recorder = Recorder()
        self.worker = None
        self.listener = None

        # Hotkey signal bridge (thread-safe)
        self.hotkey_signal = HotkeySignal()
        self.hotkey_signal.pressed.connect(self._on_hotkey_pressed)
        self.hotkey_signal.released.connect(self._on_hotkey_released)

        # Status signal bridge (for updates from worker threads)
        self.status_signal = StatusSignal()
        self.status_signal.updated.connect(self._on_status_update)

        self._setup_tray()
        self._setup_hotkey()

        # Load model in background
        self._load_model_async()

    def _setup_tray(self):
        """Setup system tray icon and menu"""
        self.tray = QSystemTrayIcon()

        # Try to load icon, fallback to theme icon
        icon_path = Path(__file__).parent.parent / "resources" / "icon.png"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            self.tray.setIcon(QIcon.fromTheme("audio-input-microphone"))

        # Create menu
        menu = QMenu()

        hotkey = self.config.get("hotkey").upper()
        self.status_action = QAction(f"Ready (hold {hotkey} to record)")
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Model submenu
        model_menu = menu.addMenu("Switch Model")
        self.model_actions = []
        for model in AVAILABLE_MODELS:
            action = QAction(model, model_menu)
            action.setCheckable(True)
            action.setChecked(model == self.config.model)
            action.triggered.connect(lambda checked, m=model: self._switch_model(m))
            model_menu.addAction(action)
            self.model_actions.append(action)
        self.model_menu = model_menu

        set_hotkey_action = QAction("Set Hotkey...")
        set_hotkey_action.triggered.connect(self._change_hotkey)
        menu.addAction(set_hotkey_action)

        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Whisper Dictate")
        self.tray.show()

    def _setup_hotkey(self):
        """Setup global hotkey with push-to-talk behavior"""
        # Stop existing listener if any
        if self.listener:
            self.listener.stop()

        hotkey_config = self.config.get("hotkey")

        def on_press(key):
            if key_matches_config(key, hotkey_config):
                if not self.recorder.is_recording:
                    print(f"[DEBUG] Hotkey pressed: {key}")
                    self.hotkey_signal.pressed.emit()

        def on_release(key):
            if key_matches_config(key, hotkey_config):
                if self.recorder.is_recording:
                    print(f"[DEBUG] Hotkey released: {key}")
                    self.hotkey_signal.released.emit()

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()
        print(f"[DEBUG] Hotkey listener started (hold {hotkey_config} to record)")

    def _on_status_update(self, msg: str):
        """Handle status updates from transcriber"""
        self.status_action.setText(msg)
        print(f"[UI STATUS] {msg}")

    def _update_status_text(self):
        """Update status text with current hotkey"""
        hotkey = self.config.get("hotkey").upper()
        model = self.transcriber.current_model or self.config.model
        self.status_action.setText(f"Ready - {model} (hold {hotkey})")

    def _load_model_async(self):
        """Load model in background"""
        model_name = self.config.model
        self.status_action.setText(f"Loading {model_name}...")

        class LoadWorker(QThread):
            finished = pyqtSignal()
            status = pyqtSignal(str)

            def __init__(self, transcriber):
                super().__init__()
                self.transcriber = transcriber

            def run(self):
                # Connect status callback
                self.transcriber.on_status = lambda msg: self.status.emit(msg)
                self.transcriber.load_model()
                self.finished.emit()

        self.load_worker = LoadWorker(self.transcriber)
        self.load_worker.status.connect(self._on_status_update)
        self.load_worker.finished.connect(self._update_status_text)
        self.load_worker.start()

    def _on_hotkey_pressed(self):
        """Start recording when hotkey is pressed"""
        print("[DEBUG] Starting recording (hotkey pressed)...")
        self.recorder.start()
        hotkey = self.config.get("hotkey").upper()
        self.status_action.setText(f"Recording... (release {hotkey})")
        self.tray.showMessage("Recording", "Speak now...",
                             QSystemTrayIcon.MessageIcon.Information, 1000)

    def _on_hotkey_released(self):
        """Stop recording when hotkey is released"""
        print("[DEBUG] Stopping recording (hotkey released)...")
        audio_path = self.recorder.stop()
        print(f"[DEBUG] Audio saved to: {audio_path}")
        if not audio_path:
            self._update_status_text()
            return

        model = self.transcriber.current_model or self.config.model
        self.status_action.setText(f"Transcribing with {model}...")

        self.worker = TranscribeWorker(self.transcriber, audio_path)
        self.worker.finished.connect(self._on_transcription_done)
        self.worker.error.connect(self._on_transcription_error)
        self.worker.start()

    def _on_transcription_done(self, text):
        print(f"[DEBUG] Transcription done: '{text}'")
        self._update_status_text()

        if not text:
            self.tray.showMessage("No speech", "No speech detected",
                                 QSystemTrayIcon.MessageIcon.Warning, 2000)
            return

        # Copy to clipboard
        clipboard = self.app.clipboard()
        clipboard.setText(text)

        # Auto-paste if enabled
        if self.config.get("auto_paste"):
            import time

            # Also copy to clipboard as backup
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode(),
                check=True
            )

            # Small delay before typing
            time.sleep(0.15)

            # Type out the text (works everywhere including web terminals)
            print(f"[DEBUG] Typing out: {text[:50]}...")
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text])

        self.tray.showMessage("Transcribed", text[:100] + "..." if len(text) > 100 else text,
                             QSystemTrayIcon.MessageIcon.Information, 3000)

    def _on_transcription_error(self, error):
        self._update_status_text()
        self.tray.showMessage("Error", error,
                             QSystemTrayIcon.MessageIcon.Critical, 3000)

    def _switch_model(self, model_name):
        print(f"[DEBUG] Switching to model: {model_name}")
        self.transcriber.switch_model(model_name)

        # Update menu checkmarks
        for action in self.model_actions:
            action.setChecked(action.text() == model_name)

        # Show notification
        self.tray.showMessage("Switching Model", f"Loading {model_name}...",
                             QSystemTrayIcon.MessageIcon.Information, 2000)

        self._load_model_async()

    def _change_hotkey(self):
        """Open hotkey capture dialog from tray menu"""
        dialog = HotkeyCapture()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_hotkey = dialog.get_hotkey_config()
            if new_hotkey:
                self.config.set("hotkey", new_hotkey)
                self._setup_hotkey()
                self._update_status_text()
                self.tray.showMessage("Hotkey Changed", f"New hotkey: {dialog.captured_key_name}",
                                     QSystemTrayIcon.MessageIcon.Information, 2000)

    def _show_settings(self):
        dialog = SettingsDialog(self.config, self._switch_model, self._setup_hotkey)
        dialog.exec()
        # Update status text in case hotkey changed
        self._update_status_text()

    def _quit(self):
        if self.listener:
            self.listener.stop()
        self.app.quit()

    def run(self):
        return self.app.exec()


def main():
    app = WhisperDictateApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
