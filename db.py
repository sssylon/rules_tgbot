import asyncpg
import os
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# ensure .env is loaded when imported
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/rulesdb")

class DB:
    def __init__(self, dsn: str = DATABASE_URL):
        self.dsn = dsn
        self._pool: Optional[asyncpg.pool.Pool] = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(self.dsn, max_size=10)

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def init_db(self):
        sql_path = os.path.join(os.path.dirname(__file__), "migrations/init_db.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        # split and execute statements to be safe
        async with self._pool.acquire() as conn:
            for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                try:
                    await conn.execute(stmt)
                except Exception:
                    # ignore if already exists or not supported
                    pass
            # ensure columns exist (for upgrades)
            try:
                await conn.execute("ALTER TABLE chats ADD COLUMN IF NOT EXISTS non_bot_members INTEGER")
            except Exception:
                pass
            try:
                await conn.execute("ALTER TABLE chats ADD COLUMN IF NOT EXISTS bot_count INTEGER DEFAULT 1")
            except Exception:
                pass

    async def execute(self, query: str, *params):
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *params)

    async def fetchone(self, query: str, *params):
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *params)

    async def fetchall(self, query: str, *params):
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *params)

    # helper methods
    async def set_rules_message(self, chat_id: int, message_id: int):
        await self.execute(
            "INSERT INTO chats(chat_id, rules_message_id) VALUES ($1, $2) ON CONFLICT (chat_id) DO UPDATE SET rules_message_id = EXCLUDED.rules_message_id",
            chat_id,
            message_id,
        )

    async def get_rules_message(self, chat_id: int) -> Optional[int]:
        row = await self.fetchone("SELECT rules_message_id FROM chats WHERE chat_id = $1", chat_id)
        return row[0] if row else None

    async def create_rule(self, chat_id: int, text: str) -> int:
        ts = int(time.time())
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("INSERT INTO rules(chat_id, text, created_at) VALUES ($1, $2, $3) RETURNING id", chat_id, text, ts)
            return row[0]

    async def accept_rule(self, rule_id: int):
        ts = int(time.time())
        await self.execute("UPDATE rules SET accepted_at = $1 WHERE id = $2", ts, rule_id)

    async def create_vote(self, rule_id: int, chat_id: int, vote_message_id: Optional[int] = None) -> int:
        ts = int(time.time())
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO votes(rule_id, chat_id, vote_message_id, created_at, active) VALUES ($1, $2, $3, $4, 1) RETURNING id",
                rule_id,
                chat_id,
                vote_message_id,
                ts,
            )
            return row[0]

    async def set_vote_message(self, vote_id: int, message_id: int):
        await self.execute("UPDATE votes SET vote_message_id = $1 WHERE id = $2", message_id, vote_id)

    async def close_vote(self, vote_id: int):
        await self.execute("UPDATE votes SET active = 0 WHERE id = $1", vote_id)

    async def get_active_votes(self) -> List[Dict[str, Any]]:
        rows = await self.fetchall("SELECT id, rule_id, chat_id, vote_message_id, created_at FROM votes WHERE active = 1")
        return [dict(r) for r in rows]

    async def add_or_update_vote(self, vote_id: int, user_id: int, username: Optional[str], display_name: str, choice: str):
        ts = int(time.time())
        await self.execute(
            "INSERT INTO vote_voters(vote_id, user_id, username, display_name, choice, voted_at) VALUES ($1, $2, $3, $4, $5, $6) "
            "ON CONFLICT (vote_id, user_id) DO UPDATE SET choice = EXCLUDED.choice, voted_at = EXCLUDED.voted_at, username = EXCLUDED.username, display_name = EXCLUDED.display_name",
            vote_id,
            user_id,
            username,
            display_name,
            choice,
            ts,
        )

    async def get_vote_counts(self, vote_id: int):
        row_yes = await self.fetchone("SELECT COUNT(*) FROM vote_voters WHERE vote_id = $1 AND choice = 'yes'", vote_id)
        row_no = await self.fetchone("SELECT COUNT(*) FROM vote_voters WHERE vote_id = $1 AND choice = 'no'", vote_id)
        return (int(row_yes[0]) if row_yes else 0, int(row_no[0]) if row_no else 0)

    async def get_voters_lists(self, vote_id: int, limit: int = 50):
        rows_yes = await self.fetchall(
            "SELECT user_id, username, display_name FROM vote_voters WHERE vote_id = $1 AND choice = 'yes' ORDER BY voted_at DESC LIMIT $2",
            vote_id,
            limit,
        )
        rows_no = await self.fetchall(
            "SELECT user_id, username, display_name FROM vote_voters WHERE vote_id = $1 AND choice = 'no' ORDER BY voted_at DESC LIMIT $2",
            vote_id,
            limit,
        )
        return rows_yes, rows_no

    async def get_vote(self, vote_id: int):
        row = await self.fetchone("SELECT id, rule_id, chat_id, vote_message_id, created_at, active FROM votes WHERE id = $1", vote_id)
        return dict(row) if row else None

    async def get_accepted_rules(self, chat_id: int):
        rows = await self.fetchall("SELECT text FROM rules WHERE chat_id = $1 AND accepted_at IS NOT NULL ORDER BY accepted_at", chat_id)
        return [r[0] for r in rows]

    async def get_accepted_rules_with_ids(self, chat_id: int):
        rows = await self.fetchall("SELECT id, text FROM rules WHERE chat_id = $1 AND accepted_at IS NOT NULL ORDER BY accepted_at", chat_id)
        return [(r[0], r[1]) for r in rows]

    async def add_accepted_rule(self, chat_id: int, text: str):
        ts = int(time.time())
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("INSERT INTO rules(chat_id, text, created_at, accepted_at) VALUES ($1, $2, $3, $4) RETURNING id", chat_id, text, ts, ts)
            return row[0]

    async def delete_rule_by_id(self, rule_id: int):
        await self.execute("DELETE FROM rules WHERE id = $1", rule_id)

    async def update_rule_text(self, rule_id: int, new_text: str):
        await self.execute("UPDATE rules SET text = $1 WHERE id = $2", new_text, rule_id)

    async def set_non_bot_members(self, chat_id: int, count: int):
        await self.execute("INSERT INTO chats(chat_id, non_bot_members) VALUES ($1, $2) ON CONFLICT (chat_id) DO UPDATE SET non_bot_members = EXCLUDED.non_bot_members", chat_id, count)

    async def get_non_bot_members(self, chat_id: int) -> Optional[int]:
        row = await self.fetchone("SELECT non_bot_members FROM chats WHERE chat_id = $1", chat_id)
        return int(row[0]) if row and row[0] is not None else None

    async def incr_non_bot_members(self, chat_id: int, delta: int = 1):
        current = await self.get_non_bot_members(chat_id)
        if current is None:
            current = 0
        new = max(0, current + delta)
        await self.set_non_bot_members(chat_id, new)
        return new

    async def set_bot_count(self, chat_id: int, count: int):
        await self.execute("INSERT INTO chats(chat_id, bot_count) VALUES ($1, $2) ON CONFLICT (chat_id) DO UPDATE SET bot_count = EXCLUDED.bot_count", chat_id, count)

    async def get_bot_count(self, chat_id: int) -> int:
        row = await self.fetchone("SELECT bot_count FROM chats WHERE chat_id = $1", chat_id)
        if row and row[0] is not None:
            return int(row[0])
        # default to 1
        return 1


# module-level DB instance for simple access from handlers
db = DB()