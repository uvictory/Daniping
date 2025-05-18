#from PyInstaller.building.utils import add_suffix_to_extension
from fastapi import FastAPI, Request, Form  # FastAPI의 핵심 클래스들과 폼 데이터를 위한 Form 임포트
from fastapi.responses import HTMLResponse, RedirectResponse  # HTML 응답과 리다이렉트 응답 지원
from fastapi.staticfiles import StaticFiles  # 정적 파일 서빙을 위한 모듈
from fastapi.templating import Jinja2Templates  # Jinja2 템플릿을 FastAPI에 통합하기 위한 모듈
#from database import get_db_connection  # DB 연결을 위한 함수 (별도 모듈로 분리함)
from datetime import date, datetime  # 날짜 및 시간 처리를 위한 표준 모듈
import random  # 랜덤 선택을 위한 모듈
import aiosqlite  # SQLite의 비동기 버전 라이브러리
from fastapi import FastAPI
from database import init_db
import os
from contextlib import asynccontextmanager
# FastAPI 인스턴스 생성
app = FastAPI()

DB_PATH = "messages"

# assets 폴더 경로
ASSETS_DIR = "assets"


# assets 폴더 내의 파일 목록을 가져오는 함수
def get_file_list():
    # assets 폴더 내 모든 파일 리스트를 가져오고, 확장자를 제외한 파일명만 반환
    files = [os.path.splitext(f)[0] for f in os.listdir(ASSETS_DIR) if os.path.isfile(os.path.join(ASSETS_DIR, f))]
    return files


"""
@app.on_event("startup")
async def startup_event():
    await init_db()
"""
# lifespan 이벤트 핸들러 사용
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 처리할 코드
    print("서버 시작!")
    yield
    # 서버 종료 시 처리할 코드
    print("서버 종료!")

app = FastAPI(lifespan=lifespan)





# 정적 파일을 서빙할 디렉토리 설정 (예: CSS, JS, 이미지 등)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 디렉토리 설정
templates = Jinja2Templates(directory="templates")

"""
# 앱 시작 시 DB 초기화
@app.on_event("startup")
async def startup():
    await init_db()
"""
# 메인 폼 (문구 리스트 + 설정)
@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request, mode: str = "latest"):
    """
        관리자 페이지 GET 요청 처리
        - 오늘 날짜 기준의 문구들을 조회
        - 출력 모드와 함께 HTML 템플릿 렌더링
        """
    files = get_file_list()  # assets 폴더에서 파일 리스트 가져오기


    print("GET 요청 도착")  # 디버깅용 로그
    print("현재 DB 경로:", DB_PATH)
    today = date.today().isoformat()    #  오늘 날짜를 문자열로 가져옴

    # now 값과 DB 값의 포맷을 맞춰야 함
    now = datetime.now().strftime("%H:%M")

    async with aiosqlite.connect(DB_PATH) as db:  # 비동기 SQLite 연결
        # 문구 목록 조회 (현재 시간 기준 유효한 것만)
        cursor = await db.execute("""
        SELECT id, text, start_time, end_time FROM messages
        WHERE day=? AND (start_time IS NULL OR start_time <= ?)
        AND (end_time IS NULL OR end_time >= ?)
        """, (today, now, now))
        rows = await cursor.fetchall()  # 모든 메시지 행 가져오기

        # 메시지를 딕셔너리 형태로 변환하여 템플릿에 전달하기 쉽게 구성
        messages = [
            {"id": r[0], "text": r[1], "start_time": r[2], "end_time": r[3]}
            for r in rows
        ]

        # 현재 출력 모드 조회
        cursor = await db.execute("SELECT value FROM config WHERE key='mode'")
        mode_row = await cursor.fetchone()
        mode = mode_row[0] if mode_row else "latest"

    # 가장 최근 문구 선택 (없으면 기본 메시지 표시)
    selected = messages[-1]["text"] if messages else "오늘의 문구가 없습니다."

    # 템플릿 렌더링 및 전달할 변수들
    return templates.TemplateResponse("form.html", {
        "request": request,         # 필수: Jinja2 템플릿 내에서 request 객체 사용 가능하게 함
        "messages": messages,       #  오늘의 메시지 리스트
        "selected" : selected,      # 기본 선택된 메시지
        "mode" : mode,               # 현재 출력 모드
        "files": files  # 파일 리스트를 템플릿에 전달
    })

    # 문구 등록

# 문구 등록 엔드 포인트
@app.post("/submit_message", response_class=HTMLResponse)
async def submit_message(
        request: Request,
        message: str = Form(...),   #등록할 메시지
        msg_date: str = Form(None), # 메시지 날짜 (기본값: 오늘)
        start_time: str = Form(None),   # 예약 시작 시각
        end_time: str = Form(None)  # 예약 종료 시각
):
    msg_date = msg_date or date.today().isoformat() # 날짜가 없으면 오늘로 설정

    # 시작 시각과 종료 시각이 비어 있으면 기본값 설정
    if not start_time:
        start_time = "00:00"
    if not end_time:
        end_time = "23:59"


    async with aiosqlite.connect(DB_PATH) as db:
        # 문구 데이터 삽입
        await db.execute("""
        INSERT INTO messages (day, text, start_time, end_time)
        VALUES (?, ?, ?, ?)
        """, (msg_date, message, start_time, end_time))
        await db.commit()   # 변경사항 커밋

    return RedirectResponse("/",status_code=303)    # 등록 후 메인 페이지로 리다이렉트

# 문구 수정

# Post/ submit_behavior - 행동 정보 저장
@app.post("/submit_behavior")
async def submit_behavior(
        behavior_type: str = Form(...),     # 행동 타입 (IDLE, LEFT, RIGHT 등)
        file_name: str = Form(None)     # 행동 이름 (예: mask 등)
):
        now = datetime.now().isoformat()    # 현재 시각 ISO 형식 문자열로 저장

        # 비동기 SQLite 연결
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('type', ?)", (behavior_type,))

            # file_name이 있으면 그것을 'name'으로 저장
            if file_name:
                await db.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('name', ?)", (file_name,))

            # 'updated_at' 값 업데이트
            await db.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('updated_at', ?)", (now,))

            # 커밋
            await db.commit()
        # 저장 완료 후 리디렉션
        return RedirectResponse("/", status_code=303)

# POST /set_mode - 문구 출력 모드 저장
@app.post("/set_mode")
async def set_mode(mode: str = Form(...)):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('mode', ?)", (mode,))
        await db.commit()
    return RedirectResponse("/",status_code=303)

# ✅ 문구 수정
@app.post("/edit_message")
async def edit_message(id: int = Form(...), new_text: str = Form(...)):
    print(f"수정 요청: id={id}, new_text={new_text}")
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE messages SET text=? WHERE id=?", (new_text, id))
        await conn.commit()
    return RedirectResponse("/", status_code=303)

# ✅ 문구 삭제
@app.post("/delete_message")
async def delete_message(id: int = Form(...)):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM messages WHERE id=?", (id,))
        await conn.commit()
    return RedirectResponse("/", status_code=303)




# GET / mode  - 현재 출력 모드 조회
@app.get("/mode")
async def get_mode():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM config WHERE key='mode'")
        row = await cur.fetchone()
        return {"mode": row[0] if row else "latest"}

# GET/ behavior - 현재 행동 정보 조회
@app.get("/behavior")
async def get_behavior():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT key, value FROM behavior")
            rows = await cur.fetchall()

            # 키-값 딕셔너리로 변환
            data = {key: value for key, value in rows}
            print("📦 현재 behavior 설정:", data)

            return {
                "type": data.get("type", "IDLE"),
                "name": data.get("name", "default"),  # 이 부분이 이제 file_name을 의미
                "updated_at": data.get("updated_at", datetime.now().isoformat())
            }
    except Exception as e:
        print("행동 제공 실패: ", e)
        return {"type": "IDLE", "name": "default", "updated_at": datetime.now().isoformat()}



# ✅ 문구 요청 (유효 시간 기반 + 모드별 선택 + 만료 문구 자동 삭제)
@app.get("/message")
async def get_message():
    try:
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.time().strftime("%H:%M")

        async with aiosqlite.connect(DB_PATH) as conn:
            # ⛔️ 종료 시간이 지난 문구는 삭제
            await conn.execute("""
                DELETE FROM messages 
                WHERE end_time IS NOT NULL AND end_time < ?
            """, (current_time,))

            # 현재 출력 모드 가져오기
            async with conn.execute("SELECT value FROM config WHERE key='mode'") as cur:
                mode_row = await cur.fetchone()
                mode = mode_row[0] if mode_row else "random"

            # 유효한 시간대의 문구만 선택
            async with conn.execute("""
                SELECT id, text FROM messages
                WHERE day=?
                AND (start_time IS NULL OR start_time <= ?)
                AND (end_time IS NULL OR end_time >= ?)
            """, (today, current_time, current_time)) as cur:
                rows = await cur.fetchall()

            if not rows:
                return {"message": "default"}

            # 모드별 문구 선택
            if mode == "random":
                selected = random.choice(rows)[1]
            elif mode == "latest":
                selected = rows[-1][1]
            elif mode == "sequence":
                async with conn.execute("SELECT value FROM state WHERE key='sequence_index'") as cur:
                    row_idx = await cur.fetchone()
                    index = int(row_idx[0]) if row_idx else 0
                    if index >= len(rows):
                        index = 0
                    selected = rows[index][1]
                    next_index = (index + 1) % len(rows)
                    await conn.execute(
                        "INSERT OR REPLACE INTO state (key, value) VALUES ('sequence_index', ?)",
                        (str(next_index),)
                    )
            else:
                selected = "알 수 없는 모드입니다."

            await conn.commit()

        return {"message": selected}

    except Exception as e:
        print("🔥 서버 오류:", e)
        return {"message": f"⚠ 서버 오류 발생: {e}"}

