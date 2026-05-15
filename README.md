# Shadow TG Register 🤖

**Automated account creation & workflow recorder for Telegram bots.**

Shadow Red Team 2026 — Authorized use only.

---

## What it does

- Connects to any Telegram bot via **Bot API** or **Telethon (MTProto)**
- Records the full registration/onboarding flow step by step
- Replays the recorded session N times with **random or fixed data**
- Supports bots that use **inline keyboards**, **reply keyboards**, and **text prompts**
- Exports sessions to JSON for audit / reporting

---

## Structure

```
shadow-tg-register/
├── tg_register.py      # Main interactive CLI
├── sessions/           # Saved session files (JSON)
├── requirements.txt
└── README.md
```

---

## Usage

```bash
pip install -r requirements.txt
python3 tg_register.py
```

---

## Commands (interactive CLI)

| Command | Description |
|---|---|
| `start` | Start recording a new bot session |
| `replay` | Replay last session once |
| `replay <N>` | Replay N times |
| `show` | Show recorded steps |
| `save` | Export session to JSON |
| `done` | Replay + save + exit |
| `quit` | Exit without saving |

---

## Requirements

- Python 3.9+
- `telethon` — MTProto client
- `rich` — CLI interface
- A Telegram **phone number** or **bot token**
