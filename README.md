# Wisper (Linux)

A Linux speech-to-text application that uses Groq's Whisper API. Hold a hotkey to record, release to transcribe, and the text is automatically pasted.

## Features

- **Hold-to-record**: Hold `Ctrl+Super` to record, release to transcribe
- **Auto-paste**: Transcribed text is automatically copied and pasted
- **Multi-language**: Supports 11 languages (English, Hindi, Spanish, French, German, Chinese, Japanese, Korean, Portuguese, Russian, Arabic)
- **System tray**: Runs in background with tray icon for language selection
- **Visual feedback**: Overlay shows recording/transcribing status

## Requirements

- Linux (tested on Ubuntu 22.04+)
- Python 3.8+
- PulseAudio (for audio recording and feedback sounds)
- xdotool (for auto-paste functionality)
- Groq API key (get one at https://console.groq.com)

## Installation

1. Install system dependencies:
   ```bash
   sudo apt install python3-tk python3-dev portaudio19-dev xdotool pulseaudio-utils
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wisper.git
   cd wisper
   git checkout linux
   ```

3. Create virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure your API key:**
   ```bash
   cp config.example.py config.py
   ```
   Then edit `config.py` and replace `YOUR_GROQ_API_KEY_HERE` with your actual Groq API key:
   ```python
   GROQ_API_KEY = "your_actual_groq_api_key"
   ```

## Usage

Run the application:
```bash
./run_wisper.sh
```

Or directly:
```bash
python3 main.py
```

### Controls

- **Hold `Ctrl+Super`**: Start recording
- **Release `Ctrl+Super`**: Stop recording and transcribe
- **Right-click tray icon**: Change language or quit

## Optional: Run at Startup

To run Wisper automatically at login, create a desktop entry:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/wisper.desktop << EOF
[Desktop Entry]
Type=Application
Name=Wisper
Exec=/path/to/wisper/run_wisper.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

Replace `/path/to/wisper` with the actual path to your wisper installation.

## Troubleshooting

### No audio recording
- Ensure PulseAudio is running: `pulseaudio --check`
- Check microphone permissions and default input device

### Auto-paste not working
- Install xdotool: `sudo apt install xdotool`
- Ensure you're running on X11 (Wayland may have limitations)

### System tray not showing
- Install AppIndicator support for your desktop environment
- On GNOME, install the AppIndicator extension

## License

MIT
