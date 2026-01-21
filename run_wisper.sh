#!/bin/bash
# Wisper - Speech to Text Application Launcher (Linux)
# Hold Ctrl+Super to record, release to transcribe.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for required system dependencies
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "Warning: $1 is not installed. $2"
    fi
}

check_dependency "xdotool" "Auto-paste feature will not work. Install with: sudo apt install xdotool"
check_dependency "paplay" "Audio feedback will not work. Install pulseaudio-utils."

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Try to activate venv if it exists in the script directory
    if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
        source "$SCRIPT_DIR/venv/bin/activate"
    elif [ -f "$SCRIPT_DIR/../venv/bin/activate" ]; then
        source "$SCRIPT_DIR/../venv/bin/activate"
    fi
fi

# Run the application
cd "$SCRIPT_DIR"
python3 main.py "$@"
