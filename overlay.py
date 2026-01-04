import tkinter as tk
import threading
from logger import get_logger

logger = get_logger("wisper.overlay")


class StatusOverlay:
    def __init__(self):
        self.root = None
        self.label = None
        self.is_visible = False
        self.hide_timer = None
        self._setup_done = threading.Event()
        self._destroyed = False

        try:
            # Start tkinter in separate thread
            self.tk_thread = threading.Thread(target=self._run_tk, daemon=True)
            self.tk_thread.start()
            # Wait for setup with timeout
            if not self._setup_done.wait(timeout=5):
                logger.error("Overlay setup timed out")
            else:
                logger.info("Overlay initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize overlay: {e}")

    def _run_tk(self):
        try:
            self.root = tk.Tk()
            self.root.title("Wisper Status")

            # Remove window decorations
            self.root.overrideredirect(True)

            # Always on top
            self.root.attributes('-topmost', True)

            # Make window click-through (Windows)
            self.root.attributes('-transparentcolor', 'black')

            # Create label
            self.label = tk.Label(
                self.root,
                text="",
                font=("Segoe UI", 14, "bold"),
                fg="white",
                bg="#333333",
                padx=20,
                pady=10
            )
            self.label.pack()

            # Position at bottom center
            self._position_window()

            # Start hidden
            self.root.withdraw()

            self._setup_done.set()
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Overlay thread error: {e}")
            self._setup_done.set()

    def _position_window(self):
        try:
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            window_width = self.root.winfo_width()

            x = (screen_width - window_width) // 2
            y = screen_height - 120  # Above taskbar

            self.root.geometry(f"+{x}+{y}")
        except Exception as e:
            logger.error(f"Error positioning window: {e}")

    def show(self, text, color="#FF4444"):
        if self._destroyed or not self.root:
            return
        try:
            self.root.after(0, lambda: self._show(text, color))
        except Exception as e:
            logger.error(f"Error scheduling show: {e}")

    def _show(self, text, color):
        try:
            if self._destroyed:
                return
            if self.hide_timer:
                self.root.after_cancel(self.hide_timer)
                self.hide_timer = None

            self.label.config(text=text, fg=color)
            self.root.deiconify()
            self._position_window()
            self.is_visible = True
        except Exception as e:
            logger.error(f"Error showing overlay: {e}")

    def hide(self):
        if self._destroyed or not self.root:
            return
        try:
            self.root.after(0, self._hide)
        except Exception as e:
            logger.error(f"Error scheduling hide: {e}")

    def _hide(self):
        try:
            if self._destroyed:
                return
            self.root.withdraw()
            self.is_visible = False
        except Exception as e:
            logger.error(f"Error hiding overlay: {e}")

    def show_success(self, text="Done!", duration=1000):
        if self._destroyed or not self.root:
            return
        try:
            self.root.after(0, lambda: self._show_success(text, duration))
        except Exception as e:
            logger.error(f"Error scheduling show_success: {e}")

    def _show_success(self, text, duration):
        try:
            if self._destroyed:
                return
            self._show(text, "#44FF44")
            self.hide_timer = self.root.after(duration, self._hide)
        except Exception as e:
            logger.error(f"Error in show_success: {e}")

    def recording(self):
        logger.debug("Showing recording overlay")
        self.show("🎙 Recording...", "#FF4444")

    def transcribing(self):
        logger.debug("Showing transcribing overlay")
        self.show("⏳ Transcribing...", "#FFAA00")

    def success(self):
        logger.debug("Showing success overlay")
        self.show_success("✓ Done!", 1500)

    def error(self, msg="Error"):
        logger.debug(f"Showing error overlay: {msg}")
        self.show_success(f"✗ {msg}", 2000)

    def destroy(self):
        logger.info("Destroying overlay")
        self._destroyed = True
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception as e:
                logger.error(f"Error destroying overlay: {e}")
