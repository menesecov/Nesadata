from __future__ import annotations

import asyncio
import random
import time
from typing import Optional

from pyrogram import Client
from pyrogram.errors import (
    FloodWait, UserBannedInChannel, ChatWriteForbidden,
    SlowmodeWait, PeerIdInvalid, ChannelPrivate,
)

from core.logger import log, log_send
from core.proxy_parser import parse_proxy
from db import database as db

class AccountClient:
    def __init__(self, row: db.aiosqlite.Row) -> None:
        self.phone: str = row["phone"]
        self.api_id: int = row["api_id"]
        self.api_hash: str = row["api_hash"]
        self.session: str = row["session"]
        self.proxy_str: str | None = row["proxy"]
        self.client: Optional[Client] = None

    def build_client(self) -> Client:
        proxy = parse_proxy(self.proxy_str) if self.proxy_str else None
        kwargs: dict = dict(
            name=self.session,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir="sessions",
            no_updates=True,
        )
        if proxy:
            kwargs["proxy"] = proxy
        self.client = Client(**kwargs)
        return self.client

    async def start(self) -> None:
        if self.client is None:
            self.build_client()
        await self.client.start()
        log.info(f"[green]Connected:[/green] {self.phone}")

    async def stop(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.stop()
            log.info(f"[yellow]Disconnected:[/yellow] {self.phone}")

    async def send_message(self, channel: str, text: str) -> str:
        """Send a message; return 'ok' or error string."""
        try:
            await self.client.send_message(channel, text)
            return "ok"
        except FloodWait as e:
            log.warning(f"[yellow]FloodWait {e.value}s[/yellow] on {self.phone}")
            await asyncio.sleep(e.value)
            return f"flood_wait:{e.value}"
        except SlowmodeWait as e:
            log.warning(f"[yellow]SlowmodeWait {e.value}s[/yellow] on {self.phone}")
            await asyncio.sleep(e.value)
            return f"slowmode:{e.value}"
        except (UserBannedInChannel, ChatWriteForbidden, ChannelPrivate, PeerIdInvalid) as e:
            return type(e).__name__
        except Exception as e:
            return str(e)


class Manager:
    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def run(self) -> None:
        """Load config from DB and start the appropriate send loop."""
        settings = await db.get_all_settings()
        mode = settings.get("mode", "obo")
        delay_min = float(settings.get("delay_min", 3))
        delay_max = float(settings.get("delay_max", 7))
        autonomous_limit = int(settings.get("autonomous_limit", 0))

        accounts_rows = await db.get_accounts()
        channels_rows = await db.get_channels()
        text = await db.get_message_text()

        if not accounts_rows:
            log.error("No active accounts found. Add at least one account first.")
            return
        if not channels_rows:
            log.error("No channels found. Add at least one channel first.")
            return
        if not text.strip():
            log.error("Message text is empty. Set the text first.")
            return

        clients = [AccountClient(r) for r in accounts_rows]
        channels = [r["username"] for r in channels_rows]

        log.info("[bold cyan]Starting all clients…[/bold cyan]")
        for ac in clients:
            try:
                await ac.start()
            except Exception as e:
                log.error(f"Failed to start {ac.phone}: {e}")

        active = [c for c in clients if c.client and c.client.is_connected]
        if not active:
            log.error("No clients connected successfully. Aborting.")
            return

        self._stop_event.clear()

        deadline: Optional[float] = None
        if autonomous_limit > 0:
            deadline = time.monotonic() + autonomous_limit * 60
            log.info(
                f"[bold magenta]Autonomous mode:[/bold magenta] "
                f"will stop after [cyan]{autonomous_limit}[/cyan] minutes."
            )

        try:
            if mode == "obo":
                await self._loop_obo(active, channels, text, delay_min, delay_max, deadline)
            else:
                await self._loop_random(active, channels, text, delay_min, delay_max, deadline)
        finally:
            log.info("[bold]Stopping all clients…[/bold]")
            for ac in active:
                await ac.stop()

    def stop(self) -> None:
        """Signal the running loop to stop gracefully."""
        self._stop_event.set()

    def _check_deadline(self, deadline: Optional[float]) -> bool:
        """Return True if we should stop (deadline passed or stop requested)."""
        if self._stop_event.is_set():
            return True
        if deadline is not None and time.monotonic() >= deadline:
            log.info("[bold magenta]Autonomous time limit reached. Stopping.[/bold magenta]")
            return True
        return False

    async def _sleep_delay(self, delay_min: float, delay_max: float,
                           deadline: Optional[float]) -> bool:
        delay = random.uniform(delay_min, delay_max)
        log.info(f"[dim]Waiting {delay:.1f}s…[/dim]")
        end = time.monotonic() + delay
        while time.monotonic() < end:
            if self._check_deadline(deadline):
                return False
            await asyncio.sleep(0.5)
        return True

    async def _do_send(self, ac: AccountClient, channel: str, text: str) -> None:
        result = await ac.send_message(channel, text)
        log_send(ac.phone, channel, result, "" if result == "ok" else result)
        if result == "ok":
            await db.update_sent_count(ac.phone)

    async def _loop_obo(
        self,
        clients: list[AccountClient],
        channels: list[str],
        text: str,
        delay_min: float,
        delay_max: float,
        deadline: Optional[float],
    ) -> None:
        log.info("[bold green]Mode: One-By-One[/bold green]")
        while not self._check_deadline(deadline):
            for ac in clients:
                if self._check_deadline(deadline):
                    return
                for channel in channels:
                    if self._check_deadline(deadline):
                        return
                    await self._do_send(ac, channel, text)
                    if not await self._sleep_delay(delay_min, delay_max, deadline):
                        return

    async def _loop_random(
        self,
        clients: list[AccountClient],
        channels: list[str],
        text: str,
        delay_min: float,
        delay_max: float,
        deadline: Optional[float],
    ) -> None:
        log.info("[bold green]Mode: Random[/bold green]")
        prev_phone: Optional[str] = None
        prev_channel: Optional[str] = None

        while not self._check_deadline(deadline):

            if len(clients) > 1:
                pool = [c for c in clients if c.phone != prev_phone]
            else:
                pool = clients
            ac = random.choice(pool)

            if len(channels) > 1:
                ch_pool = [c for c in channels if c != prev_channel]
            else:
                ch_pool = channels
            channel = random.choice(ch_pool)

            prev_phone = ac.phone
            prev_channel = channel

            await self._do_send(ac, channel, text)

            if not await self._sleep_delay(delay_min, delay_max, deadline):
                return