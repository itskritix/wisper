import os
import httpx
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from groq import Groq
from logger import get_logger

logger = get_logger("wisper.transcriber")

try:
    from config import GROQ_API_KEY as CONFIG_API_KEY
except ImportError:
    CONFIG_API_KEY = None

# Timeout settings (in seconds)
API_TIMEOUT = 30.0


class Transcriber:
    def __init__(self, model="whisper-large-v3-turbo"):
        api_key = CONFIG_API_KEY or os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY not found")
            raise ValueError(
                "GROQ_API_KEY not found. Set it in config.py or as environment variable. "
                "Get your API key from https://console.groq.com"
            )

        try:
            # Create client with timeout
            self.client = Groq(
                api_key=api_key,
                timeout=httpx.Timeout(API_TIMEOUT, connect=10.0)
            )
            self.model = model
            self._executor = ThreadPoolExecutor(max_workers=1)
            logger.info(f"Transcriber initialized with model: {model}, timeout: {API_TIMEOUT}s")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise

    def _do_transcribe(self, audio_path, language):
        """Internal method that does the actual API call"""
        with open(audio_path, "rb") as audio_file:
            return self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=language,
                response_format="text",
                temperature=0.0
            )

    def transcribe(self, audio_path, language="en"):
        logger.info(f"Transcribing {audio_path} (language: {language})")

        try:
            # Use executor with timeout for robust timeout handling
            future = self._executor.submit(self._do_transcribe, audio_path, language)

            try:
                transcription = future.result(timeout=API_TIMEOUT)
                logger.info(f"Transcription successful: {len(transcription)} chars")
                return transcription
            except FuturesTimeoutError:
                logger.error(f"Transcription timed out after {API_TIMEOUT}s (futures timeout)")
                future.cancel()
                raise TimeoutError(f"API timeout after {API_TIMEOUT}s")

        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            raise
        except TimeoutError:
            raise  # Re-raise our timeout
        except httpx.TimeoutException as e:
            logger.error(f"Transcription timed out (httpx): {e}")
            raise TimeoutError(f"API timeout after {API_TIMEOUT}s")
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise ConnectionError("Failed to connect to Groq API")
        except Exception as e:
            logger.error(f"Transcription failed: {type(e).__name__}: {e}")
            raise
