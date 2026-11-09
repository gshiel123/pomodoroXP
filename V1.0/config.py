from __future__ import annotations

import os

import keyring
from PySide6.QtCore import QSettings


SERVICE_NAME = "PomodoroXP"
TOKEN_KEY = "telegram_bot_token"
CHAT_ID_KEY = "telegram_chat_id"
PRESET_KEY = "preset_index"
ALWAYS_ON_TOP_KEY = "always_on_top"
OPACITY_KEY = "opacity_percent"


def settings() -> QSettings:
    return QSettings("PomodoroXP", "PomodoroXP")


def load_token() -> str:
    environment_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if environment_token:
        return environment_token
    return keyring.get_password(SERVICE_NAME, TOKEN_KEY) or ""


def save_token(token: str) -> None:
    keyring.set_password(SERVICE_NAME, TOKEN_KEY, token.strip())


def load_chat_id() -> str:
    return settings().value(CHAT_ID_KEY, "", type=str).strip()


def save_chat_id(chat_id: str) -> None:
    settings().setValue(CHAT_ID_KEY, chat_id.strip())


def load_preset_index() -> int:
    return settings().value(PRESET_KEY, 0, type=int)


def save_preset_index(index: int) -> None:
    settings().setValue(PRESET_KEY, index)


def load_always_on_top() -> bool:
    return settings().value(ALWAYS_ON_TOP_KEY, False, type=bool)


def save_always_on_top(enabled: bool) -> None:
    settings().setValue(ALWAYS_ON_TOP_KEY, enabled)


def load_opacity() -> int:
    value = settings().value(OPACITY_KEY, 100, type=int)
    return value if value in (20, 40, 60, 80, 100) else 100


def save_opacity(percent: int) -> None:
    settings().setValue(OPACITY_KEY, percent)
