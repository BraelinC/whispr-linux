# Whispr Linux

A lightweight Linux voice-to-text dictation app with push-to-talk and auto-paste.

## Features

- **Push-to-talk**: Hold hotkey to record, release to transcribe
- **Auto-paste**: Automatically pastes transcribed text at cursor
- **Multiple models**: Moonshine (fast) and Whisper models
- **System tray**: Runs quietly in the background
- **Configurable hotkey**: Set any key as your record trigger

## Models

| Model | RAM | Speed | Accuracy |
|-------|-----|-------|----------|
| moonshine-tiny | ~210MB | fastest | ~87% |
| moonshine-base | ~430MB | very fast | ~92% |
| distil-small.en | ~300MB | fast | 87% |
| distil-medium.en | ~500MB | fast | 88% |
| small.en | ~500MB | moderate | 92% |

## Installation

```bash
# Install system dependencies
sudo apt install python3-pip python3-venv xdotool xclip portaudio19-dev \
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0

# Clone and setup
git clone https://github.com/BraelinC/whispr-linux.git
cd whispr-linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Download Moonshine models
mkdir -p models && cd models
curl -SL -O https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-moonshine-base-en-int8.tar.bz2
tar xvf sherpa-onnx-moonshine-base-en-int8.tar.bz2
rm sherpa-onnx-moonshine-base-en-int8.tar.bz2
cd ..

# Run
whisper-dictate
```

## Usage

1. Run `whisper-dictate` - appears in system tray
2. Hold your hotkey (default: Alt) and speak
3. Release to transcribe and auto-paste

## Configuration

Config file: `~/.config/whisper-dictate/config.json`

```json
{
  "model": "moonshine-base",
  "hotkey": "alt",
  "auto_paste": true,
  "paste_command": "ctrl+shift+v"
}
```

Right-click tray icon to:
- Switch models
- Set hotkey
- Open settings

## License

MIT
