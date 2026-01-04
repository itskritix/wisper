# Wisper

A Windows speech-to-text application that uses Groq's Whisper API. Hold a hotkey to record, release to transcribe, and the text is automatically pasted.

## Features

- **Hold-to-record**: Hold `Ctrl+Win` to record, release to transcribe
- **Auto-paste**: Transcribed text is automatically copied and pasted
- **Multi-language**: Supports 11 languages (English, Hindi, Spanish, French, German, Chinese, Japanese, Korean, Portuguese, Russian, Arabic)
- **System tray**: Runs in background with tray icon for language selection
- **Visual feedback**: Overlay shows recording/transcribing status

## Requirements

- Windows 10/11
- Python 3.8+
- Groq API key (get one at https://console.groq.com)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wisper.git
   cd wisper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your API key:**
   ```bash
   cp settings.example.json settings.json
   ```
   Then edit `settings.json` and replace `YOUR_GROQ_API_KEY_HERE` with your actual Groq API key:
   ```json
   {
     "api_key": "your_actual_groq_api_key",
     "language": "en",
     "language_name": "English"
   }
   ```

## Usage

Run the application:
```bash
python main.py
```

Or use the batch file:
```bash
run.bat
```

### Controls

- **Hold `Ctrl+Win`**: Start recording
- **Release `Ctrl+Win`**: Stop recording and transcribe
- **Right-click tray icon**: Change language or quit

## Optional: Run at Startup

To run Wisper automatically at Windows startup:
```bash
add_to_startup.bat
```

## License

MIT
