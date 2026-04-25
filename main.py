from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from db.database import init_db
from cli.accounts import menu_accounts
from cli.channels import menu_channels
from cli.text import menu_text
from cli.settings import menu_settings
from cli.logs import start_sender
from cli.io import menu_io
from cli.utils import clear, BANNER

console = Console()

from cli.utils import clear, BANNER

MAIN_MENU = """
 [bold][1][/bold] Accounts      — Manage Telegram sessions
 [bold][2][/bold] Channels      — Target channel list
 [bold][3][/bold] Text          — Broadcast message
 [bold][4][/bold] Settings      — Delay, mode, autonomous limit
 [bold][5][/bold] Start Sender  — Launch the send loop (live logs)
 [bold][6][/bold] Import/Export — Bulk sync channels/sessions
 [bold][0][/bold] Exit
"""

async def main_loop() -> None:
    await init_db()

    while True:
        clear()
        console.print(
            Panel(MAIN_MENU, title="[bold magenta]Main Menu[/bold magenta]",
                  border_style="cyan", expand=False)
        )
        choice = Prompt.ask("[bold]Select[/bold]", default="0")

        if choice == "1":
            await menu_accounts()
        elif choice == "2":
            await menu_channels()
        elif choice == "3":
            await menu_text()
        elif choice == "4":
            await menu_settings()
        elif choice == "5":
            await start_sender()
        elif choice == "6":
            await menu_io()
        elif choice == "0":
            console.print("[dim]Bye.[/dim]")
            break
        else:
            console.print("[red]Unknown option.[/red]")


async def cleanup_tasks(loop: asyncio.AbstractEventLoop):
    """Gracefully cancel all pending tasks before closing the loop."""
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    if not tasks:
        return
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)

def main() -> None:
    try:
        _loop.run_until_complete(main_loop())
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Bye.[/dim]")
    finally:
        try:
            _loop.run_until_complete(cleanup_tasks(_loop))
            _loop.run_until_complete(asyncio.sleep(0.1))
        except Exception:
            pass
        _loop.close()

if __name__ == "__main__":
    main()
