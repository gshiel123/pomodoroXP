from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time


class Session(str, Enum):
    WORK = "work"
    REST = "rest"


@dataclass(frozen=True)
class Preset:
    work_minutes: int
    rest_minutes: int

    @property
    def label(self) -> str:
        return f"{self.work_minutes} / {self.rest_minutes} minutes"


class PomodoroTimer:
    def __init__(
        self,
        presets: tuple[Preset, ...] | None = None,
        preset_index: int = 0,
        clock=time.monotonic,
    ) -> None:
        self.presets = presets or (
            Preset(25, 5),
            Preset(50, 10),
        )
        if not self.presets:
            raise ValueError("At least one preset is required")

        self._clock = clock
        self.preset_index = max(0, min(preset_index, len(self.presets) - 1))
        self.session = Session.WORK
        self.remaining_seconds = 0.0
        self._end_at: float | None = None
        self.reset()

    @property
    def preset(self) -> Preset:
        return self.presets[self.preset_index]

    @property
    def running(self) -> bool:
        return self._end_at is not None

    def reset(self) -> None:
        self._end_at = None
        self.session = Session.WORK
        self.remaining_seconds = self.preset.work_minutes * 60

    def select_preset(self, index: int) -> None:
        if not 0 <= index < len(self.presets):
            raise IndexError("Preset index is out of range")
        self.preset_index = index
        self.reset()

    def start(self, now: float | None = None) -> None:
        if self.running:
            return
        current_time = self._clock() if now is None else now
        self._end_at = current_time + self.remaining_seconds

    def pause(self, now: float | None = None) -> None:
        if not self.running:
            return
        current_time = self._clock() if now is None else now
        self.remaining_seconds = max(0.0, self._end_at - current_time)
        self._end_at = None

    def toggle(self, now: float | None = None) -> None:
        if self.running:
            self.pause(now)
        else:
            self.start(now)

    def skip(self) -> Session:
        completed = self.session
        was_running = self.running
        self._advance_session()
        if was_running:
            self.start()
        return completed

    def tick(self, now: float | None = None) -> Session | None:
        if not self.running:
            return None

        current_time = self._clock() if now is None else now
        self.remaining_seconds = max(0.0, self._end_at - current_time)
        if self.remaining_seconds > 0:
            return None

        completed = self.session
        self._advance_session()
        self.start(current_time)
        return completed

    def _advance_session(self) -> None:
        self._end_at = None
        if self.session is Session.WORK:
            self.session = Session.REST
            self.remaining_seconds = self.preset.rest_minutes * 60
        else:
            self.session = Session.WORK
            self.remaining_seconds = self.preset.work_minutes * 60

    def display_time(self) -> str:
        seconds = max(0, int(self.remaining_seconds + 0.999))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
