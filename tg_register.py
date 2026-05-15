#!/usr/bin/env python3
"""
Shadow TG Register v1.0
========================
Automated account creation & workflow recorder for Telegram bots.
Records every step (message sent / button clicked) and replays N times.

Usage:
    python3 tg_register.py

Authorized use only — Shadow Red Team 2026
"""

import os, sys, json, time, random, string, asyncio, warnings
from datetime import datetime
from pathlib import Path
warnings.filterwarnings("ignore")

# ── Dependencies ──────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.table import Table
    from rich import box as rbox
except ImportError:
    os.system("pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.table import Table
    from rich import box as rbox

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        KeyboardButtonRow, KeyboardButton,
        ReplyInlineMarkup, ReplyKeyboardMarkup,
        KeyboardButtonCallback, KeyboardButtonUrl,
    )
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    os.system("pip install telethon -q")
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        KeyboardButtonRow, KeyboardButton,
        ReplyInlineMarkup, ReplyKeyboardMarkup,
        KeyboardButtonCallback, KeyboardButtonUrl,
    )
    from telethon.errors import SessionPasswordNeededError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

console = Console()

# ── Global state ──────────────────────────────────────────────────────────────
state = {
    "bot_username": "",
    "actions":      [],       # recorded steps
    "start":        datetime.now().isoformat(),
}

_client: TelegramClient = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _rnd(mode: str, label: str = "") -> str:
    """Generate a random value based on mode and label hint."""
    lbl = label.lower()
    if mode == "fix":
        return ""   # caller supplies fixed value
    if any(x in lbl for x in ["phone", "tel", "mobile", "number"]):
        return "+216" + "".join(random.choices(string.digits, k=8))
    if any(x in lbl for x in ["email", "mail"]):
        return "".join(random.choices(string.ascii_lowercase, k=8)) + "@shadow.com"
    if any(x in lbl for x in ["pass", "pwd", "secret"]):
        return "".join(random.choices(string.ascii_letters + string.digits + "!@#", k=12))
    if any(x in lbl for x in ["name", "user", "login"]):
        return "".join(random.choices(string.ascii_lowercase, k=9))
    if any(x in lbl for x in ["code", "otp", "verif"]):
        return "".join(random.choices(string.digits, k=6))
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _extract_buttons(message) -> list:
    """Extract all buttons from a Telegram message."""
    buttons = []
    markup = getattr(message, "reply_markup", None)
    if markup is None:
        return buttons
    rows = getattr(markup, "rows", [])
    for row in rows:
        for btn in getattr(row, "buttons", []):
            text = getattr(btn, "text", "")
            data = getattr(btn, "data", None)
            url  = getattr(btn, "url", None)
            btype = "callback" if data is not None else ("url" if url else "reply")
            buttons.append({"text": text, "type": btype, "data": data})
    return buttons


def _display_message(msg, idx: int = None):
    """Pretty-print a bot message with its buttons."""
    prefix = f"[dim][BOT][/dim] " if idx is None else f"[dim][{idx}][/dim] "
    text = (msg.text or msg.message or "").strip()
    if text:
        console.print(f"\n{prefix}[green]{text}[/green]")
    buttons = _extract_buttons(msg)
    if buttons:
        console.print("  [dim]Buttons:[/dim]")
        for i, b in enumerate(buttons):
            icon = "🔘" if b["type"] == "callback" else "🔗" if b["type"] == "url" else "💬"
            console.print(f"    [bold cyan]{i}[/bold cyan] {icon}  {b['text']}")
    return buttons


# ── Client setup ──────────────────────────────────────────────────────────────

async def setup_client() -> TelegramClient:
    """Interactive Telethon client setup."""
    console.print(Rule("[bold red]Client Setup[/bold red]"))

    api_id  = os.getenv("TG_API_ID")  or Prompt.ask("  [bold]API ID[/bold]   [dim](from my.telegram.org)[/dim]")
    api_hash = os.getenv("TG_API_HASH") or Prompt.ask("  [bold]API HASH[/bold] [dim](from my.telegram.org)[/dim]")
    phone    = os.getenv("TG_PHONE")   or Prompt.ask("  [bold]Phone[/bold]    [dim](+216xxxxxxxx)[/dim]")

    session_file = f"sessions/shadow_{phone.replace('+','')}"
    Path("sessions").mkdir(exist_ok=True)

    client = TelegramClient(session_file, int(api_id), api_hash)
    await client.start(phone=lambda: phone,
                       code_callback=lambda: Prompt.ask("  [bold yellow]Enter OTP code[/bold yellow]"))

    console.print(f"[green]✓ Connected as {phone}[/green]\n")
    return client


# ── Recording engine ──────────────────────────────────────────────────────────

async def record_session():
    """Interactive recording loop with a Telegram bot."""
    global _client

    bot_input = Prompt.ask("\n  [bold]Bot username or link[/bold] [dim](@username / t.me/botname)[/dim]")
    bot_username = bot_input.strip().lstrip("@").replace("https://t.me/", "").replace("t.me/", "")
    state["bot_username"] = bot_username

    console.print(f"\n[cyan][*] Opening chat with @{bot_username}...[/cyan]")

    # Send /start to kick off the bot
    await _client.send_message(bot_username, "/start")
    time.sleep(1.5)

    # Fetch last bot message
    msgs = await _client.get_messages(bot_username, limit=5)
    last_msg = None
    for m in msgs:
        if m.sender_id != (await _client.get_me()).id:
            last_msg = m
            break

    if last_msg:
        buttons = _display_message(last_msg)
        state["actions"].append({
            "step":    len(state["actions"]) + 1,
            "type":    "send",
            "value":   "/start",
            "mode":    "fix",
            "label":   "start command",
        })

    # ── Main recording loop ────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[dim]Recording — type your response or pick a button number[/dim]"))

    while True:
        console.print()
        cmd = Prompt.ask("[bold red]tg-rec[/bold red]").strip()

        if not cmd:
            continue

        # ── Commands ──────────────────────────────────────────────────────────
        if cmd.lower() in ("done", "stop", "quit", "exit"):
            break

        if cmd.lower() == "show":
            _display_actions()
            continue

        if cmd.lower().startswith("replay"):
            parts = cmd.lower().split()
            n = 1
            if len(parts) == 2:
                try: n = max(1, int(parts[1]))
                except ValueError: pass
            await replay_session(count=n)
            continue

        if cmd.lower() == "save":
            save_session()
            continue

        # ── Button selection (number) ─────────────────────────────────────────
        if cmd.isdigit() and last_msg:
            buttons = _extract_buttons(last_msg)
            idx = int(cmd)
            if 0 <= idx < len(buttons):
                btn = buttons[idx]
                console.print(f"  [dim]→ Clicking:[/dim] [cyan]{btn['text']}[/cyan]")

                mode = Prompt.ask(
                    "  Replay mode?",
                    choices=["fix", "skip"], default="fix"
                )

                state["actions"].append({
                    "step":    len(state["actions"]) + 1,
                    "type":    "button",
                    "value":   btn["text"],
                    "btn_type": btn["type"],
                    "btn_data": btn["data"].decode() if isinstance(btn.get("data"), bytes) else btn.get("data"),
                    "mode":    mode,
                    "label":   btn["text"],
                })

                if btn["type"] == "callback":
                    await _client.send_message(bot_username, btn["text"])
                else:
                    await _client.send_message(bot_username, btn["text"])

                await asyncio.sleep(1.5)
                msgs = await _client.get_messages(bot_username, limit=3)
                last_msg = None
                for m in msgs:
                    if m.sender_id != (await _client.get_me()).id:
                        last_msg = m
                        break
                if last_msg:
                    _display_message(last_msg)
                continue
            else:
                console.print(f"[yellow]No button #{idx}[/yellow]")
                continue

        # ── Text input ────────────────────────────────────────────────────────
        label = Prompt.ask("  [dim]Field label (e.g. phone / email / name)[/dim]", default="text")
        mode  = Prompt.ask(
            "  Replay mode?",
            choices=["fix", "random", "skip"], default="fix"
        )

        state["actions"].append({
            "step":  len(state["actions"]) + 1,
            "type":  "send",
            "value": cmd,
            "mode":  mode,
            "label": label,
        })

        await _client.send_message(bot_username, cmd)
        await asyncio.sleep(1.5)

        msgs = await _client.get_messages(bot_username, limit=3)
        last_msg = None
        for m in msgs:
            if m.sender_id != (await _client.get_me()).id:
                last_msg = m
                break
        if last_msg:
            _display_message(last_msg)


# ── Replay engine ─────────────────────────────────────────────────────────────

async def replay_session(count: int = 1):
    """Replay the recorded session N times."""
    acts = state["actions"]
    bot  = state["bot_username"]

    if not acts:
        console.print("[yellow]Nothing to replay.[/yellow]")
        return
    if not bot:
        bot = Prompt.ask("  Bot username")

    console.print()
    console.print(Rule("[bold red]REPLAY[/bold red]"))
    console.print(f"[cyan][*] Replaying {len(acts)} steps × [bold]{count}[/bold] time(s)...[/cyan]")

    me = await _client.get_me()

    for run_i in range(1, count + 1):
        if count > 1:
            console.print(f"\n[bold cyan]━━━ Run {run_i}/{count} ━━━[/bold cyan]")

        for a in acts:
            if a.get("mode") == "skip":
                console.print(f"  [dim]→ skip: {a['label']}[/dim]")
                continue

            # Resolve value
            if a["mode"] == "random":
                val = _rnd("random", a.get("label", ""))
            else:
                val = a["value"]

            step_label = a.get("label", a.get("value", ""))

            if a["type"] == "send":
                console.print(f"  [yellow]SEND[/yellow]   [{step_label}] → [cyan]{val}[/cyan]")
                await _client.send_message(bot, val)
                await asyncio.sleep(1.2)

            elif a["type"] == "button":
                console.print(f"  [red]CLICK[/red]  [{step_label}] → [cyan]{val}[/cyan]")
                await _client.send_message(bot, val)
                await asyncio.sleep(1.2)

            # Show bot reply
            msgs = await _client.get_messages(bot, limit=3)
            for m in msgs:
                if m.sender_id != me.id:
                    text = (m.text or m.message or "").strip()
                    if text:
                        console.print(f"  [dim][BOT][/dim] [green]{text[:120]}[/green]")
                    break

        console.print(f"\n[bold green]✓ Run {run_i}/{count} complete.[/bold green]")

    console.print()
    console.print(f"[bold green]✓ All {count} run(s) finished.[/bold green]")


# ── Display / Save ────────────────────────────────────────────────────────────

def _display_actions():
    acts = state["actions"]
    if not acts:
        console.print("[yellow]No actions recorded.[/yellow]")
        return

    t = Table(title=f"Recorded Steps — @{state['bot_username']}",
              box=rbox.SIMPLE, show_lines=False)
    t.add_column("#",     style="dim",    width=4)
    t.add_column("Type",  style="yellow", width=8)
    t.add_column("Label", style="cyan",   width=20)
    t.add_column("Value", style="white",  width=30)
    t.add_column("Mode",  style="dim",    width=8)

    for a in acts:
        t.add_row(
            str(a["step"]),
            a["type"],
            a.get("label", ""),
            str(a.get("value", ""))[:30],
            a.get("mode", "fix"),
        )
    console.print(t)


def save_session() -> str:
    Path("sessions").mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"sessions/tg_session_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "recorded_at":   state["start"],
            "bot_username":  state["bot_username"],
            "total_steps":   len(state["actions"]),
            "actions":       state["actions"],
        }, f, indent=2, ensure_ascii=False)
    console.print(f"[green][+] Saved →[/green] [cyan]{path}[/cyan]")
    return path


# ── Banner ────────────────────────────────────────────────────────────────────

def banner():
    console.clear()
    console.print()
    console.print(Panel(
        "[bold red]Shadow TG Register[/bold red]  [dim]v1.0 — Telegram Bot Recorder[/dim]\n"
        "[dim]Record every step with a Telegram bot → replay N times.\n"
        "Supports inline keyboards, reply keyboards, and text prompts.\n"
        "Authorized use only — Shadow Red Team 2026[/dim]\n\n"
        "[bold]Commands (during recording):[/bold]\n"
        "  [cyan]<number>[/cyan]       click a button by index\n"
        "  [cyan]<text>[/cyan]         send a text message to the bot\n"
        "  [cyan]replay[/cyan]         replay session once\n"
        "  [cyan]replay <N>[/cyan]     replay N times (e.g. replay 5)\n"
        "  [cyan]show[/cyan]           display recorded steps\n"
        "  [cyan]save[/cyan]           export session to JSON\n"
        "  [cyan]done[/cyan]           replay + save + exit\n"
        "  [cyan]quit[/cyan]           exit without saving",
        border_style="red", padding=(0, 3),
    ))
    console.print()


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    banner()

    global _client
    _client = await setup_client()

    try:
        await record_session()
    except KeyboardInterrupt:
        pass

    # Done — ask for replay count then save
    console.print()
    _display_actions()

    if state["actions"]:
        if Confirm.ask("\n  [bold cyan]Replay before saving?[/bold cyan]", default=True):
            try:
                n = int(Prompt.ask("  How many times?", default="1"))
            except ValueError:
                n = 1
            await replay_session(count=max(1, n))

        save_session()

    await _client.disconnect()
    console.print("\n[bold red]Shadow TG Register — session closed.[/bold red]\n")


if __name__ == "__main__":
    asyncio.run(main())
