import logging
from rich.logging import RichHandler
from rich.console import Console

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True,
                          markup=True, show_path=False)],
)

log = logging.getLogger("nesadata")

def log_send(account_phone: str, channel: str, result: str, error: str = "") -> None:
    """Structured send-event log line."""
    status = "[green]✓ Success[/green]" if result == "ok" else f"[red]✗ Error: {error}[/red]"
    log.info(f"[cyan]{account_phone}[/cyan] → [yellow]@{channel}[/yellow] | {status}")
