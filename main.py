"""
Wisper - Speech to Text Application (Linux Version)
Version 1.0

Hold Ctrl+Super (Windows key) to record, release to transcribe.
"""
import os
import sys
import time
import threading
import atexit
import subprocess
import pyperclip
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item
from pynput import keyboard

from logger import setup_logger, setup_global_exception_handler, get_logger
from recorder import AudioRecorder
from transcriber import Transcriber
from state_machine import StateMachine
from history import TranscriptionHistory
from gui_manager import GUIManager

# Initialize logging first
setup_logger()
setup_global_exception_handler()
logger = get_logger("wisper.main")


HOTKEY_DISPLAY = "Ctrl+Super"

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

# Global app instance for cleanup
_app_instance = None


def cleanup_on_exit():
    """Cleanup handler for atexit."""
    global _app_instance
    if _app_instance:
        logger.info("Running atexit cleanup")
        try:
            _app_instance.emergency_cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


class WisperApp:
    def __init__(self):
        global _app_instance
        _app_instance = self

        logger.info("Initializing WisperApp")
        self.recorder = None
        self.transcriber = None
        self.is_running = True
        self.recording_thread = None
        self.language = "en"
        self.language_name = "English"
        self.tray_icon = None
        self.gui = None
        self.state_machine = StateMachine()
        self.history = TranscriptionHistory()
        self._cleanup_done = False

        # Hotkey state tracking
        self._ctrl_pressed = False
        self._super_pressed = False
        self._hotkey_active = False
        self._key_lock = threading.Lock()

        # Register cleanup handlers
        atexit.register(cleanup_on_exit)

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
            self.gui = GUIManager(
                history=self.history,
                on_language_change=self._on_language_change_from_gui
            )
        except Exception as e:
            logger.error(f"Failed to initialize GUI: {e}")
            print(f"Warning: GUI failed to initialize, continuing without GUI")
            self.gui = None

        logger.info("Initialization complete")
        print("Groq API connected successfully")
        return True

    def _on_language_change_from_gui(self, name, code):
        """Callback when language is changed from Settings GUI."""
        self.language = code
        self.language_name = name
        logger.info(f"Language changed from GUI to: {name} ({code})")
        print(f"\nLanguage changed to: {name}")
        print(f"Ready. Hold {HOTKEY_DISPLAY} to record [{name}]...")

    def beep_start(self):
        """Play start recording beep using paplay."""
        try:
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/message.oga"],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            logger.debug(f"Beep start failed (audio feedback not available): {e}")

    def beep_stop(self):
        """Play stop recording beep using paplay."""
        try:
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            logger.debug(f"Beep stop failed (audio feedback not available): {e}")

    def beep_success(self):
        """Play success beep using paplay."""
        try:
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            logger.debug(f"Beep success failed (audio feedback not available): {e}")

    def record_audio_loop(self):
        """Recording loop - runs in separate thread."""
        logger.debug("Recording loop started")
        try:
            while self.recorder and not self.recorder._stop_event.is_set():
                if not self.recorder.read_chunk():
                    break
                time.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in recording loop: {e}")
        logger.debug("Recording loop ended")

    def on_hotkey_press(self):
        # Attempt state transition first (atomic, with debounce/cooldown)
        if not self.state_machine.start_recording():
            return

        logger.info("Hotkey pressed - starting recording")

        # Beep in background thread
        threading.Thread(target=self.beep_start, daemon=True).start()

        # Update GUI
        if self.gui:
            self.gui.overlay_recording()

        print(f"\nRecording [{self.language_name}]... (release {HOTKEY_DISPLAY} to stop)")

        # Update tray icon
        try:
            if self.tray_icon:
                self.tray_icon.icon = self.create_icon_image(recording=True)
        except Exception as e:
            logger.error(f"Tray icon update failed: {e}")

        # Start recording
        try:
            if self.recorder:
                success = self.recorder.start_recording()
                if success:
                    self.recording_thread = threading.Thread(
                        target=self.record_audio_loop,
                        name="RecordingThread",
                        daemon=True
                    )
                    self.recording_thread.start()
                else:
                    logger.error("Failed to start recording")
                    self.state_machine.reset_to_idle()
                    if self.gui:
                        self.gui.overlay_error("Mic error")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.state_machine.reset_to_idle()
            if self.gui:
                self.gui.overlay_error("Error")

    def _do_transcription(self, audio_path):
        """Run transcription in background thread."""
        try:
            text = self.transcriber.transcribe(audio_path, language=self.language)
            if text:
                logger.info(f"Transcription result: {text[:50]}...")
                print(f"\n{'='*50}")
                print(text)
                print(f"{'='*50}")

                # Save to history
                try:
                    self.history.add(text, self.language)
                except Exception as e:
                    logger.error(f"Failed to save to history: {e}")

                try:
                    pyperclip.copy(text)
                    time.sleep(0.1)
                    # Use xdotool for paste on Linux
                    subprocess.run(
                        ["xdotool", "key", "ctrl+v"],
                        capture_output=True,
                        timeout=2
                    )
                except Exception as e:
                    logger.error(f"Paste failed: {e}")

                self.beep_success()
                if self.gui:
                    self.gui.overlay_success()
                print("[Pasted automatically]")
            else:
                logger.warning("No speech detected")
                print("No speech detected")
                if self.gui:
                    self.gui.overlay_error("No speech")
        except TimeoutError as e:
            logger.error(f"Transcription timeout: {e}")
            print("Transcription timeout - please try again")
            if self.gui:
                self.gui.overlay_error("Timeout")
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            print("Connection error - check internet")
            if self.gui:
                self.gui.overlay_error("No internet")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            print(f"Transcription error: {e}")
            if self.gui:
                self.gui.overlay_error("Error")
        finally:
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                    logger.debug(f"Cleaned up temp file: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")

            # Transition state (with cooldown)
            self.state_machine.finish_transcription()
            logger.debug("Transcription complete, state returned to IDLE")
            print(f"\nReady. Hold {HOTKEY_DISPLAY} to record [{self.language_name}]...")

    def on_hotkey_release(self):
        # Attempt state transition first (atomic, with debounce)
        if not self.state_machine.stop_recording():
            return

        logger.info("Hotkey released - stopping recording")

        # Beep in background thread
        threading.Thread(target=self.beep_stop, daemon=True).start()

        audio_path = None
        duration = 0
        try:
            result = self.recorder.stop_recording()
            if result:
                audio_path, duration = result
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")

        # Update tray icon
        try:
            if self.tray_icon:
                self.tray_icon.icon = self.create_icon_image(recording=False)
        except Exception as e:
            logger.error(f"Tray icon update failed: {e}")

        # Wait for recording thread to finish
        if self.recording_thread:
            try:
                self.recording_thread.join(timeout=1.0)
                if self.recording_thread.is_alive():
                    logger.warning("Recording thread still running, continuing anyway")
            except Exception as e:
                logger.error(f"Error joining recording thread: {e}")
            self.recording_thread = None

        if not audio_path:
            logger.warning("No audio recorded")
            print("No audio recorded")
            if self.gui:
                self.gui.overlay_hide()
            self.state_machine.reset_to_idle()
            return

        # Skip very short recordings
        MIN_DURATION = 0.3
        if duration < MIN_DURATION:
            logger.info(f"Recording too short ({duration:.2f}s), skipping")
            print(f"Recording too short ({duration:.1f}s), skipping...")
            if self.gui:
                self.gui.overlay_hide()
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                logger.error(f"Failed to cleanup: {e}")
            self.state_machine.reset_to_idle()
            print(f"Ready. Hold {HOTKEY_DISPLAY} to record [{self.language_name}]...")
            return

        # Show transcribing overlay
        if self.gui:
            self.gui.overlay_transcribing()

        print("Transcribing...")

        # Run transcription in background thread
        threading.Thread(
            target=self._do_transcription,
            args=(audio_path,),
            name="TranscriptionThread",
            daemon=True
        ).start()

    def set_language(self, name, code):
        def callback(icon, item):
            self.language = code
            self.language_name = name
            logger.info(f"Language changed to: {name} ({code})")
            print(f"\nLanguage changed to: {name}")
            print(f"Ready. Hold {HOTKEY_DISPLAY} to record [{name}]...")
            if self.gui:
                self.gui.set_language(name)
        return callback

    def check_language(self, name):
        def callback(item):
            return self.language_name == name
        return callback

    def open_settings(self, icon, item):
        """Open the settings window."""
        logger.info("Opening settings window")
        if self.gui:
            self.gui.show_settings()

    def quit_app(self, icon, item):
        logger.info("Quit requested from tray menu")
        self.is_running = False
        icon.stop()

    def _on_key_press(self, key):
        """Handle key press events from pynput."""
        with self._key_lock:
            try:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                    self._ctrl_pressed = True
                elif key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r or key == keyboard.Key.cmd:
                    self._super_pressed = True

                # Check if hotkey combo is now active
                if self._ctrl_pressed and self._super_pressed and not self._hotkey_active:
                    self._hotkey_active = True
                    # Run in separate thread to not block the listener
                    threading.Thread(target=self.on_hotkey_press, daemon=True).start()
            except Exception as e:
                logger.error(f"Error in key press handler: {e}")

    def _on_key_release(self, key):
        """Handle key release events from pynput."""
        with self._key_lock:
            try:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                    self._ctrl_pressed = False
                elif key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r or key == keyboard.Key.cmd:
                    self._super_pressed = False

                # Check if hotkey combo was released
                if self._hotkey_active and (not self._ctrl_pressed or not self._super_pressed):
                    self._hotkey_active = False
                    # Run in separate thread to not block the listener
                    threading.Thread(target=self.on_hotkey_release, daemon=True).start()
            except Exception as e:
                logger.error(f"Error in key release handler: {e}")

    def create_tray_menu(self):
        language_items = [
            item(name, self.set_language(name, code), checked=self.check_language(name))
            for name, code in LANGUAGES.items()
        ]

        menu = pystray.Menu(
            item(f"Wisper - Hold {HOTKEY_DISPLAY}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Settings", self.open_settings),
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

    def emergency_cleanup(self):
        """Emergency cleanup for crashes."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        logger.info("Emergency cleanup...")
        try:
            if self.recorder:
                self.recorder.cleanup()
        except Exception as e:
            logger.error(f"Recorder cleanup error: {e}")

    def run(self):
        logger.info("Starting Wisper application")

        if not self.initialize():
            logger.error("Initialization failed, exiting")
            return

        self.run_tray()

        print(f"\nReady. Hold {HOTKEY_DISPLAY} to record [{self.language_name}]...")
        print("Running in system tray. Right-click tray icon to change language or quit.\n")

        # Start keyboard listener using pynput
        keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        keyboard_listener.start()

        try:
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            print("\nExiting...")
        except Exception as e:
            logger.critical(f"Critical error in main loop: {e}")
        finally:
            keyboard_listener.stop()
            self.shutdown()

    def shutdown(self):
        """Clean shutdown."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        logger.info("Shutting down...")

        try:
            if self.gui:
                self.gui.destroy()
        except Exception as e:
            logger.error(f"Error destroying GUI: {e}")

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
    logger.info("Wisper V1.0 (Linux) starting")
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
