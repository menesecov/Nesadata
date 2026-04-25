from __future__ import annotations

import asyncio
import os

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

from core.proxy_parser import parse_proxy
from core.manager import AccountClient
from db import database as db
from cli.utils import clear

console = Console()

async def menu_accounts() -> None:
    while True:
        clear()
        console.print("\n[bold cyan]═══ ACCOUNTS ═══[/bold cyan]")
        console.print(" [1] List accounts")
        console.print(" [2] Add new account (phone auth)")
        console.print(" [3] Set / update proxy")
        console.print(" [4] Remove account")
        console.print(" [5] Check all accounts (Health check)")
        console.print(" [0] Back")
        choice = Prompt.ask("[bold]>[/bold]", default="0")

        if choice == "1":
            await _show_accounts(wait=True)
        elif choice == "2":
            await _add_account()
        elif choice == "3":
            await _set_proxy()
        elif choice == "4":
            await _remove_account()
        elif choice == "5":
            await _check_accounts()
        elif choice == "0":
            break

async def _show_accounts(wait: bool = False) -> list[db.aiosqlite.Row]:
    clear()
    rows = await db.get_accounts()
    if not rows:
        console.print("[yellow]No accounts stored.[/yellow]")
        if wait:
            input("\n  [Нажмите Enter, чтобы продолжить] ")
        return []

    table = Table(
        title="Accounts",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Phone", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Session", style="green")
    table.add_column("API ID", style="yellow")
    table.add_column("Sent", justify="right", style="bright_white")
    table.add_column("Proxy", style="blue")

    for i, r in enumerate(rows, 1):
        st = r["status"] or "Unknown"
        if st == "Active": color = "bold green"
        elif st == "Inactive": color = "bold red"
        else: color = "dim yellow"

        table.add_row(
            str(i),
            r["phone"],
            f"[{color}]{st}[/{color}]",
            r["session"],
            str(r["api_id"]),
            str(r["sent_count"]),
            r["proxy"] or "[dim]None[/dim]",
        )

    console.print(table)
    if wait:
        input("\n  [Нажмите Enter, чтобы продолжить] ")
    return rows

async def _add_account() -> None:
    clear()
    console.print("\n[bold cyan]── Add Account ──[/bold cyan] [dim](Введите 0 для отмены)[/dim]")

    while True:
        api_id_str = Prompt.ask("API ID").strip()
        if api_id_str == "0": return
        if api_id_str.isdigit():
            api_id = int(api_id_str)
            break
        console.print("[red]Ошибка: Введите цифры или 0 для отмены.[/red]")

    while True:
        api_hash = Prompt.ask("API Hash").strip()
        if api_hash == "0": return
        if api_hash: break
        console.print("[red]Ошибка: Hash не может быть пустым.[/red]")

    while True:
        phone = Prompt.ask("Phone").strip()
        if phone == "0": return
        if phone: break
        console.print("[red]Ошибка: Номер обязателен.[/red]")

    session_name = Prompt.ask("Session name", default=phone.replace("+", ""))
    if session_name == "0": return

    proxy_str = Prompt.ask("Proxy (optional)", default="")
    if proxy_str == "0": return
    proxy = parse_proxy(proxy_str)

    os.makedirs("sessions", exist_ok=True)

    client_kwargs: dict = dict(
        name=session_name,
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        workdir="sessions",
        no_updates=True,
    )
    if proxy:
        client_kwargs["proxy"] = proxy

    client = Client(**client_kwargs)

    try:
        await client.connect()
        sent = await client.send_code(phone)

        while True:
            code = Prompt.ask("Telegram Code").strip()
            if code == "0":
                await client.disconnect()
                return
            if code: break

        try:
            await client.sign_in(phone, sent.phone_code_hash, code)
        except SessionPasswordNeeded:
            while True:
                pwd = Prompt.ask("2FA Password", password=True).strip()
                if pwd == "0":
                    await client.disconnect()
                    return
                if pwd: break
            await client.check_password(pwd)

        me = await client.get_me()
        await client.disconnect()

        await db.add_account(
            phone=phone, api_id=api_id, api_hash=api_hash,
            session=session_name, proxy=proxy_str.strip() or None,
        )
        console.print(f"\n[green]✓ Добавлен: {me.first_name} ({phone})[/green]")
    except Exception as e:
        console.print(f"\n[red]Ошибка:[/red] {e}")
        try: await client.disconnect()
        except: pass

    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _set_proxy() -> None:
    rows = await _show_accounts(wait=False)
    if not rows: return

async def _set_proxy() -> None:
    rows = await _show_accounts(wait=False)
    if not rows: return

    while True:
        idx_str = Prompt.ask("Номер аккаунта (#) для прокси (0 = Отмена)").strip()
        if idx_str == "0": return
        try:
            idx = int(idx_str) - 1
            if 0 <= idx < len(rows):
                target = rows[idx]
                break
        except: pass
        console.print("[red]Неверный выбор.[/red]")

    proxy_str = Prompt.ask(f"Новый прокси для {target['phone']} (0 = Отмена, Пусто = Удалить)")
    if proxy_str == "0": return

    test = parse_proxy(proxy_str)
    if proxy_str.strip() and test is None:
        console.print("[red]Неверный формат прокси.[/red]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    await db.set_account_proxy(target['phone'], proxy_str.strip() or None)
    console.print("[green]✓ Обновлено.[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")

async def _remove_account() -> None:
    rows = await _show_accounts(wait=False)
    if not rows: return

    while True:
        idx_str = Prompt.ask("Номер аккаунта (#) для удаления (0 = Отмена)").strip()
        if idx_str == "0": return
        try:
            idx = int(idx_str) - 1
            if 0 <= idx < len(rows):
                target = rows[idx]
                break
        except: pass
        console.print("[red]Неверный выбор.[/red]")

    if Confirm.ask(f"Удалить аккаунт [cyan]{target['phone']}[/cyan]?"):
        await db.remove_account(target['phone'])
        console.print("[green]✓ Удалено.[/green]")
    input("\n  [Нажмите Enter, чтобы продолжить] ")


async def _check_accounts() -> None:
    clear()
    rows = await db.get_accounts()
    if not rows:
        console.print("[yellow]Нет аккаунтов.[/yellow]")
        input("\n  [Нажмите Enter, чтобы продолжить] ")
        return

    console.print(f"[bold cyan]Проверка {len(rows)} аккаунтов...[/bold cyan]\n")

    results_table = Table(title="Health Check Results", header_style="bold magenta")
    results_table.add_column("Phone", style="cyan")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Details", style="dim")

    for r in rows:
        ac = AccountClient(r)
        status_label = ""
        db_status = "Unknown"
        details = ""

        try:
            await asyncio.wait_for(ac.start(), timeout=15)
            me = await ac.client.get_me()
            status_label = "[bold green]ALIVE[/bold green]"
            db_status = "Active"
            details = f"Name: {me.first_name} | @{me.username or ''}"
            await ac.stop()
        except asyncio.TimeoutError:
            status_label = "[bold red]TIMEOUT[/bold red]"
            db_status = "Unknown"
            details = "Таймаут"
        except Exception as e:
            err_msg = str(e).lower()
            if "auth_key_unregistered" in err_msg or "session_revoked" in err_msg:
                status_label = "[bold red]EXPIRED[/bold red]"
                db_status = "Inactive"
                details = "Сессия сдохла"
            elif "user_deactivated" in err_msg or "user_is_blocked" in err_msg:
                status_label = "[bold red]BANNED[/bold red]"
                db_status = "Inactive"
                details = "Бан"
            elif "proxy" in err_msg or "connection" in err_msg:
                status_label = "[bold yellow]PROXY ERR[/bold yellow]"
                db_status = "Unknown"
                details = f"Прокси: {type(e).__name__}"
            else:
                status_label = "[bold red]ERROR[/bold red]"
                db_status = "Inactive"
                details = str(e)

            try: await ac.stop()
            except: pass

        await db.update_account_status(r["phone"], db_status)
        results_table.add_row(r["phone"], status_label, details)

    clear()
    console.print(results_table)
    input("\n  [Нажмите Enter, чтобы продолжить] ")