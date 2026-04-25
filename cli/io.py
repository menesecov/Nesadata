import os
import json
from rich.console import Console
from rich.prompt import Prompt, Confirm
from db import database as db
from cli.utils import clear

console = Console()

async def menu_io() -> None:
    while True:
        clear()
        console.print("\n[bold cyan]═══ IMPORT / EXPORT ═══[/bold cyan]")
        console.print(" [1] Import Channels (from channels_import.txt)")
        console.print(" [2] Export Channels (to channels_export.txt)")
        console.print(" [3] Scan & Auto-Import Sessions (needs /sessions + json)")
        console.print(" [4] Export Account Data (to JSON + TXT)")
        console.print(" [0] Back")

        choice = Prompt.ask("[bold]>[/bold]", default="0")

        if choice == "1":
            await _import_channels()
        elif choice == "2":
            await _export_channels()
        elif choice == "3":
            await _import_sessions()
        elif choice == "4":
            await _export_accounts()
        elif choice == "0":
            break

async def _import_channels() -> None:
    clear()
    filename = "channels_import.txt"
    if not os.path.exists(filename):
        console.print(f"[red]Error:[/red] File [yellow]{filename}[/yellow] not found.")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    raw_list = content.replace(",", "\n").split("\n")
    added = 0
    for item in raw_list:
        username = item.strip().lstrip("@")
        if username:
            await db.add_channel(username)
            added += 1

    console.print(f"[green]✓ Imported {added} channels.[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _export_channels() -> None:
    clear()
    rows = await db.get_channels()
    if not rows:
        console.print("[yellow]No channels to export.[/yellow]")
    else:
        filename = "channels_export.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(f"@{r['username']}\n")
        console.print(f"[green]✓ Exported {len(rows)} channels to {filename}[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _import_sessions() -> None:
    clear()
    session_dir = "sessions"
    metadata_file = "accounts_metadata.json"

    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        console.print(f"[yellow]Folder '{session_dir}' was empty.[/yellow]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    files = [f for f in os.listdir(session_dir) if f.endswith(".session")]
    if not files:
        console.print("[yellow]No .session files found in /sessions folder.[/yellow]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    metadata = {}
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            console.print(f"[green]✓ Loaded metadata for {len(metadata)} accounts from JSON.[/green]")
        except Exception as e:
            console.print(f"[red]Error loading JSON metadata:[/red] {e}")

    existing_rows = await db.get_accounts()
    existing_sessions = {r["session"] for r in existing_rows}

    new_sessions = [f[:-8] for f in files if f[:-8] not in existing_sessions]

    if not new_sessions:
        console.print("[green]All session files are already in the database.[/green]")
    else:
        console.print(f"[cyan]Found {len(new_sessions)} new session files.[/cyan]\n")

        auto_count = 0
        manual_sessions = []

        for sess_name in new_sessions:
            if sess_name in metadata:

                data = metadata[sess_name]
                await db.add_account(
                    phone=data["phone"],
                    api_id=int(data["api_id"]),
                    api_hash=data["api_hash"],
                    session=sess_name,
                    proxy=data.get("proxy")
                )
                auto_count += 1
            else:
                manual_sessions.append(sess_name)

        if auto_count > 0:
            console.print(f"[bold green]✓ Automatically imported {auto_count} accounts from metadata![/bold green]")

        if manual_sessions:
            console.print(f"\n[yellow]{len(manual_sessions)} sessions have no metadata in JSON.[/yellow]")
            if Confirm.ask("Import them manually?"):
                def_api_id = Prompt.ask("Default API ID", default="")
                def_api_hash = Prompt.ask("Default API Hash", default="")

                for sess_name in manual_sessions:
                    console.print(f"\n[bold yellow]Manual Import: {sess_name}.session[/bold yellow] [dim](0 to cancel)[/dim]")

                    while True:
                        phone = Prompt.ask("Phone", default=sess_name if sess_name.startswith("+") else "").strip()
                        if phone == "0": return
                        if phone: break
                        console.print("[red]Phone required.[/red]")

                    while True:
                        api_id_s = def_api_id or Prompt.ask("API ID").strip()
                        if api_id_s == "0": return
                        if api_id_s.isdigit():
                            api_id = int(api_id_s)
                            break
                        console.print("[red]API ID must be numeric.[/red]")

                    while True:
                        api_hash = def_api_hash or Prompt.ask("API Hash").strip()
                        if api_hash == "0": return
                        if api_hash: break
                        console.print("[red]API Hash required.[/red]")

                    await db.add_account(phone=phone, api_id=api_id, api_hash=api_hash, session=sess_name)
                    console.print(f"[green]✓ Added.[/green]")

    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _export_accounts() -> None:
    clear()
    rows = await db.get_accounts()
    if not rows:
        console.print("[yellow]No accounts to export.[/yellow]")
    else:

        metadata = {}
        for r in rows:
            metadata[r["session"]] = {
                "phone": r["phone"],
                "api_id": r["api_id"],
                "api_hash": r["api_hash"],
                "proxy": r["proxy"]
            }

        with open("accounts_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        filename = "accounts_export.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{'Phone':<15} | {'API ID':<10} | {'Proxy':<20} | {'Session'}\n")
            f.write("-" * 70 + "\n")
            for r in rows:
                f.write(f"{r['phone']:<15} | {r['api_id']:<10} | {str(r['proxy']):<20} | {r['session']}\n")

        console.print(f"[green]✓ Exported metadata to [bold]accounts_metadata.json[/bold][/green]")
        console.print(f"[green]✓ Exported report to [bold]{filename}[/bold][/green]")

    input("\n  [Нажмите Enter, чтобы продолжить] ")