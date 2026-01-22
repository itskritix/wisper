"""
Unified GUI Manager for Wisper.
Handles all tkinter windows in a single thread with one Tk() root.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import pyperclip
from logger import get_logger

logger = get_logger("wisper.gui")

# Supported languages
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


class GUIManager:
    """
    Single GUI manager that handles all tkinter windows.
    Runs in its own thread with a single Tk() root.
    Thread-safe: all calls go through a command queue.
    """

    def __init__(self, history=None, on_language_change=None):
        self.history = history
        self.on_language_change = on_language_change

        # Tkinter objects (created in GUI thread)
        self.root = None
        self.overlay_window = None
        self.overlay_label = None
        self.settings_window = None
        self.language_var = None
        self.history_listbox = None
        self.status_var = None

        # State
        self._current_language = "English"
        self._destroyed = False
        self._setup_done = threading.Event()
        self._hide_timer_id = None

        # Command queue for thread-safe operations
        self._cmd_queue = queue.Queue()

        # Start GUI thread
        self.gui_thread = threading.Thread(target=self._run_gui, daemon=True, name="GUIThread")
        self.gui_thread.start()

        # Wait for setup
        if not self._setup_done.wait(timeout=5):
            logger.error("GUI setup timed out")
        else:
            logger.info("GUI Manager initialized")

    def _run_gui(self):
        """Main GUI thread - creates root and runs mainloop."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # Hide root window
            self.root.title("Wisper")

            # Create overlay window
            self._create_overlay()

            # Create settings window
            self._create_settings()

            self._setup_done.set()

            # Process command queue periodically
            self._process_commands()

            # Run mainloop
            self.root.mainloop()
        except Exception as e:
            logger.error(f"GUI thread error: {e}")
            self._setup_done.set()

    def _process_commands(self):
        """Process commands from queue (runs in GUI thread)."""
        if self._destroyed:
            return

        try:
            while True:
                try:
                    cmd, args = self._cmd_queue.get_nowait()
                    cmd(*args)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Command error: {e}")
        except Exception as e:
            logger.error(f"Process commands error: {e}")

        # Schedule next check
        if not self._destroyed and self.root:
            self.root.after(50, self._process_commands)

    def _queue_cmd(self, cmd, *args):
        """Queue a command to run in GUI thread."""
        if not self._destroyed:
            self._cmd_queue.put((cmd, args))

    # ==================== OVERLAY ====================

    def _create_overlay(self):
        """Create overlay window (called in GUI thread)."""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Wisper Status")
        self.overlay_window.overrideredirect(True)
        self.overlay_window.attributes('-topmost', True)

        self.overlay_label = tk.Label(
            self.overlay_window,
            text="",
            font=("DejaVu Sans", 14, "bold"),
            fg="white",
            bg="#333333",
            padx=20,
            pady=10
        )
        self.overlay_label.pack()

        self._position_overlay()
        self.overlay_window.withdraw()

    def _position_overlay(self):
        """Position overlay at bottom center of screen."""
        try:
            self.overlay_window.update_idletasks()
            screen_width = self.overlay_window.winfo_screenwidth()
            screen_height = self.overlay_window.winfo_screenheight()
            window_width = self.overlay_window.winfo_width()
            x = (screen_width - window_width) // 2
            y = screen_height - 120
            self.overlay_window.geometry(f"+{x}+{y}")
        except Exception as e:
            logger.error(f"Position overlay error: {e}")

    def _show_overlay(self, text, color):
        """Show overlay with text and color (GUI thread)."""
        if self._destroyed or not self.overlay_window:
            return
        try:
            if self._hide_timer_id:
                self.root.after_cancel(self._hide_timer_id)
                self._hide_timer_id = None

            self.overlay_label.config(text=text, fg=color)
            self.overlay_window.deiconify()
            self._position_overlay()
        except Exception as e:
            logger.error(f"Show overlay error: {e}")

    def _hide_overlay(self):
        """Hide overlay (GUI thread)."""
        if self._destroyed or not self.overlay_window:
            return
        try:
            self.overlay_window.withdraw()
        except Exception as e:
            logger.error(f"Hide overlay error: {e}")

    def _show_overlay_timed(self, text, color, duration):
        """Show overlay then hide after duration (GUI thread)."""
        if self._destroyed:
            return
        self._show_overlay(text, color)
        self._hide_timer_id = self.root.after(duration, self._hide_overlay)

    # Public overlay methods (thread-safe)

    def overlay_recording(self):
        """Show recording overlay."""
        logger.debug("Showing recording overlay")
        self._queue_cmd(self._show_overlay, "Recording...", "#FF4444")

    def overlay_transcribing(self):
        """Show transcribing overlay."""
        logger.debug("Showing transcribing overlay")
        self._queue_cmd(self._show_overlay, "Transcribing...", "#FFAA00")

    def overlay_success(self):
        """Show success overlay."""
        logger.debug("Showing success overlay")
        self._queue_cmd(self._show_overlay_timed, "Done!", "#44FF44", 1500)

    def overlay_error(self, msg="Error"):
        """Show error overlay."""
        logger.debug(f"Showing error overlay: {msg}")
        self._queue_cmd(self._show_overlay_timed, f"{msg}", "#FF4444", 2000)

    def overlay_hide(self):
        """Hide overlay."""
        self._queue_cmd(self._hide_overlay)

    # ==================== SETTINGS ====================

    def _create_settings(self):
        """Create settings window (called in GUI thread)."""
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Wisper Settings")
        self.settings_window.geometry("500x400")
        self.settings_window.minsize(400, 300)
        self.settings_window.protocol("WM_DELETE_WINDOW", self._on_settings_close)

        # Main frame
        main_frame = ttk.Frame(self.settings_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Language frame
        lang_frame = ttk.LabelFrame(main_frame, text="Language", padding="5")
        lang_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(lang_frame, text="Transcription Language:").pack(side=tk.LEFT, padx=(0, 10))

        self.language_var = tk.StringVar(value=self._current_language)
        language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.language_var,
            values=list(LANGUAGES.keys()),
            state="readonly",
            width=20
        )
        language_combo.pack(side=tk.LEFT)
        language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)

        # History frame
        history_frame = ttk.LabelFrame(main_frame, text="Transcription History", padding="5")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        list_frame = ttk.Frame(history_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("DejaVu Sans", 10),
            selectmode=tk.SINGLE
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
        self.history_listbox.bind("<Double-1>", self._on_history_double_click)

        hint_label = ttk.Label(
            history_frame,
            text="Double-click an item to copy to clipboard",
            font=("DejaVu Sans", 9),
            foreground="gray"
        )
        hint_label.pack(anchor=tk.W, pady=(5, 0))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        refresh_btn = ttk.Button(button_frame, text="Refresh History", command=self._refresh_history)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = ttk.Button(button_frame, text="Clear History", command=self._clear_history)
        clear_btn.pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Start hidden
        self.settings_window.withdraw()

    def _on_settings_close(self):
        """Hide settings on close."""
        if self.settings_window:
            self.settings_window.withdraw()

    def _on_language_selected(self, event=None):
        """Handle language change."""
        name = self.language_var.get()
        code = LANGUAGES.get(name, "en")
        self._current_language = name
        logger.info(f"Language selected: {name} ({code})")

        if self.on_language_change:
            try:
                self.on_language_change(name, code)
            except Exception as e:
                logger.error(f"Language callback error: {e}")

        self.status_var.set(f"Language changed to {name}")

    def _on_history_double_click(self, event=None):
        """Copy history item to clipboard."""
        selection = self.history_listbox.curselection()
        if not selection or not self.history:
            return

        try:
            index = selection[0]
            all_history = self.history.get_all()
            reversed_index = len(all_history) - 1 - index
            if 0 <= reversed_index < len(all_history):
                text = all_history[reversed_index]["text"]
                pyperclip.copy(text)
                self.status_var.set("Copied to clipboard!")
                logger.debug(f"Copied: {text[:30]}...")
        except Exception as e:
            logger.error(f"Copy error: {e}")

    def _refresh_history(self):
        """Refresh history list."""
        if not self.history_listbox or not self.history:
            return

        try:
            self.history_listbox.delete(0, tk.END)
            all_history = self.history.get_all()
            for entry in reversed(all_history):
                text = entry.get("text", "")
                display = text[:80] + "..." if len(text) > 80 else text
                display = display.replace("\n", " ")
                self.history_listbox.insert(tk.END, display)
            self.status_var.set(f"{len(all_history)} items in history")
        except Exception as e:
            logger.error(f"Refresh error: {e}")

    def _clear_history(self):
        """Clear history after confirmation."""
        if messagebox.askyesno("Clear History", "Clear all transcription history?"):
            try:
                self.history.clear()
                self._refresh_history()
                self.status_var.set("History cleared")
            except Exception as e:
                logger.error(f"Clear error: {e}")

    def _show_settings(self):
        """Show settings window (GUI thread)."""
        if self._destroyed or not self.settings_window:
            return
        try:
            self._refresh_history()
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
        except Exception as e:
            logger.error(f"Show settings error: {e}")

    def _set_language_var(self, name):
        """Set language dropdown (GUI thread)."""
        if self.language_var:
            self.language_var.set(name)

    # Public settings methods (thread-safe)

    def show_settings(self):
        """Show settings window."""
        logger.info("Opening settings window")
        self._queue_cmd(self._show_settings)

    def set_language(self, name):
        """Set language dropdown value."""
        self._current_language = name
        self._queue_cmd(self._set_language_var, name)

    # ==================== CLEANUP ====================

    def destroy(self):
        """Destroy all GUI resources."""
        logger.info("Destroying GUI Manager")
        self._destroyed = True

        if self.root:
            try:
                self.root.after(0, self._do_destroy)
            except Exception as e:
                logger.error(f"Destroy schedule error: {e}")

    def _do_destroy(self):
        """Actually destroy (GUI thread)."""
        try:
            if self.settings_window:
                self.settings_window.destroy()
            if self.overlay_window:
                self.overlay_window.destroy()
            if self.root:
                self.root.destroy()
        except Exception as e:
            logger.error(f"Destroy error: {e}")
