"""
State machine for Wisper application.
Handles state transitions with debouncing and cooldown to prevent race conditions.
"""
import time
import threading
from enum import Enum, auto
from logger import get_logger

logger = get_logger("wisper.state_machine")


class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class StateMachine:
    """
    Thread-safe state machine with debouncing and cooldown.

    State transitions:
        IDLE --> RECORDING (on start_recording)
        RECORDING --> TRANSCRIBING (on stop_recording)
        TRANSCRIBING --> IDLE (on finish_transcription)
    """

    DEBOUNCE_MS = 100  # Minimum time between state changes
    COOLDOWN_MS = 300  # Cooldown after transcription before allowing new recording

    def __init__(self):
        self._state = AppState.IDLE
        self._lock = threading.Lock()
        self._last_transition_time = 0.0
        self._cooldown_until = 0.0
        logger.info("StateMachine initialized in IDLE state")

    @property
    def state(self) -> AppState:
        with self._lock:
            return self._state

    @property
    def is_idle(self) -> bool:
        return self.state == AppState.IDLE

    @property
    def is_recording(self) -> bool:
        return self.state == AppState.RECORDING

    @property
    def is_transcribing(self) -> bool:
        return self.state == AppState.TRANSCRIBING

    def _can_transition(self) -> bool:
        """Check if enough time has passed since last transition (debounce)."""
        now = time.time() * 1000  # Convert to milliseconds
        return (now - self._last_transition_time) >= self.DEBOUNCE_MS

    def _in_cooldown(self) -> bool:
        """Check if we're still in cooldown period after transcription."""
        now = time.time() * 1000
        return now < self._cooldown_until

    def start_recording(self) -> bool:
        """
        Attempt to transition from IDLE to RECORDING.
        Returns True if transition successful, False otherwise.
        """
        with self._lock:
            if self._state != AppState.IDLE:
                logger.debug(f"Cannot start recording: state is {self._state.name}")
                return False

            if not self._can_transition():
                logger.debug("Cannot start recording: debounce active")
                return False

            if self._in_cooldown():
                logger.debug("Cannot start recording: in cooldown period")
                return False

            self._state = AppState.RECORDING
            self._last_transition_time = time.time() * 1000
            logger.info("State transition: IDLE -> RECORDING")
            return True

    def stop_recording(self) -> bool:
        """
        Attempt to transition from RECORDING to TRANSCRIBING.
        Returns True if transition successful, False otherwise.
        """
        with self._lock:
            if self._state != AppState.RECORDING:
                logger.debug(f"Cannot stop recording: state is {self._state.name}")
                return False

            if not self._can_transition():
                logger.debug("Cannot stop recording: debounce active")
                return False

            self._state = AppState.TRANSCRIBING
            self._last_transition_time = time.time() * 1000
            logger.info("State transition: RECORDING -> TRANSCRIBING")
            return True

    def finish_transcription(self) -> bool:
        """
        Transition from TRANSCRIBING to IDLE with cooldown.
        Returns True if transition successful, False otherwise.
        """
        with self._lock:
            if self._state != AppState.TRANSCRIBING:
                logger.debug(f"Cannot finish transcription: state is {self._state.name}")
                return False

            self._state = AppState.IDLE
            self._last_transition_time = time.time() * 1000
            self._cooldown_until = self._last_transition_time + self.COOLDOWN_MS
            logger.info("State transition: TRANSCRIBING -> IDLE (cooldown started)")
            return True

    def reset_to_idle(self) -> None:
        """
        Force reset to IDLE state. Use for error recovery only.
        """
        with self._lock:
            old_state = self._state
            self._state = AppState.IDLE
            self._last_transition_time = time.time() * 1000
            self._cooldown_until = 0.0
            logger.warning(f"State RESET: {old_state.name} -> IDLE (forced)")
