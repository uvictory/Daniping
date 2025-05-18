import asyncio  # 비동기 처리(이벤트 루프, 태스크 등)를 위한 기본 모듈
import os
import websockets
import json
import logging
import socket

LOG_FILE = "notify_log.jsonl"  # 알림 로그 파일

def save_notify_log(data):
    try:
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", LOG_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        print("로그 저장 실패:", e)

# ⛔ websockets 내부 로깅을 끄기
logging.getLogger('websockets.server').setLevel(logging.CRITICAL)

# 🔌 연결된 클라이언트 저장
connected_clients = {}  # ✅ ip → websocket 형태의 딕셔너리

async def handler(websocket):
    peername = websocket.remote_address
    client_id = f"{peername[0]}:{peername[1]}" if peername else "unknown"

    connected_clients[client_id] = websocket
    print(f"✅ 클라이언트 접속: {client_id}")

    try:
        async for message in websocket:
            print(f"📩 수신 메시지: {message}")
            try:
                data = json.loads(message)
                save_notify_log(data)

            except Exception as e:
                print(f"❌ 처리 오류: {e}")
    except websockets.exceptions.ConnectionClosed:
        print(f"🔴 연결 종료됨: {client_id}")
    finally:
        if connected_clients.get(client_id) == websocket:
            del connected_clients[client_id]
            print(f"🧹 연결 제거 완료: {client_id}")

async def main():
    print("🚀 서버 실행 중: ws://0.0.0.0:9090")
    async with websockets.serve(handler, "0.0.0.0", 9090):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
