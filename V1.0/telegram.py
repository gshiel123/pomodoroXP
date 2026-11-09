from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str, chat_id: str, timeout: float = 15.0) -> None:
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str) -> None:
        if not self.configured:
            raise TelegramError(
                "Configure a Telegram bot token and chat ID in Settings first."
            )

        payload = urlencode({"chat_id": self.chat_id, "text": text}).encode()
        request = Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise TelegramError(f"Telegram request failed: {error}") from error
        except (OSError, ValueError) as error:
            raise TelegramError(f"Could not read Telegram response: {error}") from error

        if result.get("ok") is not True:
            raise TelegramError(
                result.get("description", "Telegram rejected the message")
            )

    def find_chats(self) -> list[tuple[str, str]]:
        if not self.token:
            raise TelegramError("Configure a Telegram bot token first.")

        request = Request(
            f"https://api.telegram.org/bot{self.token}/getUpdates",
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise TelegramError(f"Telegram request failed: {error}") from error
        except (OSError, ValueError) as error:
            raise TelegramError(f"Could not read Telegram response: {error}") from error

        chats: dict[str, str] = {}
        for update in result.get("result", []):
            message = (
                update.get("message")
                or update.get("edited_message")
                or update.get("channel_post")
                or {}
            )
            chat = message.get("chat") or {}
            if "id" not in chat:
                continue
            name = chat.get("title") or " ".join(
                part for part in (chat.get("first_name"), chat.get("last_name")) if part
            )
            chats[str(chat["id"])] = name or chat.get("username", "Telegram chat")
        return list(chats.items())
