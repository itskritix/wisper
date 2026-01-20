"""
Audio recorder for Wisper.
Thread-safe recording with proper synchronization.
"""
import pyaudio
import wave
import tempfile
import threading
from logger import get_logger

logger = get_logger("wisper.recorder")


class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        self.audio = None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self._lock = threading.Lock()
        self._stream_lock = threading.Lock()  # Separate lock for stream operations
        self._stop_event = threading.Event()  # Signal to stop recording loop

        try:
            self.audio = pyaudio.PyAudio()
            logger.info("PyAudio initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            raise

    def start_recording(self):
        with self._lock:
            if self.is_recording:
                logger.warning("Already recording, ignoring start request")
                return False

            try:
                self.frames = []
                self._stop_event.clear()

                with self._stream_lock:
                    self.stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=self.sample_rate,
                        input=True,
                        frames_per_buffer=self.chunk_size
                    )

                self.is_recording = True
                logger.info("Recording started")
                return True
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                self.is_recording = False
                self.stream = None
                return False

    def stop_recording(self):
        with self._lock:
            if not self.is_recording:
                logger.warning("Not recording, ignoring stop request")
                return None

            # Signal the recording loop to stop
            self._stop_event.set()
            self.is_recording = False
            logger.info("Stopping recording...")

            # Close stream with stream lock
            with self._stream_lock:
                try:
                    if self.stream:
                        self.stream.stop_stream()
                        self.stream.close()
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
                finally:
                    self.stream = None

            if not self.frames:
                logger.warning("No audio frames captured")
                return None

            try:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav",
                    delete=False
                )
                temp_path = temp_file.name
                temp_file.close()

                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.frames))

                duration = (len(self.frames) * self.chunk_size) / self.sample_rate
                logger.info(f"Audio saved to {temp_path} ({len(self.frames)} frames, {duration:.1f}s)")
                return temp_path, duration
            except Exception as e:
                logger.error(f"Failed to save audio file: {e}")
                return None

    def read_chunk(self):
        """Read a chunk of audio data. Thread-safe."""
        # Check stop event first (fast path)
        if self._stop_event.is_set():
            return False

        # Try to read with stream lock
        with self._stream_lock:
            if not self.is_recording or not self.stream:
                return False

            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
                return True
            except OSError as e:
                # Stream was closed - this is expected during stop
                if "Stream is stopped" in str(e) or "Stream not open" in str(e):
                    return False
                logger.error(f"Error reading audio chunk: {e}")
                return False
            except Exception as e:
                logger.error(f"Error reading audio chunk: {e}")
                return False

    def cleanup(self):
        """Clean up all audio resources."""
        logger.info("Cleaning up audio resources...")

        # Stop any ongoing recording
        self._stop_event.set()
        self.is_recording = False

        with self._lock:
            with self._stream_lock:
                try:
                    if self.stream:
                        self.stream.stop_stream()
                        self.stream.close()
                        self.stream = None
                except Exception as e:
                    logger.error(f"Error closing stream during cleanup: {e}")

            try:
                if self.audio:
                    self.audio.terminate()
                    self.audio = None
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")

        logger.info("Audio cleanup complete")
