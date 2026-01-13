from setuptools import setup, find_packages

setup(
    name="whisper-dictate",
    version="1.0.0",
    description="Voice to text dictation using Whisper",
    author="braelin",
    packages=find_packages(),
    install_requires=[
        "faster-whisper>=1.0.0",
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "pynput>=1.7.6",
        "PyQt6>=6.5.0",
    ],
    entry_points={
        "console_scripts": [
            "whisper-dictate=whisper_dictate:main",
        ],
    },
    python_requires=">=3.9",
)
