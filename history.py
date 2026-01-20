"""
Transcription history storage for Wisper.
Stores transcriptions in JSON format with automatic FIFO management.
"""
import json
import os
import threading
from datetime import datetime
from logger import get_logger

logger = get_logger("wisper.history")

# Data directory and file path
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
MAX_ITEMS = 100


class TranscriptionHistory:
    """
    Thread-safe transcription history with JSON persistence.
    Maintains a maximum of MAX_ITEMS entries (FIFO).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._history = []
        self._ensure_data_dir()
        self._load()
        logger.info(f"TranscriptionHistory initialized with {len(self._history)} items")

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")

    def _load(self):
        """Load history from JSON file."""
        if not os.path.exists(HISTORY_FILE):
            self._history = []
            return

        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._history = data
                else:
                    logger.warning("Invalid history file format, starting fresh")
                    self._history = []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse history file: {e}")
            self._history = []
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self._history = []

    def _save(self):
        """Save history to JSON file."""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add(self, text: str, language: str = "en") -> None:
        """
        Add a transcription to history.
        Removes oldest entries if history exceeds MAX_ITEMS.
        """
        if not text or not text.strip():
            return

        with self._lock:
            entry = {
                "text": text.strip(),
                "language": language,
                "timestamp": datetime.now().isoformat()
            }
            self._history.append(entry)

            # Enforce FIFO limit
            while len(self._history) > MAX_ITEMS:
                self._history.pop(0)

            self._save()
            logger.debug(f"Added to history: {text[:30]}...")

    def get_all(self) -> list:
        """Return all history entries (newest last)."""
        with self._lock:
            return list(self._history)

    def get_recent(self, count: int = 10) -> list:
        """Return the most recent entries (newest first)."""
        with self._lock:
            return list(reversed(self._history[-count:]))

    def clear(self) -> None:
        """Clear all history."""
        with self._lock:
            self._history = []
            self._save()
            logger.info("History cleared")

    def __len__(self) -> int:
        with self._lock:
            return len(self._history)
