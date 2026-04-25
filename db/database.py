import aiosqlite
import os

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "nesadata.db")
)

async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db() -> None:
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                phone       TEXT UNIQUE NOT NULL,
                api_id      INTEGER NOT NULL,
                api_hash    TEXT NOT NULL,
                session     TEXT NOT NULL,
                proxy       TEXT DEFAULT NULL,
                sent_count  INTEGER DEFAULT 0,
                active      INTEGER DEFAULT 1,
                status      TEXT DEFAULT 'Unknown'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_text (
                id   INTEGER PRIMARY KEY CHECK (id = 1),
                body TEXT NOT NULL DEFAULT ''
            )
        """)

        defaults = [
            ("delay_min", "3"),
            ("delay_max", "7"),
            ("mode", "obo"),
            ("autonomous_limit", "0"),
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", defaults
        )

        await db.execute(
            "INSERT OR IGNORE INTO message_text (id, body) VALUES (1, '')"
        )


        try:
            async with db.execute("SELECT status FROM accounts LIMIT 1") as cur:
                await cur.fetchone()
        except aiosqlite.OperationalError:

            await db.execute("ALTER TABLE accounts ADD COLUMN status TEXT DEFAULT 'Unknown'")

        await db.commit()

async def add_account(phone: str, api_id: int, api_hash: str,
                      session: str, proxy: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO accounts
               (phone, api_id, api_hash, session, proxy)
               VALUES (?, ?, ?, ?, ?)""",
            (phone, api_id, api_hash, session, proxy),
        )
        await db.commit()

async def get_accounts() -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM accounts WHERE active = 1 ORDER BY id"
        ) as cur:
            return await cur.fetchall()

async def update_sent_count(phone: str, increment: int = 1) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET sent_count = sent_count + ? WHERE phone = ?",
            (increment, phone),
        )
        await db.commit()

async def set_account_proxy(phone: str, proxy: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET proxy = ? WHERE phone = ?", (proxy, phone)
        )
        await db.commit()

async def remove_account(phone: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
        await db.commit()

async def update_account_status(phone: str, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET status = ? WHERE phone = ?", (status, phone)
        )
        await db.commit()

async def add_channel(username: str) -> None:
    username = username.lstrip("@").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,)
        )
        await db.commit()

async def get_channels() -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels ORDER BY id") as cur:
            return await cur.fetchall()

async def remove_channel(username: str) -> None:
    username = username.lstrip("@").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE username = ?", (username,))
        await db.commit()

async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row["value"] if row else None

async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()

async def get_all_settings() -> dict[str, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
            return {r["key"]: r["value"] for r in rows}

async def get_message_text() -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT body FROM message_text WHERE id = 1") as cur:
            row = await cur.fetchone()
            return row["body"] if row else ""

async def set_message_text(body: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO message_text (id, body) VALUES (1, ?)", (body,)
        )
        await db.commit()