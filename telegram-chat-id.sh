#!/bin/bash
# Prints the chat IDs that have recently messaged your bot, and saves the newest one to the .env.
set -euo pipefail

ENV_FILE="<directory to your env file>v"
TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' ')

if [ -z "$TOKEN" ]; then
  echo "Add TELEGRAM_BOT_TOKEN to $ENV_FILE first." >&2
  exit 1
fi

RESPONSE=$(curl -fsS "https://api.telegram.org/bot${TOKEN}/getUpdates")

CHATS=$(printf '%s' "$RESPONSE" | /usr/bin/python3 -c '
import json, sys
seen = {}
for u in json.load(sys.stdin).get("result", []):
    msg = u.get("message") or u.get("edited_message") or u.get("channel_post") or {}
    chat = msg.get("chat")
    if chat:
        name = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("username", "")
        seen[chat["id"]] = name
for cid, name in seen.items():
    print(f"{cid}\t{name}")
')

if [ -z "$CHATS" ]; then
  echo "No messages found. Send any message to your bot in Telegram, then run this again." >&2
  echo "(If the bot uses a webhook, getUpdates returns nothing; find the chat ID another way.)" >&2
  exit 1
fi

echo "Chats that messaged the bot:"
echo "$CHATS"

LATEST=$(echo "$CHATS" | tail -1 | cut -f1)
/usr/bin/sed -i '' "s/^TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=${LATEST}/" "$ENV_FILE"
echo "Saved TELEGRAM_CHAT_ID=${LATEST} to $ENV_FILE"
