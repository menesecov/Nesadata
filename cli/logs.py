from __future__ import annotations

import asyncio
import signal

from rich.console import Console
from rich.prompt import Prompt

from core.manager import Manager
from core.logger import log
from db import database as db
from cli.utils import clear
import threading

console = Console()

async def start_sender() -> None:
    """
    Prompt confirmation, then run the sender loop.
    Ctrl+C stops the loop gracefully.
    """
    clear()
    settings = await db.get_all_settings()
    mode = settings.get("mode", "obo")
    delay_min = settings.get("delay_min", "3")
    delay_max = settings.get("delay_max", "7")
    limit = settings.get("autonomous_limit", "0")
    accounts = await db.get_accounts()
    channels = await db.get_channels()
    text = await db.get_message_text()

    console.print("\n[bold cyan]═══ START SENDER ═══[/bold cyan]")
    console.print(f"  Mode           : [green]{mode}[/green]")
    console.print(f"  Delay          : [green]{delay_min}–{delay_max}s[/green]")
    console.print(f"  Autonomous lim : [green]{'∞' if limit == '0' else limit + ' min'}[/green]")
    console.print(f"  Accounts       : [green]{len(accounts)}[/green]")
    console.print(f"  Channels       : [green]{len(channels)}[/green]")
    console.print(f"  Text length    : [green]{len(text)} chars[/green]")
    console.print("\n[dim]Press Ctrl+C at any time to stop gracefully.[/dim]\n")

    confirm = Prompt.ask("Start?", choices=["y", "n"], default="y")
    if confirm != "y":
        return

    manager = Manager()

    def command_listener():
        while not manager._stop_event.is_set():
            try:

                cmd = input().strip().lower()
                if cmd in ("/stop", "stop"):
                    log.warning("[yellow]Command received: stopping...[/yellow]")
                    manager.stop()
                    break
            except EOFError:
                break
            except Exception:
                break

    input_thread = threading.Thread(target=command_listener, daemon=True)
    input_thread.start()

    loop = asyncio.get_event_loop()

    def _signal_handler() -> None:
        log.warning("[yellow]Stop signal received — finishing current send…[/yellow]")
        manager.stop()

    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        pass
    try:
        await manager.run()
    except KeyboardInterrupt:
        manager.stop()
    finally:
        try:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        except (NotImplementedError, Exception):
            pass

    console.print("\n[bold green]Sender stopped.[/bold green]")