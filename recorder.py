import pyaudio
import wave
import tempfile
import os
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

            self.is_recording = False
            logger.info("Stopping recording...")

            try:
                if self.stream:
                    self.stream.stop_stream()
                    self.stream.close()
                    self.stream = None
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
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
        if not self.is_recording or not self.stream:
            return False

        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            self.frames.append(data)
            return True
        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return False

    def cleanup(self):
        logger.info("Cleaning up audio resources...")
        with self._lock:
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
