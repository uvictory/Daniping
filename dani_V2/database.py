import aiosqlite
import asyncio

from datetime import datetime
# 데이터베이스 파일명 (전체 프로젝트에서 사용할 db  경로를 고정해둠)
import os

# 현재 파일 기준으로 db 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "messages.db")

# DB 초기화 함수 (앱 시작 시 호출)
async def init_db():
    """
    메시지, 설정, 상태, 행동 테이블을 생성합니다.
    각 테이블은 존재하지 않을 경우에만 생성됩니다.
    :return:
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # 메시지 테이블: 메시지 내용 + 시작/종료 시간 설정
        await db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        day TEXT NOT NULL,
                        text TEXT NOT NULL,
                        start_time TEXT,
                        end_time TEXT
                    );
                """)
        # 설정 테이블: 모드 설정 등 key-value 형식의 구성
        await db.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                """)

        # 행동 테이블: 다니의 상태를 저장하는 테이블
        await db.execute("""
                    CREATE TABLE IF NOT EXISTS behavior (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                """)
        # 상태 테이블: 순차 출력 모드를 위한 인덱스 값 저장용
        await db.execute("""
                    CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                """)

        await db.commit()    # 변경 사항 저장


