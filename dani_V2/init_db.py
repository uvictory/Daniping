# init_db.py
import aiosqlite
import asyncio
import os

DB_PATH = "messages"

async def init():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # 기존 DB 삭제



    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            text TEXT,
            start_time TEXT,
            end_time TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS behavior (
    key TEXT PRIMARY KEY,  -- 'key'를 PRIMARY KEY로 설정
    value TEXT
)
        """)
        await db.execute("""
        CREATE TABLE state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.commit()
        print("✅ DB 및 테이블 초기화 완료")

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("PRAGMA table_info(behavior);")
            columns = await cursor.fetchall()
            print("behavior 테이블 컬럼:", columns)

asyncio.run(init())
