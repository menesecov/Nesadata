from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt, Confirm

from db import database as db
from cli.utils import clear

console = Console()

async def menu_text() -> None:
    while True:
        clear()
        console.print("\n[bold cyan]═══ MESSAGE TEXT ═══[/bold cyan]")
        console.print(" [1] View current text")
        console.print(" [2] Edit text")
        console.print(" [3] Clear text")
        console.print(" [0] Back")
        choice = Prompt.ask("[bold]>[/bold]", default="0")

        if choice == "1":
            await _view_text()
        elif choice == "2":
            await _edit_text()
        elif choice == "3":
            await _clear_text()
        elif choice == "0":
            break

async def _view_text() -> None:
    clear()
    text = await db.get_message_text()
    if not text.strip():
        console.print("[yellow]No message text set.[/yellow]")
    else:
        console.print(Panel(text, title="Current Message", border_style="cyan"))
    input("\n  [Press Enter to continue] ")

async def _edit_text() -> None:
    clear()
    console.print(Rule("[bold cyan]Edit Message[/bold cyan]"))
    console.print(
        "[dim]Введите текст сообщения построчно.\n"
        "  • Сохранить:  [bold]Ctrl+Z[/bold] затем [bold]Enter[/bold]  (Windows)\n"
        "  • Или введите [bold].save[/bold] на отдельной строке\n[/dim]"
    )
    console.print(Rule(style="dim"))

    existing = await db.get_message_text()
    if existing.strip():
        console.print(
            Panel(existing,
                  title="[dim]Текущий текст (будет заменён)[/dim]",
                  border_style="dim")
        )
        console.print()

    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == ".save":
                break
            lines.append(line)
    except EOFError:
        pass
    if not lines:
        console.print("[yellow]Текст пустой — ничего не сохранено.[/yellow]")
        input("\n  [Press Enter to continue] ")
        return

    text = "\n".join(lines)
    await db.set_message_text(text)
    console.print(
        f"\n[green]✓ Сохранено[/green] — "
        f"[cyan]{len(lines)} строк, {len(text)} символов[/cyan]"
    )
    input("\n  [Press Enter to continue] ")

async def _clear_text() -> None:
    clear()
    if Confirm.ask("Очистить текущий текст сообщения?"):
        await db.set_message_text("")
        console.print("[green]✓ Очищено.[/green]")