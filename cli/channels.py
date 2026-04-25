from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from db import database as db
from cli.utils import clear

console = Console()

async def menu_channels() -> None:
    while True:
        clear()
        console.print("\n[bold cyan]═══ CHANNELS ═══[/bold cyan]")
        console.print(" [1] List channels")
        console.print(" [2] Add channel")
        console.print(" [3] Add multiple channels (paste list)")
        console.print(" [4] Remove channel")
        console.print(" [0] Back")
        choice = Prompt.ask("[bold]>[/bold]", default="0")

        if choice == "1":
            await _show_channels(wait=True)
        elif choice == "2":
            await _add_single()
        elif choice == "3":
            await _add_bulk()
        elif choice == "4":
            await _remove_channel()
        elif choice == "0":
            break

async def _show_channels(wait: bool = False) -> list[db.aiosqlite.Row]:
    clear()
    rows = await db.get_channels()
    if not rows:
        console.print("[yellow]No channels stored.[/yellow]")
        if wait:
            input("\n  [Нажмите Enter, чтобы продолжить] ")
        return []

    table = Table(
        title=f"Channels ({len(rows)})",
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Username", style="cyan")

    for i, r in enumerate(rows, 1):
        table.add_row(str(i), f"@{r['username']}")

    console.print(table)
    if wait:
        input("\n  [Нажмите Enter, чтобы продолжить] ")
    return rows

async def _add_single() -> None:
    clear()
    username = Prompt.ask("Channel @username")
    username = username.lstrip("@").strip()
    if not username:
        console.print("[red]Empty username.[/red]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return
    await db.add_channel(username)
    console.print(f"[green]✓ Added:[/green] @{username}")
    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _add_bulk() -> None:
    clear()
    console.print(
        "[dim]Paste @usernames one per line. "
        "Enter an empty line when done.[/dim]"
    )
    added = 0
    while True:
        line = input().strip()
        if not line:
            break
        username = line.lstrip("@").strip()
        if username:
            await db.add_channel(username)
            added += 1
    console.print(f"[green]✓ Added {added} channel(s).[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _remove_channel() -> None:
    rows = await _show_channels(wait=False)
    if not rows: return

    idx_str = Prompt.ask("Выберите номер канала (#) для удаления")
    try:
        idx = int(idx_str) - 1
        if not (0 <= idx < len(rows)): raise ValueError
        target = rows[idx]
    except ValueError:
        console.print("[red]Неверный номер.[/red]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    if Confirm.ask(f"Remove [cyan]@{target['username']}[/cyan]?"):
        await db.remove_channel(target['username'])
        console.print("[green]✓ Removed.[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")