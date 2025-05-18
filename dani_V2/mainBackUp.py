from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import date, datetime
import random

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def form_get(request: Request, mode: str = "latest"):
    """
        관리자 페이지 GET 요청 처리
        - 오늘 날짜 기준의 문구들을 조회
        - 출력 모드와 함께 HTML 템플릿 렌더링
        """
    print("GET 요청 도착")  # 디버깅용 로그

    today = str(date.today())  # 오늘 날짜 (문자열)로 변환

    # SQLite DB 연결
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()

    # ✅ 오늘의 메시지들 조회 (예약 시간도 포함)
    cur.execute("SELECT id, text, start_time, end_time FROM messages WHERE day=?", (today,))
    rows = cur.fetchall()

    # 메시지를 리스트 딕셔너리로 변환
    # 템플릿에서 쉽게 사용하기 위해 {"id": 1, "text": "...", "reserved_at": "..."} 형태로 구성
    messages = [
        {"id": row[0], "text": row[1], "start_time": row[2], "end_time": row[3]}
        for row in rows
    ]

    # ✅ 현재 출력 모드 조회
    cur.execute("SELECT value FROM config WHERE key='mode'")
    mode_row = cur.fetchone()
    mode = mode_row[0] if mode_row else "random"

    conn.close()  # db 연결 닫기

    # ✅ 템플릿에 전달할 데이터들
    selected = messages[-1]["text"] if messages else "오늘의 문구가 없습니다."

    # 템플릿에 전달할 변수들 구성해서 렌더링
    return templates.TemplateResponse("form.html", {
        "request": request,  # Jinja2 템플릿에서 사용 가능하게 전달
        "messages": messages,  # 오늘의 문구 리스트
        "selected": selected,  # 화면에 표시할 문구 하나
        "mode": mode  # 현재 선택된 출력 모드
    })


@app.post("/submit_message", response_class=HTMLResponse)
def submit_message(
        message: str = Form(...),
        msg_date: str = Form(None),
        start_time: str = Form(None),
        end_time: str = Form(None),

):
    print("message:", message)
    print("msg_date:", msg_date)
    print("start_time:", start_time)
    print("end_time:", end_time)
    msg_date = msg_date or str(date.today())
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("""
            INSERT INTO messages (day, text, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (msg_date, message, start_time, end_time))
    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)


@app.post("/submit_behavior", response_class=HTMLResponse)
def submit_behavior(
        behavior_type: str = Form(...),
        behavior_name: str = Form(None)
):
    now = datetime.now().isoformat()
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('type', ?)", (behavior_type,))
    if behavior_name:
        cur.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('name', ?)", (behavior_name,))
    cur.execute("INSERT OR REPLACE INTO behavior (key, value) VALUES ('updated_at', ?)", (now,))
    conn.commit()
    conn.close()
    print("✅ 행동 저장:", behavior_type, behavior_name)
    return RedirectResponse("/", status_code=303)


@app.post("/set_mode")
def set_mode(mode: str = Form(...)):
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('mode', ?)", (mode,))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)


@app.post("/edit_message")
def edit_message(id: int = Form(...), new_text: str = Form(...)):
    print(f"수정 요청: id={id}, new_text={new_text}")
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("UPDATE messages SET text=? WHERE id=?", (new_text, id))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)


@app.post("/delete_message")
def delete_message(id: int = Form(...)):
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)


@app.get("/mode")
def get_mode():
    conn = sqlite3.connect("messages.db")
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key='mode'")
    row = cur.fetchone()
    conn.close()
    return {"mode": row[0] if row else "random"}


@app.get("/behavior")
def get_behavior():
    try:
        conn = sqlite3.connect("messages.db")
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM behavior")
        rows = cur.fetchall()
        conn.close()
        data = {key: value for key, value in rows}
        print("📦 현재 behavior 설정:", data)
        return {
            "type": data.get("type", "IDLE"),
            "name": data.get("name", "default"),
            "updated_at": data.get("updated_at", datetime.now().isoformat())
        }
    except Exception as e:
        print("❌ 행동 제공 실패:", e)
        return {"type": "IDLE", "name": "default", "updated_at": datetime.now().isoformat()}


@app.get("/message")
def get_message():
    try:
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.time().strftime("%H:%M")

        conn = sqlite3.connect("messages.db")
        cur = conn.cursor()

        cur.execute("SELECT value FROM config WHERE key='mode'")
        mode_row = cur.fetchone()
        mode = mode_row[0] if mode_row else "random"

        # 현재 시간 기준 유효한 문구만 선택
        cur.execute("""
                    SELECT id, text FROM messages
                    WHERE day=?
                    AND (start_time IS NULL OR start_time <= ?)
                    AND (end_time IS NULL OR end_time >= ?)
                """, (today, current_time, current_time))
        rows = cur.fetchall()
        if not rows:
            return {"message": "오늘의 문구가 없어요!"}
        if mode == "random":
            selected = random.choice(rows)[1]
        elif mode == "latest":
            selected = rows[-1][1]
        elif mode == "sequence":
            cur.execute("SELECT value FROM state WHERE key='sequence_index'")
            row_idx = cur.fetchone()
            index = int(row_idx[0]) if row_idx else 0
            if index >= len(rows):
                index = 0
            selected = rows[index][1]
            next_index = (index + 1) % len(rows)
            cur.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('sequence_index', ?)", (str(next_index),))
        else:
            selected = "알 수 없는 모드입니다."
        conn.commit()
        conn.close()
        return {"message": selected}
    except Exception as e:
        print("🔥 서버 오류:", e)
        return {"message": f"⚠ 서버 오류 발생: {e}"}
