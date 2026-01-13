#!/bin/bash
set -e

echo "=== Building Whisper Dictate ==="

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build with PyInstaller
pyinstaller --onefile \
    --name whisper-dictate \
    --add-data "resources:resources" \
    --hidden-import faster_whisper \
    --hidden-import sounddevice \
    --hidden-import pynput \
    whisper_dictate/app.py

echo "=== Build complete! ==="
echo "Binary at: dist/whisper-dictate"

# Optional: Create .deb package
if command -v fpm &> /dev/null; then
    echo "Creating .deb package..."
    fpm -s dir -t deb \
        -n whisper-dictate \
        -v 1.0.0 \
        --description "Voice to text dictation using Whisper" \
        dist/whisper-dictate=/usr/bin/whisper-dictate \
        resources/whisper-dictate.desktop=/usr/share/applications/whisper-dictate.desktop
    echo "DEB package created!"
fi
