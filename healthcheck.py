import asyncio
import os
import sys

import asyncpg

async def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    try:
        conn = await asyncpg.connect(dsn)
        await conn.close()
        print("ok")
        sys.exit(0)
    except Exception as e:
        print("db error:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
