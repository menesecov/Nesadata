from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from db import database as db
from cli.utils import clear

console = Console()

SETTING_META = {
    "delay_min":        ("Delay min (sec)",         "3"),
    "delay_max":        ("Delay max (sec)",         "7"),
    "mode":             ("Send mode (obo/random)",  "obo"),
    "autonomous_limit": ("Autonomous limit (min, 0=∞)", "0"),
}

async def menu_settings() -> None:
    while True:
        clear()
        console.print("\n[bold cyan]═══ SETTINGS ═══[/bold cyan]")
        console.print(" [1] View settings")
        console.print(" [2] Edit setting")
        console.print(" [0] Back")
        choice = Prompt.ask("[bold]>[/bold]", default="0")

        if choice == "1":
            await _show_settings(wait=True)
        elif choice == "2":
            await _edit_setting()
        elif choice == "0":
            break

async def _show_settings(wait: bool = False) -> None:
    clear()
    current = await db.get_all_settings()

    table = Table(
        title="Current Settings",
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("Key", style="cyan")
    table.add_column("Description", style="dim")
    table.add_column("Value", style="bright_white")

    for key, (desc, _) in SETTING_META.items():
        val = current.get(key, "[dim]not set[/dim]")
        table.add_row(key, desc, val)

    console.print(table)
    if wait:
        input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _edit_setting() -> None:

    await _show_settings(wait=False)
    key = Prompt.ask("Setting key to change")

    if key not in SETTING_META:
        console.print(f"[red]Unknown key: {key}[/red]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    desc, default = SETTING_META[key]
    current = await db.get_setting(key) or default
    new_val = Prompt.ask(f"{desc}", default=current)

    if key in ("delay_min", "delay_max"):
        try:
            float(new_val)
        except ValueError:
            console.print("[red]Must be a number.[/red]")
            input("\n  [Нажмите Enter, чтобы продолжить] ")
            return
    elif key == "mode" and new_val not in ("obo", "random"):
        console.print("[red]Mode must be 'obo' or 'random'.[/red]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return
    elif key == "autonomous_limit":
        try:
            int(new_val)
        except ValueError:
            console.print("[red]Must be an integer.[/red]")
            input("\n  [Нажмите Enter, чтобы продолжить] ")
            return

    await db.set_setting(key, new_val)
    console.print(f"[green]✓ {key} = {new_val}[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")