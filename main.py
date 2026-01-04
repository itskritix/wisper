import os
import time
import threading
import keyboard
import pyperclip
import pyautogui
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item

from logger import setup_logger, setup_global_exception_handler, get_logger
from recorder import AudioRecorder
from transcriber import Transcriber
from overlay import StatusOverlay

# Initialize logging first
setup_logger()
setup_global_exception_handler()
logger = get_logger("wisper.main")


HOTKEY = "ctrl+win"

LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Portuguese": "pt",
    "Russian": "ru",
    "Arabic": "ar",
}


class WisperApp:
    def __init__(self):
        logger.info("Initializing WisperApp")
        self.recorder = None
        self.transcriber = None
        self.is_running = True
        self.recording_thread = None
        self.transcription_thread = None
        self.language = "en"
        self.language_name = "English"
        self.tray_icon = None
        self.overlay = None
        self._recording_lock = threading.Lock()
        self._is_busy = False  # Busy during transcription

    def create_icon_image(self, recording=False):
        color = "red" if recording else "green"
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill=color)
        return image

    def initialize(self):
        logger.info("Starting initialization...")
        print("Initializing Wisper...")

        try:
            self.recorder = AudioRecorder()
        except Exception as e:
            logger.error(f"Failed to initialize recorder: {e}")
            print(f"Error: Failed to initialize audio recorder: {e}")
            return False

        try:
            self.transcriber = Transcriber()
        except Exception as e:
            logger.error(f"Failed to initialize transcriber: {e}")
            print(f"Error: {e}")
            return False

        try:
            self.overlay = StatusOverlay()
        except Exception as e:
            logger.error(f"Failed to initialize overlay: {e}")
            # Overlay is optional, continue without it
            self.overlay = None

        logger.info("Initialization complete")
        print("Groq API connected successfully")
        return True

    def beep_start(self):
        try:
            import winsound
            winsound.Beep(800, 150)
        except Exception as e:
            logger.warning(f"Beep start failed: {e}")

    def beep_stop(self):
        try:
            import winsound
            winsound.Beep(400, 150)
        except Exception as e:
            logger.warning(f"Beep stop failed: {e}")

    def beep_success(self):
        try:
            import winsound
            winsound.Beep(600, 100)
            winsound.Beep(800, 100)
        except Exception as e:
            logger.warning(f"Beep success failed: {e}")

    def record_audio_loop(self):
        logger.debug("Recording loop started")
        try:
            while self.recorder and self.recorder.is_recording:
                self.recorder.read_chunk()
                time.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in recording loop: {e}")
        logger.debug("Recording loop ended")

    def on_hotkey_press(self):
        with self._recording_lock:
            # Check if busy (transcribing)
            if self._is_busy:
                logger.debug("Busy transcribing, ignoring press")
                return

            if self.recorder and self.recorder.is_recording:
                logger.debug("Already recording, ignoring press")
                return

            logger.info("Hotkey pressed - starting recording")

            try:
                self.beep_start()
            except Exception as e:
                logger.error(f"Beep failed: {e}")

            try:
                if self.overlay:
                    self.overlay.recording()
            except Exception as e:
                logger.error(f"Overlay update failed: {e}")

            print(f"\nRecording [{self.language_name}]... (release Ctrl+Win to stop)")

            try:
                if self.tray_icon:
                    self.tray_icon.icon = self.create_icon_image(recording=True)
            except Exception as e:
                logger.error(f"Tray icon update failed: {e}")

            try:
                if self.recorder:
                    success = self.recorder.start_recording()
                    if success:
                        self.recording_thread = threading.Thread(
                            target=self.record_audio_loop,
                            name="RecordingThread"
                        )
                        self.recording_thread.start()
                    else:
                        logger.error("Failed to start recording")
                        if self.overlay:
                            self.overlay.error("Mic error")
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                if self.overlay:
                    self.overlay.error("Error")

    def _do_transcription(self, audio_path):
        """Run transcription in background thread"""
        try:
            text = self.transcriber.transcribe(audio_path, language=self.language)
            if text:
                logger.info(f"Transcription result: {text[:50]}...")
                print(f"\n{'='*50}")
                print(text)
                print(f"{'='*50}")

                try:
                    pyperclip.copy(text)
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')
                except Exception as e:
                    logger.error(f"Paste failed: {e}")

                self.beep_success()
                if self.overlay:
                    self.overlay.success()
                print("[Pasted automatically]")
            else:
                logger.warning("No speech detected")
                print("No speech detected")
                if self.overlay:
                    self.overlay.error("No speech")
        except TimeoutError as e:
            logger.error(f"Transcription timeout: {e}")
            print("Transcription timeout - please try again")
            if self.overlay:
                self.overlay.error("Timeout")
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            print("Connection error - check internet")
            if self.overlay:
                self.overlay.error("No internet")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            print(f"Transcription error: {e}")
            if self.overlay:
                self.overlay.error("Error")
        finally:
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                    logger.debug(f"Cleaned up temp file: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")

            self._is_busy = False
            logger.debug("Transcription complete, busy=False")
            print(f"\nReady. Hold {HOTKEY.upper()} to record [{self.language_name}]...")

    def on_hotkey_release(self):
        with self._recording_lock:
            if not self.recorder or not self.recorder.is_recording:
                logger.debug("Not recording, ignoring release")
                return

            logger.info("Hotkey released - stopping recording")

            try:
                self.beep_stop()
            except Exception as e:
                logger.error(f"Beep failed: {e}")

            audio_path = None
            duration = 0
            try:
                result = self.recorder.stop_recording()
                if result:
                    audio_path, duration = result
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")

            try:
                if self.tray_icon:
                    self.tray_icon.icon = self.create_icon_image(recording=False)
            except Exception as e:
                logger.error(f"Tray icon update failed: {e}")

            # Wait for recording thread to finish
            if self.recording_thread:
                try:
                    self.recording_thread.join(timeout=2.0)
                    if self.recording_thread.is_alive():
                        logger.warning("Recording thread did not finish in time, continuing anyway")
                    else:
                        logger.debug("Recording thread finished")
                except Exception as e:
                    logger.error(f"Error joining recording thread: {e}")
                self.recording_thread = None

            if not audio_path:
                logger.warning("No audio recorded")
                print("No audio recorded")
                if self.overlay:
                    self.overlay.hide()
                return

            # Skip very short recordings (likely accidental)
            MIN_DURATION = 0.3  # seconds
            if duration < MIN_DURATION:
                logger.info(f"Recording too short ({duration:.2f}s < {MIN_DURATION}s), skipping")
                print(f"Recording too short ({duration:.1f}s), skipping...")
                try:
                    if self.overlay:
                        self.overlay.hide()
                except Exception as e:
                    logger.error(f"Error hiding overlay: {e}")
                try:
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                        logger.debug(f"Cleaned up short recording: {audio_path}")
                except Exception as e:
                    logger.error(f"Failed to cleanup short recording: {e}")
                print(f"Ready. Hold {HOTKEY.upper()} to record [{self.language_name}]...")
                return

            # Set busy flag before starting transcription
            self._is_busy = True
            logger.debug("Starting transcription, busy=True")

            try:
                if self.overlay:
                    self.overlay.transcribing()
            except Exception as e:
                logger.error(f"Overlay update failed: {e}")

            print("Transcribing...")

            # Run transcription in background thread
            self.transcription_thread = threading.Thread(
                target=self._do_transcription,
                args=(audio_path,),
                name="TranscriptionThread",
                daemon=True
            )
            self.transcription_thread.start()

    def set_language(self, name, code):
        def callback(icon, item):
            self.language = code
            self.language_name = name
            logger.info(f"Language changed to: {name} ({code})")
            print(f"\nLanguage changed to: {name}")
            print(f"Ready. Hold {HOTKEY.upper()} to record [{name}]...")
        return callback

    def check_language(self, name):
        def callback(item):
            return self.language_name == name
        return callback

    def quit_app(self, icon, item):
        logger.info("Quit requested from tray menu")
        self.is_running = False
        icon.stop()

    def check_hotkey_held(self):
        try:
            return (keyboard.is_pressed("ctrl") and
                    keyboard.is_pressed("windows"))
        except Exception as e:
            logger.error(f"Error checking hotkey: {e}")
            return False

    def create_tray_menu(self):
        language_items = [
            item(name, self.set_language(name, code), checked=self.check_language(name))
            for name, code in LANGUAGES.items()
        ]

        menu = pystray.Menu(
            item(f"Wisper - Hold {HOTKEY.upper()}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Language", pystray.Menu(*language_items)),
            pystray.Menu.SEPARATOR,
            item("Quit", self.quit_app)
        )
        return menu

    def run_tray(self):
        try:
            self.tray_icon = pystray.Icon(
                "Wisper",
                self.create_icon_image(),
                "Wisper - Speech to Text",
                self.create_tray_menu()
            )
            self.tray_icon.run_detached()
            logger.info("Tray icon started")
        except Exception as e:
            logger.error(f"Failed to start tray icon: {e}")

    def run(self):
        logger.info("Starting Wisper application")

        if not self.initialize():
            logger.error("Initialization failed, exiting")
            return

        self.run_tray()

        print(f"\nReady. Hold {HOTKEY.upper()} to record [{self.language_name}]...")
        print("Running in system tray. Right-click tray icon to change language or quit.\n")

        was_pressed = False

        try:
            while self.is_running:
                try:
                    is_pressed = self.check_hotkey_held()

                    if is_pressed and not was_pressed:
                        self.on_hotkey_press()
                    elif not is_pressed and was_pressed:
                        self.on_hotkey_release()

                    was_pressed = is_pressed
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            print("\nExiting...")
        except Exception as e:
            logger.critical(f"Critical error in main loop: {e}")
        finally:
            logger.info("Shutting down...")
            try:
                if self.overlay:
                    self.overlay.destroy()
            except Exception as e:
                logger.error(f"Error destroying overlay: {e}")

            try:
                if self.tray_icon:
                    self.tray_icon.stop()
            except Exception as e:
                logger.error(f"Error stopping tray icon: {e}")

            try:
                if self.recorder:
                    self.recorder.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up recorder: {e}")

            logger.info("Shutdown complete")


def main():
    logger.info("="*50)
    logger.info("Wisper starting")
    logger.info("="*50)

    try:
        app = WisperApp()
        app.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Wisper exited")


if __name__ == "__main__":
    main()
