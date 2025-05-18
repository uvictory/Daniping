
import os
import sys
import zipfile
import shutil
import urllib.request
import subprocess
import time
import socket
import winreg

# 🔗 서버 주소 설정
SERVER_URL = "http://192.168.1.11:30007"
VERSION_URL = f"{SERVER_URL}/static/version.txt"      # 서버에 저장된 최신 버전 정보
ZIP_URL = f"{SERVER_URL}/static/Dani.zip"             # 배포용 zip 파일 위치

# 📁 로컬 저장 경로 설정
LOCAL_DIR = os.path.join(os.path.expanduser("~"), "DaniApp")  # Dani 저장 위치 (예: C:/Users/사용자/DaniApp)
LOCAL_VERSION_PATH = os.path.join(LOCAL_DIR, "version.txt")   # 로컬 버전 정보 경로
ZIP_PATH = os.path.join(LOCAL_DIR, "Dani.zip")                # 다운로드된 zip 파일 경로


# 🌐 인터넷 연결 확인 함수
def is_internet_available(timeout=3):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False

# ⏳ 인터넷 연결 대기 함수 (최대 max_wait초 동안 interval초 간격으로 재시도)
def wait_for_internet(max_wait=600, interval=10):
    waited = 0
    while waited < max_wait:
        if is_internet_available():
            return True
        time.sleep(interval)
        waited += interval
    return False

# 🌐 서버에서 최신 버전 정보 가져오기
def get_remote_version():
    try:
        with urllib.request.urlopen(VERSION_URL) as response:
            return response.read().decode("utf-8").strip()
    except Exception as e:
        print(f"❌ 버전 확인 실패: {e}")
        return None

# 💾 로컬에서 현재 버전 읽기
def get_local_version():
    if not os.path.exists(LOCAL_VERSION_PATH):
        return None
    with open(LOCAL_VERSION_PATH, "r") as f:
        return f.read().strip()

# 🔄 서버와 버전 비교 후 필요 시 업데이트 실행
def update_if_needed():
    remote_version = get_remote_version()
    local_version = get_local_version()

    print(f"🔍 서버 버전: {remote_version}, 로컬 버전: {local_version}")
    if remote_version and remote_version != local_version:
        print("⬇️ 업데이트 필요 → 다운로드 중...")
        try:
            os.makedirs(LOCAL_DIR, exist_ok=True)

            # Dani.zip 다운로드
            urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)

            # 압축 해제
            with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
                zip_ref.extractall(LOCAL_DIR)

            # 버전 정보 저장
            with open(LOCAL_VERSION_PATH, "w") as f:
                f.write(remote_version)

            print("✅ 업데이트 완료")
        except Exception as e:
            print(f"❌ 업데이트 실패: {e}")
    else:
        print("✅ 최신 버전입니다.")

    # 🎯 Dani 실행
    exe_path = os.path.join(LOCAL_DIR, "Dani.exe")
    if os.path.exists(exe_path):
        subprocess.Popen([exe_path])  # 백그라운드 실행
        print("🚀 Dani 실행됨")
    else:
        print("❌ Dani.exe가 존재하지 않습니다.")

# 🪛 윈도우 시작 시 자동 실행 등록 함수
def register_startup():
    exe_path = os.path.abspath(sys.argv[0])  # 현재 실행 중인 런처 경로
    reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "DaniUpdater"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                # 기존에 등록된 값이 같으면 재등록 안 함
                current_value, _ = winreg.QueryValueEx(key, app_name)
                if current_value == exe_path:
                    return
            except FileNotFoundError:
                pass  # 최초 등록

            # 자동 실행 경로 등록
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            print("✅ 시작 프로그램 등록 완료")
    except Exception as e:
        print(f"❌ 자동 실행 등록 실패: {e}")

# 🚀 프로그램 진입점
if __name__ == "__main__":
    register_startup()  # 시작 프로그램 등록
    if wait_for_internet():  # 인터넷 대기 후
        update_if_needed()   # 업데이트 체크 및 실행
    else:
        print("❌ 인터넷 연결 실패. Dani 실행 생략")