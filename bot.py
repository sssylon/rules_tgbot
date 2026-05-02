import asyncio
import logging
import os
from dotenv import load_dotenv

# load .env early so environment variables are available to modules
load_dotenv()

from aiogram import Bot, Dispatcher
from db import db
from handlers import admin, members, vote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN env var required. Create a .env with BOT_TOKEN or set the environment variable.")
    bot = Bot(TOKEN)
    dp = Dispatcher()

    # use module-level db instance
    await db.connect()
    await db.init_db()

    # include routers
    dp.include_router(admin.router)
    dp.include_router(vote.router)
    dp.include_router(members.router)

    # start scheduling existing votes
    active_votes = await db.get_active_votes()
    for v in active_votes:
        vote_id = v['id']
        created_at = v['created_at']
        # schedule close tasks
        asyncio.create_task(vote.schedule_close(vote_id, created_at, bot))

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
