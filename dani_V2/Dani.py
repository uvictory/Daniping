import asyncio

from PyQt5.QtCore import QObject, pyqtSlot, QUrl, QTimer, QEvent, QPropertyAnimation, pyqtSignal, QPoint
from PyQt5.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5 import QtWidgets, QtGui, QtCore, QtWebEngineWidgets
from PyQt5.QtGui import QFontDatabase, QFont, QIcon, QPixmap, QFontMetrics
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineScript
import sys, requests
import random, psutil
import time
import socket
from openai import timeout
from pynput import mouse, keyboard
import datetime
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from qasync import QEventLoop
import asyncio
import websockets
import json
import subprocess
import os
from dani_secom import BrowserWindow
from autologin import AutoLogin

def is_already_running():
    """다른 인스턴스가 포트 9999를 사용 중인지 확인"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("localhost", 9999))  # 사용 가능하면 바인딩됨
        s.close()
        return False  # 다른 인스턴스 없음
    except OSError:
        return True  # 이미 사용 중 (다른 다니 실행 중)

class MemoryMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("메모리 사용량 모니터")
        self.setGeometry(100, 100, 250, 100)

        self.label = QLabel("메모리 사용량 측정 중...", self)
        self.label.setStyleSheet("font-size: 14px; color: green;")

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # 타이머로 주기적으로 업데이트
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_memory_usage)
        self.timer.start(1000)  # 1초마다 측정

    def update_memory_usage(self):
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / (1024 * 1024)  # MB 단위
        self.label.setText(f"현재 메모리 사용량: {mem:.2f} MB")

# 다니 숨기기 플래그
dani_hide = False

# 메시지 팝업 주기
msg_timer = 24000   #24초
hide_time = 4000   # 말풍선 디스플레이 시간 - 4초
server = "http://localhost:30000"

try:
    res = requests.get(f"{server}/message?mode=random")

    print("✅ 상태 코드:", res.status_code)
    print("✅ 응답 본문:", res.text)
except:
    print("서버 통신 x")

# 기본 시간대별 값 설정
DEFAULT_GIF = {
    "00:00-10:00": "assets/coffee.gif",   # 오전 8-10 기본 gif
    "10:00-11:30": "assets/work.gif",
    "11:30-13:00": "assets/lunch.gif",
    "13:00-16:00": "assets/work.gif",
    "16:00-18:00": "assets/study.gif",
    "18:00-24:00": "assets/home.gif",
}

DEFAULT_MESSAGE = {
    "8:00-10:00": "좋은 아침입니다!☀️",
    "10:00-11:30": "집중 근무 시간입니다. 힘내십시오!☕",
    "11:30-13:00": "벌써 점심 시간이네요! 메뉴는 무엇인가요?🍱",
    "13:00-14:00": "점심 먹고 졸릴 땐 스트레칭 한 번 해볼까요?🤸‍♂️",
    "14:00-15:00": "오후 업무 스타트!",
    "15:00-16:00": "슬슬 피곤해질 시간… 간식 타임 어때요?🍪",
    "16:00-17:00": 	"오늘 하루도 거의 다 왔어요!",
    "17:00-18:00": "마무리 정리 타임! 오늘도 고생 많았어요😊",
    "18:00-22:00": "퇴근 시간이에요~ 오늘도 수고 많으셨습니다!🏡"
}

# resource_path() 함수 추가
def resource_path(relative_path):
    """PyInstaller 실행환경과 개발환경 모두에서 리소스를 불러올 수 있도록 경로 보정"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 실행 중일 때 생성되는 임시 폴더
    except Exception:
        base_path = os.path.abspath(".")  # 개발환경에서는 현재 경로 기준

    return os.path.join(base_path, relative_path)

def apply_default_font(font_path):
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            default_font = QFont(families[0], 10)  # 글꼴 이름과 크기 지정
            QtWidgets.QApplication.setFont(default_font)
            print(f"🖋️ 기본 폰트 적용됨: {families[0]}")
        else:
            print("❌ 적용 가능한 폰트 패밀리 없음")
    else:
        print(f"❌ 폰트 로드 실패: {font_path}")

SETTINGS_FILE = resource_path("dani_settings.json")
CONFIG_FILE = resource_path("credentials.json")

# 서버와 통신이 안되거나 문구가 없을 경우 메시지를 받아오는 함수
def get_default_message_and_gif():
    # 현재 시간
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute

    gif = DEFAULT_GIF["13:00-16:00"]

    # 시간대에 맞는 기본 메시지 및 GIF 선택
    if 7 <= hour < 10:
        message = DEFAULT_MESSAGE["8:00-10:00"]
        gif = DEFAULT_GIF["00:00-10:00"]
    elif 10 <= hour < 11 or (hour == 10 and minute <= 30):
        message = DEFAULT_MESSAGE["10:00-11:30"]
        gif = DEFAULT_GIF["10:00-11:30"]
    elif 11 <= hour < 13 or (hour == 11 and minute <= 30):
        message = DEFAULT_MESSAGE["11:30-13:00"]
        gif = DEFAULT_GIF["11:30-13:00"]
    elif 13 <= hour < 14:
        message = DEFAULT_MESSAGE["13:00-14:00"]
        gif = DEFAULT_GIF["13:00-16:00"]
    elif 14 <= hour < 15:
        message = DEFAULT_MESSAGE["14:00-15:00"]
        gif = DEFAULT_GIF["13:00-16:00"]
    elif 15 <= hour < 16:
        message = DEFAULT_MESSAGE["15:00-16:00"]
        gif = DEFAULT_GIF["13:00-16:00"]
    elif 16 <= hour < 17:
        message = DEFAULT_MESSAGE["16:00-17:00"]
        gif = DEFAULT_GIF["16:00-18:00"]
    elif 17 <= hour < 18:
        message = DEFAULT_MESSAGE["17:00-18:00"]
        gif = DEFAULT_GIF["16:00-18:00"]
    elif 18 <= hour < 22:
        message = DEFAULT_MESSAGE["18:00-22:00"]
        gif = DEFAULT_GIF["18:00-24:00"]
    else:
        # 기본 메시지 (밤 시간대)
        message = "지금은 잘 시간이네요."
        gif = "assets/sleepMoveVer.gif"

    return message, gif

# 서버에서 오늘의 랜덤 메세지를 받아오는 함수
def get_random_message():
    try:
        # 현재 모드 가져오기
        mode_res = requests.get(f"{server}/mode", timeout=5)
        mode = mode_res.json().get("mode", "random")
        print("mode=", mode)

        # mode에 따라 메시지 요청
        res = requests.get(f"{server}/message?mode={mode}", timeout=5)
        default_msg, _ = get_default_message_and_gif()
        msg = res.json().get("message", default_msg)
        if msg == "default":
            msg = default_msg
        print("messge =",msg)
        return msg
    except Exception as e:
        print(f"서버 연결 실패,")  # 예외 출력
        msg, _ = get_default_message_and_gif()
        return msg
"""
class NotifyBridge(QObject):
    def __init__(self, dani_instance):
        super().__init__()
        self.dani = dani_instance
        
    @pyqtSlot(str)
    def receiveNotification(self, message):
        print("📢 새로운 알림 수신:", message)
        #self.show_balloon(message)
"""
class NotifyBridge(QObject):
    @pyqtSlot(str)
    def receiveNotification(self, msg):
        try:
            print("📥 수신된 알림:", msg)
            dani.show_balloon(msg)  # 실제 표시

        except Exception as e:
            print("알림 처리 중 오류:", e)


class TestWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dani 내장 알림 후킹 테스트")
        layout = QVBoxLayout(self)

        # 1. webView 생성
        self.view = QWebEngineView()
        layout.addWidget(self.view)


        # 개발자 도구 창 별도로 열기
        self.devtools = QWebEngineView()
        self.view.page().setDevToolsPage(self.devtools.page())
        self.devtools.resize(800, 600)
        self.devtools.show()

        self.view.load(QUrl("http://192.168.50.3:10000/index.jsp"))

        # 페이지 로딩 완료 시, 로그인 수행
        self.view.loadFinished.connect(lambda ok: QTimer.singleShot(3000, self.perform_login))

        # 페이지 로딩 완료 시마다 URL 검사
        self.view.loadFinished.connect(self.check_and_inject)

class GlobalActivityMonitor:
    def __init__(self, dani):
        self.dani = dani
        self.last_input_time = time.time()

        # 마우스 리스너 시작
        self.mouse_listener = mouse.Listener(on_move=self.on_input, on_click=self.on_input)
        self.mouse_listener.start()

        # 키보드 리스너 시작
        self.keyboard_listener = keyboard.Listener(on_press=self.on_input)
        self.keyboard_listener.start()
        """
        # 타이머 스레드 실행
        self.check_thread = threading.Thread(target=self.inactivity_checker)
        self.check_thread_daemon = True
        #self.check_thread.start()
        """
    def on_input(self, *args, **kwargs):
        self.last_input_time = time.time()
        self.dani.reset_inactivity_timer()  # 다니 객체에게 알려줌
"""
    def inactivity_checker(self):

        while True:
            if time.time() - self.last_input_time > 5:
                print(" 잠수 30초 지남")
                self.dani.go_to_sleep()
            time.sleep(1)
"""


class FancyBalloon(QtWidgets.QWidget):

    def __init__(self, dani, parent=None):
        super().__init__(parent)
        self.dani = dani
        self.fixed = False  # 고정 여부
        # 창 속성 설정: 항상 위 + 투명 배경 + 독립 툴 창
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.balloon.setFocusPolicy(QtCore.Qt.NoFocus)  # 위젯 자체가 포커스 받지 않게 설정
        # self.balloon.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        # 말풍선 내용 전체를 감싸는 컨테이너 프레임 (흰 배경, 둥근 테두리)
        self.container = QtWidgets.QFrame(self)
        self.container.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border-radius: 15px;
}                       margin-top: 0px; /* 상단 여백 없앰 */
                """)
        # 상단 바 (배경 + 텍스트 + 닫기 버튼)
        self.header_frame = QtWidgets.QFrame(self.container)
        self.header_frame.setStyleSheet("""
                                        background-color: #fdf1dd;
                                        border-bottom-left-radius: 0px;
                                        border-bottom-right-radius: 0px;
                                         border: none;
                                         margin-top: 0px; /* 헤더 여백 제거 */
        """)

        header_layout = QtWidgets.QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)  # 여백 설정 (상단 여백을 줄임)
        self.header_frame.setFixedHeight(40)  # 높이 고정 (원하는 높이로 조정 가능)

        # 제목 라벨
        self.title = QtWidgets.QLabel("🏠 중구시설관리공단 알리미")
        font_path = resource_path("fonts/NanumSquareRoundR.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        font_families = QFontDatabase.applicationFontFamilies(font_id)

        if font_families:
            font = QFont(font_families[0], 11)  # 제목 글씨크기 조절은 이걸로
            self.title.setFont(font)
        self.title.setStyleSheet("""
                    font-weight: bold;
                    font-size: 14px;
                    color: #333;
                    # font-family: '맑은 고딕', 'Noto Sans KR', sans-serif;

                """)

        font_path = resource_path("fonts/NanumSquareRoundR.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        font_families = QFontDatabase.applicationFontFamilies(font_id)

        if font_families:
            font = QFont(font_families[0], 11)  # 제목 글씨크기 조절은 이걸로
            self.title.setFont(font)

        # 📌 핀 버튼
        self.pin_button = QtWidgets.QPushButton(self)
        self.pin_button.setFixedSize(20, 20)
        self.pin_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
        """)
        self.pin_button.setIcon(QtGui.QIcon(resource_path("images/unlocked.png")))  # 초기 상태 아이콘
        self.pin_button.setIconSize(QtCore.QSize(16, 16))  # 아이콘 크기 조절
        self.pin_button.clicked.connect(self.toggle_pin)

        # 닫기 버튼 (말풍선 우측 상단 )
        self.close_btn = QtWidgets.QPushButton()
        icon_path = resource_path("images/close.png")  # 닫기 이미지 불러오기
        icon = QtGui.QIcon(QtGui.QPixmap(icon_path))
        self.close_btn.setIcon(icon)
        self.close_btn.setIconSize(QtCore.QSize(16, 16))  # 닫기 이미지 사이즈 조절

        self.close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: transparent;
            }
        """)

        # self.close_btn.setAutoFillBackground(True)

        self.close_btn.clicked.connect(self.hide_balloon)  # 닫기 버튼 클릭 시 hide 함수 호출
        # self.close_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # self.close_btn.clicked.connect(lambda: print("닫기 버튼 눌림") or self.hide())

        header_layout.addWidget(self.title)
        header_layout.addWidget(self.pin_button)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)

        # 메시지 라벨 (서버에서 받은 내용)
        self.message = QtWidgets.QLabel()

        font_path = resource_path("fonts/NanumSquareRoundR.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        font_families = QFontDatabase.applicationFontFamilies(font_id)

        if font_families:
            font = QFont(font_families[0], 11)  # 메시지 박스 안의 글씨크기 조절은 이걸로
            self.message.setFont(font)

        self.message.setStyleSheet("""
                    color: black;
                    background: transparent;
                    # font-family: '맑은 고딕', 'Noto Sans KR', sans-serif;
                    line-height: 1.5; /* 메시지 간 간격 설정 */
                    min-width: 350px;  /* 최소 너비 설정 */
                    word-wrap: break-word; /* 줄바꿈 처리 */
                """)
        self.message.setWordWrap(True)  # 여러 줄 표시 허용
        self.message.setMinimumWidth(230)  # 창 최소 가로 넓이
        self.message.setMaximumWidth(280)  # 창 최대 가로 넓이
        self.message.setContentsMargins(12, 0, -15, 7)  # 메시지 박스 안에 좌, 상, 우, 하 마진

        # 마스코트 이미지 (하단 오른쪽)
        self.mascot = QtWidgets.QLabel()
        # 부드럽게 축소 + 투명 처리
        pixmap = QtGui.QPixmap(resource_path("assets/stretch.png"))

        # # ✅ 부드럽게 축소 + 투명 처리
        pixmap = pixmap.scaled(50, 50, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # 마스코트 라벨 배경 제거 및 여백 없애기
        self.mascot.setPixmap(pixmap)
        self.mascot.setStyleSheet("background: transparent; border: none;")
        self.mascot.setFixedSize(50, 50)

        # 하단 레이아웃: 메세지 + 마스코트 이미지
        bottom = QtWidgets.QHBoxLayout()
        bottom.setContentsMargins(10, 10, 10, 10)  # 마지막 문장 아래 여백 추가
        bottom.addWidget(self.message)
        bottom.addWidget(self.mascot)

        # 전체 레이아웃: 상단 + 하단 구성
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        layout.addWidget(self.header_frame)  # 추가해야 header_frame 보임
        layout.addLayout(bottom)

        # 외부 전체 레이아웃 설정 ( 프레임 기준)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)  # 전체 여백 제거
        outer.setSpacing(0)
        outer.addWidget(self.container)

        self.adjustSize()

        # 말풍선이 클릭된 경우를 추적하기 위한 플래그
        self.balloon_shown_by_click = False

    def toggle_pin(self):
        self.set_fixed(not self.fixed)

    def set_fixed(self, fixed: bool):
        self.fixed = fixed

        if self.fixed:
            self.pin_button.setIcon(QIcon(resource_path("images/locked.png")))
            self.pin_button.setText("")

            # ✅ 고정 상태일 때 폰트와 스타일 적용
            from PyQt5.QtGui import QFontDatabase, QFont
            font_path = resource_path("fonts/NanumSquareRoundR.ttf")
            font_id = QFontDatabase.addApplicationFont(font_path)
            font_families = QFontDatabase.applicationFontFamilies(font_id)

            if font_families:
                font = QFont(font_families[0], 11)
                self.title.setFont(font)
                print(f"📌 고정 상태 폰트 적용됨: {font_families[0]}")
            else:
                print("⚠️ 폰트 로딩 실패")

            self.container.setStyleSheet("""
                QFrame {
                    background-color: #fff8dc;
                    border-radius: 15px;
                    border: none;

                }
            """)
            self.header_frame.setStyleSheet("""
                background-color: #ffe9b3;
                border: none;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            """)

            # 타이머 정지
            self.dani.hide_timer.stop()
            self.dani.timer.stop()

        else:
            self.pin_button.setIcon(QIcon(resource_path("images/unlocked.png")))
            self.pin_button.setText("")

            # 기본 스타일로 되돌리기
            self.container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 15px;
                }
            """)
            self.header_frame.setStyleSheet("""
                background-color: #fdf1dd;
                border: none;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            """)

            # 타이머 재시작
            self.dani.hide_timer.start(hide_time)
            self.dani.timer.start(msg_timer)

        self.update_title_with_pin()

    def mouseDoubleClickEvent(self, event):
        #if event.button() == QtCore.Qt.LeftButton:
            self.dani.last_message_by_click = True
            self.dani.change_message()  # 메시지만 교체
            self.dani.hide_timer.stop()
            self.dani.hide_timer.timeout.connect(self.dani.balloon.hide)
            self.dani.hide_timer.start(hide_time)  # hide_timer 초기화
            self.dani.timer.stop()
            self.dani.timer.start(msg_timer)
            self.balloon_shown_by_click = True

    def update_title_with_pin(self):
        base_title = "🏠 중구시설관리공단 알리미"
        if self.fixed:
            self.title.setText(base_title)
        else:
            self.title.setText(base_title)



    def mousePressEvent(self, event):
        """말풍선 클릭시 이벤트 (단일 클릭만 처리)"""
        """
        if event.button() == QtCore.Qt.LeftButton:
            self.dani.last_message_by_click = True
            self.dani.change_message()  # 메시지만 교체
            self.dani.hide_timer.stop()
            self.dani.hide_timer.timeout.connect(self.dani.balloon.hide)
            self.dani.hide_timer.start(hide_time)    # hide_timer 초기화
            self.dani.timer.stop()
            self.dani.timer.start(msg_timer)
            self.balloon_shown_by_click = True
        """
    def hide_balloon(self):
        """말풍선을 숨기고 타이머 초기화"""
        self.hide() # 말풍선 숨기기
        self.balloon_shown_by_click = False # 클릭으로 보여진 메시지 여부 초기화
        self.dani.timer.stop()

    """말풍선 위치 업데이트 함수 만들기"""
    def update_balloon_position(self):
        if self.balloon and self.balloon.isVisible():
            # 말풍선을 다니의 '머리 위'로 이동 (다니 위치 기준)
            x = self.x() + (self.width() - self.balloon.width()) // 2
            y = self.y() - self.balloon.height() - 10 # 약간 위쪽 간격
            self.balloon.move(x,y)

    def set_message(self, msg: str):
        """문구를 설정하고 크기 조절"""
        self.message.setText(msg)
        self.message.adjustSize()

        # 메시지 내용 기반으로 container 크기 재조정
        message_hint = self.message.sizeHint()
        mascot_size = self.mascot.size()

        # 너비는 메시지 + 마스코트 너비 + 여유 padding
        container_width = max(message_hint.width() + mascot_size.width(), 200)    #메시지 박스 가로 크기 조절

        # 높이는 둘 중 더 큰 걸 기준으로
        body_height = max(message_hint.height(), mascot_size.height())
        container_height = self.header_frame.height() + body_height + 30

        message_height = self.message.sizeHint().height()
        #container_width = max(self.message.sizeHint().width() + 80,250) # 여유 padding
        #container_height = message_height + self.header_frame.height() + 30

        self.container.setFixedSize(container_width, container_height)
        self.setFixedSize(container_width + 20, container_height + 20)

        self.update()

    def fade_in(self):
        """말풍선을 부드럽게 표시하는 QGraphicsOpacityEffect 기반 애니메이션"""
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        anim = QtCore.QPropertyAnimation(effect, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        # ✅ 포커스를 뺏지 않게 하려면 native window handle로 처리
        self.setWindowFlags(
            QtCore.Qt.Tool |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowDoesNotAcceptFocus
        )
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.show()


        anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        # 애니메이션을 변수로 잡아주지 않으면 GC에 의해 사라짐!
        self.anim = anim



class InactivityFilter(QtCore.QObject):
    def __init__(self, target_dani):
        # QObject의 생성자 호출
        # 부모 클래스의 초기화를 명시적으로 해줘야 내부 기능이 정상 작동함
        super().__init__()  # 클래스에서 상속받은 부모 클래스의 생성자를 호출할 때 사용하는 코드.
        """ super()란?
        super() 는 부모 클래스의 메서드나 생성자를 호출하는 함수.
        즉, 자식 클래스에서 __init__()을 새로 만들면, 부모 클래스의 __init()__은 자동으로 실행되지 않아.
        -> 그래서 우리가 명시적으로 super().__init__()을 써서 호출해줘야 해."""

        # 타겟 다니 객체를 기억해두기(입력 감지 시 다니에게 알려줄 것)
        self.dani = target_dani
        self.last_mouse_move_timer = 0 # 마지막 마우스 이동 처리 시각 저장

    def eventFilter(self, obj, event):
        """ 이벤트 필터 함수
        앱 전체의 이벤트를 가로채서 처리할 수 있게 해둠
        -> 이걸 통해 '사용자 활동이 있는지 를 감지함"""
        now = time.time()

        # 마우스 이동은 머무 자주 발생하므로 0.5초 이상 지나야만 반응
        if event.type() == QtCore.QEvent.MouseMove:
            if now - self.dani.last_input_time > 0.5:
                self.dani.reset_inactivity_timer()
                self.last_mouse_move_time = now

        # 마우스 클릭이나 키보드 입력은 즉시 반응
        elif event.type() in [QtCore.QEvent.MouseButtonPress, QtCore.QEvent.KeyPress]:
            self.dani.reset_inactivity_timer()


        # 다른 위젯에서도 이벤트를 계속 처리할 수 있도록 부모에게 전달
        return super().eventFilter(obj, event)

class Dani(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        # 사용자가 마지막으로 마우스나 키보드를 입력한 시각을 저장하는 기능
        self.last_input_time = time.time() # 시각 초기화

        # 1초마다 체크하는 타이머
        self.inactivity_check_timer = QtCore.QTimer() # 1초마다 무활동 여부를 확인하는 타이머 생성

        # 타이머가 1초마다 실행될 때 호출할 함수 연결
        # -> 여기선 check_inactivity() 함수가 실행됨
        self.inactivity_check_timer.timeout.connect(self.check_inactivity)
        # 타이머를 시작하고, 1000밀리초(1초) 간격으로 반복 실행하도록 설정
        self.inactivity_check_timer.start(3000) # 3초마다 확인

        # 현재 크기를 기억하는 self.scale_mode 추가
        self.scale_mode = "medium"

        # 창 속성을 설정 (투명 배경 + 항상 위 + 테두리 없음)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 상태 GIF 들


        self.default_movie = QtGui.QMovie(resource_path("assets/home.gif")) # 초기 다니 상태
        self.sleep_movie = QtGui.QMovie(resource_path("assets/sleep2.gif"))
        self.walk_movie = QtGui.QMovie(resource_path("assets/work.gif"))
        self.mute_movie = QtGui.QMovie(resource_path("assets/mute.gif"))



        self.movies = {
            "default": QtGui.QMovie(resource_path("assets/home.gif")),
            "sleep": QtGui.QMovie(resource_path("assets/sleep2.gif")),
            "walk": QtGui.QMovie(resource_path("assets/work.gif")),
            "rain": QtGui.QMovie(resource_path("assets/rain.gif")),  # 예시 추가
            "mask": QtGui.QMovie(resource_path("assets/mask.gif")),  # 예시 추가
            "mute": QtGui.QMovie(resource_path("assets/mute.gif")),
            "loading": QtGui.QMovie(resource_path("assets/loading3.gif")),
        }




        # 각 GIF의 재생 크기 강제 설정
        self.default_movie.setScaledSize(QtCore.QSize(200, 200))
        self.sleep_movie.setScaledSize(QtCore.QSize(200, 200))
        self.walk_movie.setScaledSize(QtCore.QSize(200, 200))
        self.setFixedSize(200, 200)  # 크기 지정

        # 초기 상태: 기본.
        self.setMovie(self.default_movie)
        self.default_movie.start()
        self.state = "default"

        # 말풍선 준비
        self.balloon = None

        # 메세지 타이머
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.show_random_message)
        self.timer.start(msg_timer)

        # 걷기 이동 타이머
        self.move_timer = QtCore.QTimer()
        self.move_timer.timeout.connect(self.move_step)

        # QTimer로 5초마다 랜덤 상태 전환
        self.behavior_timer = QtCore.QTimer()
        self.behavior_timer.timeout.connect(self.apply_behavior_if_needed)
        self.behavior_timer.start(5000) # 5초마다

        # 메시지 자동 숨기기 타이머
        self.hide_timer = QtCore.QTimer()
        self.balloon = FancyBalloon(self)

        self.balloon.setWindowFlags(
            QtCore.Qt.Tool |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowDoesNotAcceptFocus
        )
        self.balloon.setFocusPolicy(QtCore.Qt.NoFocus)  # ✅ 위젯 자체도 포커스 안 받게

        self.hide_timer.timeout.connect(self.balloon.hide)

        # 상태 저장용 변수 추가
        self.behavior_state = "idle" # 현재 동작 성태: idle, left, right

        # 걷기 gif 로드
        self.walk_left_movie = QtGui.QMovie(resource_path("assets/walk_left.gif"))
        self.walk_right_movie = QtGui.QMovie(resource_path("assets/walk_right.gif"))

        # 원하는 크기로 스케일
        self.walk_left_movie.setScaledSize(QtCore.QSize(200, 200))
        self.walk_right_movie.setScaledSize(QtCore.QSize(200, 200))

        # 바로 걷기 시작
        #self.wake_up()  # 실행 즉시 걷기 시작
        # 타이머와 수동 클릭 구분하기 위한 상태 변수 추가
        self.last_message_by_click = False  # 말풍선이 수동 클릭인지 자동 타이머인지

        # 현재 서버에서 받아온 행동 정보 저장 (type과 name)
        self.current_behavior = {"type": "IDLE", "name":"default"}

        # 마지막으로 받아온 행동의 시간정보(중복 요청 방지용)
        self.last_behavior_timestamp = None # 마지막 업데이트 시간

        """1분 주기로 서버에서 동작 받아오기"""
        # 1분마다 서버에서 '현재 행동 설정'을 요청하기 위한 타이머 설정
        self.fetch_behavior_timer = QtCore.QTimer()
        self.fetch_behavior_timer.timeout.connect(self.fetch_behavior_from_server)
        self.fetch_behavior_timer.start(60000) # 1분

        """self.current_scale_px 저장 변수 추가"""
        self.current_scale_px = 200 # 기본 크기 (medium)

        self.username = f"{socket.gethostname()}_{random.randint(100,999)}"
        self.chat_window = None # 메신저 창 아직 없음

        # 이벤트 루프 생성

        #self.loop = QEventLoop(self)
        self.loop = None    # 외부에서 주입됨

        # asyncio 전역 루프 지정
        asyncio.set_event_loop(self.loop)

        # 시스템 트레이 설정
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(QPixmap(resource_path("assets/dani.ico"))))  # self.tray_icon.setIcon(QIcon(QPixmap("dani.icon")))

        self.show()

        self.muted = False  # 기본값: 조용하지 않음

        # __init__ 내부에 추가
        self.timer_manager = TimerManager(self)

        """ 트레이 아이콘"""
        tray_menu = QMenu()
        tray_menu.addAction(
            QAction("다니 보기", self, triggered=self.show_dani))
        tray_menu.addAction(QAction("다니 숨기기", self, triggered=self.hide_dani))
        tray_menu.addAction(QAction("종료", self, triggered=sys.exit))
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.set_scale(settings.get('scale', 'medium'))  # 기본 medium
                    self.move(settings.get('x', 100), settings.get('y', 100))  # 위치 복원
                    print("📦 설정 복원 완료")
            except Exception as e:
                print(f"⚠️ 설정 복원 실패: {e}")
        else:
            self.set_scale('medium')  # 기본값

        """다니 실행시 알림용 웹소켓 연결 후 알림방 열면 websocket 그대로 전달해 충돌 방지"""
        #self.chat_client = ChatSocketClient(username=self.username) # ✅ 메시지 수신 시 자동 반응
        self.notice_client = ChatSocketClient(username=self.username, on_announce=self.react_to_message)
        
        # 드래그 플래그 추가
        self.is_dragging = False

        # Main 클래스에서 단 한 번만 생성
        self.browser = BrowserWindow()
        self.browser.dataReady.connect(self.receive_from_browser)
        #self.browser.show()
        self.browser.extractingStarted.connect(lambda: self.set_busy_gif(True))
        self.browser.extractingFinished.connect(lambda: self.set_busy_gif(False))
    
    """로딩 중 로딩 다니 디스플레이"""
    def set_busy_gif(self, busy: bool):
        if busy:
            self.timer_manager.stop_all()
            self.apply_idle_behavior("loading3")

        else:
            self.timer_manager.start_all()
            self.apply_idle_behavior("default")





    @QtCore.pyqtSlot(object)
    def receive_from_browser(self, data):
        if isinstance(data, dict):
            self.set_busy_gif(False)
            self.show_today_work_info(data)
        elif isinstance(data, str):
            self.set_busy_gif(False)
            self.show_balloon(data)
        else:
            print("⚠️ 알 수 없는 메시지 타입:", type(data))


    """채팅 클라이언트 호출 함수"""
    def open_chat_client(self):
        if not self.chat_window or not self.chat_window.isVisible():
            from chat_widget import ChatWidget

            self.chat_window = ChatWidget(username=self.username)  # ✅ parent 제거!
                #self.chat_window.message_received.connect(
                    #lambda username, message: self.react_to_message(username, message))  # 메시지 수신시

            # ✅ 공지 수신 시 다니가 반응하도록 시그널 연결
            #self.chat_window.on_announced.connect(self.react_to_message)
            #self.chat_client.attach_widget(self.chat_window)  # 연결만 함

            self.chat_window.show()
            self.chat_window.setFocus()
            # ✅ Dani에 저장된 loop를 통해 연결
            # 비동기 루프 확보
            if not self.loop:
                self.loop = QEventLoop()
                asyncio.set_event_loop(self.loop)

            self.loop.create_task(self.chat_window.connect())


    def react_to_message(self, sender, message):
        # 말풍선에 메시지 띄우기

        PopupManager.show_popup(
            title=f"📣 {sender}",
            message=f"✅ {message}",
        )
        self.show_balloon(f"📣 {sender}"'\n'f"✅ {message}")

        if not self.chat_window:
            print("⚠️ 채팅창이 닫혀 있거나 WebSocket 없음")
            return

        if self.hide:
            return

        if not self.balloon:
            self.balloon = FancyBalloon(self)

        # 수면 중일 경우 깨우기
        if self.state == "sleep":
            self.wake_up()

    
        self.balloon.set_message(f"{sender} : {message}")   # sender 와 message를 받아서 셋
        self.balloon.fade_in()  # 부드럽게 보여주기
        self.update_balloon_position()  # 위치 조정
        self.last_message_by_click = False

        # 💡 강제로 최상단 + 포커스 부여
        self.balloon.raise_()
        #self.balloon.activateWindow()
        #self.balloon.setFocus()

        self.balloon.setWindowFlags(
            QtCore.Qt.Tool |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowDoesNotAcceptFocus  # ✅ 포커스 차단
        )


        # 4초 뒤 말풍선 자동 숨김
        self.hide_timer.stop()
        self.hide_timer.timeout.connect(self.balloon.hide)
        self.hide_timer.start()

        # show 말풍선 초기화
        self.timer.stop()
        self.timer.start(msg_timer)

        # 움찔하거나 눈 반짝이는 애니메이션 재생
        """self.play_react_animation()"""





    def apply_scale_if_needed(self, movie: QtGui.QMovie):
        """현재 스케일과 다른 경우에만 setScaledSzie를 적용"""
        if self.scale_mode == "small":
            size_px = 100
        elif self.sclae_mode == "large":
            size_px = 300
        else:
            size_px = 200

        if size_px != self.current_scale_px:
            print(f" 스케일 변경 감지 -> {self.current_scale_px} -> {size_px}")
            movie.setScaledSize(QtCore.QSize(size_px, size_px))
            self.current_scale_px = size_px

    def apply_scale_to_movie(self, movie: QtGui.QMovie = None):
        """현재 scale_mode에 맞춰 movie 크기 설정"""
        """다니 전체 크기와 현재 gif의 스케일을 동시에 적용하는 함수.
        movie를 전달하면 해당 gif에도 크기를 적용함.
        전달하지 않으면 현재 self.movie()에 적용함.
        """
        if self.scale_mode == "small":
            size_px = 100
        elif self.scale_mode == "large":
            size_px = 300
        else:
            size_px = 200

        # ✅ 다니 QLabel 자체 크기 조정
        self.setFixedSize(size_px, size_px)
        self.current_scale_px = size_px  # 내부 상태 갱신
        # ✅ 현재 GIF 또는 지정된 movie에 크기 설정
        target_movie = movie or self.movie()
        if target_movie:
            target_movie.setScaledSize(QtCore.QSize(size_px, size_px))
            self.setMovie(target_movie)
            target_movie.start()

    def fetch_behavior_from_server(self):
        """
        서버에서 현재 적요알 행동 정보를 받아오는 함수,
        type (예 : LEFT, RIGHT, IDLE)와 name (idle 행동의 세부 이름)을 받아 저장한다.
        중복된 응답은 무시하고, 새로운 정보일 때만 갱신한다.
        :return:
        """
        try:
            # 서버에 행동 정보 요청
            res = requests.get(f"{server}/behavior", timeout=5)
            data = res.json()

            updated_at = data.get("updated_at")

            # 새로운 행동이라면 갱신
            if updated_at != self.last_behavior_timestamp:
                print(" 서버에서 새로운 행동 수신:", data)
                self.current_behavior = {
                    "type": data.get("type"," IDLE"),
                    "name" : data.get("name", "default")
                }
                self.last_behavior_timestamp = updated_at
            else:
                return
                # 이미 받은 행동이라면 무시
                #print(" 행동 동일 -> 무시")

        except Exception as e:
            print(" 행동 받아오기 실패:",e)

    def apply_behavior_if_needed(self):
        # 걷기 or 정지 랜덤 결정
        if self.muted:
            self.apply_idle_behavior("mute")

            return

        movement_type = random.choice(["LEFT", "RIGHT", "IDLE"])

        if movement_type == "LEFT":
            self.apply_walk_behavior(direction=-1)
        elif movement_type == "RIGHT":
            self.apply_walk_behavior(direction=1)


        else:   # IDLE일 때는 서버 설정된 name에 따라 애니메이션 변경
            if self.muted:
                self.apply_idle_behavior("mute")
                return

            name = self.current_behavior.get("name", "default")
            self.apply_idle_behavior(name)

    def apply_walk_behavior(self, direction):
        """
        걷기 동작 적용. 방향 -1이면 왼쪽, 1이면 오른쪽
        :param direction:
        :return:
        """
        self.walk_direction = direction
        if direction == -1:
            if not os.path.exists(resource_path("assets/walk_left.gif")):
                print("❌ walk_left.gif 없음! 기본으로 전환")

            else:
                self.apply_scale_to_movie(self.walk_left_movie)
                self.setMovie(self.walk_left_movie)
                self.walk_left_movie.start()
        elif direction == 1:
            self.apply_scale_to_movie(self.walk_right_movie)
            self.setMovie(self.walk_right_movie)
            self.walk_right_movie.start()

        self.state = "walk"
        self.move_timer.start(50)

    def apply_idle_behavior(self, name):
        """
        idle 행동 적용 (예: mask, ubrella 등)
        해당 name에 대응되는 gif가 있어야 함.
        """
        if name == "default":
            _, path = get_default_message_and_gif()
            movie = QtGui.QMovie(resource_path(path))
            self.apply_scale_to_movie(movie)

            self.state = "default"
        else:
            path = f"assets/{name}.gif"
            if not os.path.exists(resource_path(path)):
                print(f"❌ gif 파일 없음: {path} -> 기본으로 대체")
                movie = self.default_movie
                self.apply_scale_to_movie(movie)  # ✅ 크기 적용
                self.state = "default"
            else:
                movie = QtGui.QMovie(resource_path(path))
                self.apply_scale_to_movie(movie)  # ✅ 크기 적용
                # 현재 scale_mode에 맞춰 크기 적용
                if self.scale_mode == "small":
                    size_px = 100
                elif self.scale_mode == "large":
                    size_px = 300
                else:
                    size_px = 200

                # GIF 애니메이션의 프레임 크기를 조정함.
                movie.setScaledSize(QtCore.QSize(size_px, size_px))
                self.state = name
        self.setMovie(movie)
        movie.start()
        self.move_timer.stop() # idle은 이동 없음


    # 드래그 기능 추가
    def mousePressEvent(self, event):

        if event.button() == QtCore.Qt.RightButton:
            self.contextMenuEvent(event.pos())
            return

        if event.button() == QtCore.Qt.LeftButton:
            # 현재 마우스 클릭 지점과 다니 위치의 차이 저장
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.is_dragging = True  # ✅ 드래그 시작
            event.accept()
            return  # ✅ 클릭 이벤트 이후 말풍선 처리 방지




    def mouseDoubleClickEvent(self, event):

        # 무음 상태일 때는 클릭해도 말풍선 x
        if self.muted:
            return

        # 수면 상태일 때는 클릭으로만 깨어남
        if self.state == "sleep":
            print(" 다니 클릭 -> 깨우기!")
            self.wake_up()

        elif not self.balloon:    # 말풍선이 없으면 새로 생성하고 메시지 표시
            self.balloon = FancyBalloon(self)
            self.show_random_message()

            self.hide_timer.stop()
            self.hide_timer.timeout.connect(self.balloon.hide)
            self.hide_timer.start(hide_time)
            #QtCore.QTimer.singleShot(hide_timer, self.balloon.hide)  # 4초 후 숨기기

        # 말풍선이 존재하고, 숨겨져 있을 때는 다시 표시
        elif self.balloon.isVisible() == False: # 말풍선이 숨겨져 있으면
            self.balloon.show() # 말풍선 다시 보여주기
            self.show_random_message()  # 새로운 메시지 표시

            self.hide_timer.stop()
            self.hide_timer.timeout.connect(self.balloon.hide)
            self.hide_timer.start(hide_time)
            #QtCore.QTimer.singleShot(hide_timer, self.balloon.hide)  # 4초 후 숨기기

        else:   # 말풍선이 떠 있는 경우 메시지만 교체
            # 평소처럼 메세지 띄우기
            self.last_message_by_click = True
            self.change_message()
            self.hide_timer.stop()
            self.hide_timer.timeout.connect(self.balloon.hide)
            self.hide_timer.start(hide_time)

        self.timer.stop()
        self.timer.start(msg_timer)

    """Dani 클래스 안에 moveEvent() 오버라이드"""
    def moveEvent(self, event):
        self.update_balloon_position()  # 다니가 이동할 때마다 위치 재조정
        super().moveEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            # 이동 위치 계산
            new_pos = event.globalPos() - self.drag_position

            # 전체 스크린 영역 계산 (듀얼 모니터 대응)
            screens = QtWidgets.QApplication.screens()
            total_rect = QtCore.QRect()
            for screen in screens:
                total_rect = total_rect.united(screen.availableGeometry())

            # 다니의 크기 고려한 위치 제한
            x = max(total_rect.left(), min(new_pos.x(), total_rect.right() - self.width()))
            y = max(total_rect.top(), min(new_pos.y(), total_rect.bottom() - self.height()))

            self.move(x,y)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False  # ✅ 드래그 종료

    def reset_inactivity_timer(self):
            # 사용자가 마우스를 움직이면
            self.last_input_time = time.time()  # 현재 시각 저장
            #print(f"[입력 감지] last_input_time 갱신됨: {self.last_input_time:.2f}")

    def check_inactivity(self):
        if self.muted:
            return

        now = time.time()
        elapsed = now - self.last_input_time
        #print(f"[체크] 현재 시각: {now}, 마지막 입력: {self.last_input_time}, 경과: {elapsed:.2f}s")


        if self.state != "sleep" and elapsed >= 30:
                print("입력 안한 시간 =", elapsed)
                print(time.time())
                print(self.last_input_time)
                print("💤 30초 동안 입력 없음 → 수면 상태 진입")
                self.go_to_sleep()


    # move_step
    def move_step(self):
        """걷는 중에 위치를 조금씩 이동, 화면 밖으로 나가지 않게 제한"""
        screens = QtWidgets.QApplication.screens()
        total_rect = QtCore.QRect()

        for screen in screens:
            total_rect = total_rect.united(screen.availableGeometry())

        cur_pos = self.pos()
        new_x = cur_pos.x() + self.walk_direction

        # 다니 오른쪽 끝이 화면보다 커지면 방향 반전
        if new_x + self.width() > total_rect.right():
            new_x = total_rect.right() - self.width()
            self.walk_direction *= -1
        # 다니 왼쪽이 화면보다 작아지면 방향 반전
        elif new_x < total_rect.left():
            new_x = total_rect.left()
            self.walk_direction *= -1

        self.move(new_x, cur_pos.y())



    def switch_state(self):
        """자는 <-> 걷는 상태 전환"""
        if self.state == "sleep":

            print("걷는 GIF 유효성:", self.walk_movie.isValid())
            self.setMovie(self.walk_movie)
            self.walk_movie.start()
            self.state = "walk"
            print("걷는 상태로 전환")
        else:
            print("자는 상태로 전환")
            print("자는 GIF 유효성:", self.sleep_movie.isValid())
            self.setMovie(self.sleep_movie)
            self.sleep_movie.start()
            self.state = "sleep"


        # 다니 이미지 로딩 ( 원본 이미지 저장)
        self.original_pixmap = QtGui.QPixmap(
            "assets/coffee.gif")

        # 기본 크기 설정 (중간)
        self.set_scale("medium") # 초기 사이즈

        # 말풍선 인스턴스 준비
        self.balloon = None
        # 8초마다 자동으로 메세지를 띄우기 위한 타이머
        #self.timer = QtCore.QTimer(self)
        #self.timer.timeout.connect(self.show_random_message)
        #self.timer.start(8000) # 8초마다 메세지 팝업

    def set_scale(self, size):
        """
        다니 캐릭터의 크기를 변경합니다.
        size 값은 'small', 'medium', 'large' 중 하나여야 합니다.
        """
        self.scale_mode = size
        self.apply_scale_to_movie()
        self.save_settings()  # 🔄 변경사항 저장


    def wake_up(self):
        """자는 상태에서 깨어나는 함수"""
        print("다니가 깨어남!")



        self.state = "walk"
        # 걷기 애니메이션 재생
        self.apply_scale_to_movie(self.walk_movie)  # ✅ 크기 적용
        self.setMovie(self.walk_movie)
        self.walk_movie.start()

        # 이동 방향 랜덤 설정
        #self.walk_direction = random.choice([-1, 1])
        #self.move_timer.start(50)

        # 타이머 재시작
        self.timer_manager.start_all()
        #self.timer.start(msg_timer)
        #self.behavior_timer.start(5000)

        # 말풍선 숨기기
        if self.balloon:
            self.balloon.hide()


        #self.apply_scale_to_gif()   # 스케일

    def go_to_sleep(self):
        """걷는 상태 -> 다시 자는 상태로 전환"""
        print("go_to_sleep 함수 호출")

        self.state = "sleep"

        # 이동, 행동, 말풍선 타이머 전부 정지
        self.move_timer.stop()  # 이동 타이머 정지
        self.timer.stop()       # 말풍선 타이머 정지
        self.behavior_timer.stop()  # 행동 타이머 정지


        # 수면용 애니메이션 적용
        self.setMovie(self.sleep_movie)
        self.sleep_movie.start()
        self.apply_scale_to_movie(self.sleep_movie)
        # '다니를 클릭하여 깨워주세요" 말풍선 표시
        self.show_sleep_message()

    def show_sleep_message(self):
        """ 자는 중일 때 표시할 말풍선"""
        if not self.balloon:
            self.balloon = FancyBalloon(self)

        self.balloon.set_message("💤 다니를 더블 클릭하여 깨워주세요.")
        self.balloon.fade_in()
        self.update_balloon_position()
        self.balloon.raise_()
        #self.balloon.activateWindow()
        #self.balloon.setFocus()


    """물풍선 위치 업데이트 함수 만들기"""
    def update_balloon_position(self):
        if self.balloon and self.balloon.isVisible():
            # 말풍선을 다니의 '머리 위'로 이동 (다니 위치 기준)
            x = self.x() + (self.width() - self.balloon.width()) // 2
            y = self.y() - self.balloon.height() - 10  # 약간 위쪽 간격
            self.balloon.move(x, y)

    def change_message(self):
        """클릭시 메시지 교체"""
        try:
            if not self.balloon:
                self.balloon = FancyBalloon(self)

            msg = get_random_message()
            self.balloon.set_message(msg)
        except Exception as e:
            print("서버 요청 실패: ", e)
            return "서버 연결 실패!,change_random_message()"


    def hide_balloon(self):
        """말풍선 숨기기"""
        if self.balloon:
            self.balloon.hide()

    def show_balloon(self, message):
        """메시지를 인자로 받아 말풍선 출력, 주로 공지 또는 중요한 메시지, 조용히 모드일 때도 적용"""

        # 수면 중일 경우 깨우기
        if self.state == "sleep":
            self.wake_up()

        if message:
            self.balloon = FancyBalloon(self)

            self.balloon.set_message(message)


            self.balloon.fade_in()  # 강하게 보여주기

            self.update_balloon_position()  # 위치 조정
            self.last_message_by_click = False

            # 💡 강제로 최상단 + 포커스 부여
            #self.balloon.raise_()
            #self.balloon.activateWindow()
            self.balloon.setFocus()

            # 8초 뒤 말풍선 자동 숨김
            self.hide_timer.stop()
            self.hide_timer.timeout.connect(self.balloon.hide)
            self.hide_timer.start(8000)

            # 자동 말풍선 show 타이머 초기화
            self.timer.stop()
            self.timer.start(msg_timer)


        else:
            print("인자로 받은 메시지가 없습니다.")


    def show_random_message(self):
        """
        서버에서 메세지를 받아 말풍선에 표시하고
        4초 후 자동으로 사라지게 함.
        """
        if self.muted:
            print("muted 상태입니다.")
            return  # 조용히 모드일 땐 메시지 안 띄움

        try:
            # 부모 없는 말풍선 (다니 외부에 표시)
            if not self.balloon:
                self.balloon = FancyBalloon(self)

            msg = get_random_message()

            self.balloon = FancyBalloon(self)

            #self.balloon = FancyBalloon(self)
            self.balloon.set_message(msg)
            self.balloon.fade_in() # 부드럽게 보여주기

            self.update_balloon_position()  # 위치 조정
            self.last_message_by_click = False

            # 💡 강제로 최상단 + 포커스 부여
            self.balloon.raise_()
            self.balloon.activateWindow()
            self.balloon.setFocus()


            # 4초 뒤 말풍선 자동 숨김
            self.hide_timer.stop()
            self.hide_timer.timeout.connect(self.balloon.hide)
            self.hide_timer.start(hide_time)

            # 자동 말풍선 show 타이머 초기화
            self.timer.stop()
            self.timer.start(msg_timer)


            #QtCore.QTimer.singleShot(hide_timer, self.balloon.hide)  # 4초 뒤 자동 숨김

        except Exception as e:
            print("서버 요청 실패: ",e)
            return "서버 연결 실패!,show_random_message()"

    async def test_ws(self):
        async with websockets.connect("ws://192.168.1.11:9090") as websocket:
            while True:
                msg = await websocket.recv()
                print("📩 수신:", msg)

    def show_today_work_info(self, data):
        print("📦 수신된 데이터 타입:", type(data))
        print("📦 수신된 데이터 내용:", data)
        if data and (data.get('todayRowDict')) :
            today_row_list = (data.get('todayRowDict'))
            last_row_list = (data.get('lastRowDict'))
            message = \
        f"""📅 {today_row_list.get('일자')}  👤 {today_row_list.get('이름')}
🕗 출근: {today_row_list.get('시작')}  🕔 퇴근: {today_row_list.get('종료')}
🚪 기록: {today_row_list.get('출근')}
💰 초과: {last_row_list.get('초과')}
🍽️ 특매: {last_row_list.get('특매')}"""
            self.show_balloon(message)

    # 보이기, 숨기기 함수
    def show_dani(self):
        self.show()
        self.timer_manager.start_all()

    def hide_dani(self):
        self.hide()
        if self.balloon:
            self.balloon.hide()
        self.timer_manager.stop_all()

    # save_settings
    def save_settings(self):
        settings = {
            'scale': self.scale_mode,
            'x': self.x(),
            'y': self.y()
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
        print("✅ 설정 저장 완료")


    # 우클릭 메뉴를 화면에 띄우는 함수
    def contextMenuEvent(self, event):
        """
        우클릭 시 실행되는 메뉴 (크기 변경 및 종료 기능)
        :param event:
        :return:
        """
        # 전역 좌표로 변환
        global_Pos = self.mapToGlobal(event)

        menu = QtWidgets.QMenu(self)    #메뉴 생성
        open_chat_action = menu.addAction("💬 다니 알림방")   # 메뉴 항목 추가

        lunch_action = menu.addAction("🍱 점심 메뉴 추천받기")  # 점심 메뉴 추천 추가

        work_info_action = menu.addAction("⏰ 오늘 근무 기록 보기")

        small_action = menu.addAction("작게")
        medium_action = menu.addAction("중간")
        large_action = menu.addAction("크게")
        mute_action = menu.addAction("조용히")
        unmute_action = menu.addAction("조용히 해제")
        hide_action = menu.addAction("숨기기")
        quit_action = menu.addAction("🚪 종료")

        # 실제 메뉴 띄우기 (마우스 위치에서 실행)
        action = menu.exec_(global_Pos)

        # 선택된 메뉴에 따라 동적 실행
        if action == open_chat_action:
            # 이미 창이 열려 있지 않거나 닫혔다면 새로 열기
            if self.chat_window and self.chat_window.isVisible():
                print("💬 채팅창 이미 열려 있음 → 최상위로")
                self.chat_window.raise_()
                self.chat_window.activateWindow()
            else:

                print("💬 채팅창 새로 열기")
                self.open_chat_client()
                self.chat_window.activateWindow()

        elif action == lunch_action:
            # game.py 경로가 현재 디렉터리에 있다고 가정

            game_exe_path = resource_path("game.exe")
            subprocess.Popen([game_exe_path])

        # 근무 조회
        elif action == work_info_action:
            if self.browser is None or not self.browser.isVisible():
                print("객체가 없거나 닫혀 있음 -> 새로 생성")
                # browser 객체 생성
                self.browser = BrowserWindow()
                # browser 객체와 연결
                self.browser.dataReady.connect(self.receive_from_browser)
                self.browser.extractingStarted.connect(lambda: self.set_busy_gif(True))
                self.browser.extractingFinished.connect(lambda: self.set_busy_gif(False))

            # 이미 추출 중이라면 재호출 방지
            if self.browser.is_extractiong():
                self.show_balloon("⚠️ 이미 조회 중이에요.\n조회가 끝나면 알려 드릴게요!")
                print("⚠️ 추출 중입니다. 중복 호출 방지됨.")
                return

            # 추출 중이 아니라면, browser 객체를 통해 함수 호출
            receive_data = self.browser.send_today_data_to_dani()
            self.show_today_work_info(receive_data)

            # ✅ 조회 성공 후, BrowserWindow 해제
            #if receive_data:
                #self.browser.setParent(None)    # 위젯 트리에서 제거
                #self.browser.deleteLater()  # Qt 메모리 해제 예약
                #self.browser = None # python 참조 제거

        elif action == small_action:
            self.set_scale("small")
        elif action == medium_action:
            self.set_scale("medium")
        elif action == large_action:
            self.set_scale("large")
        elif action == mute_action:

            self.muted = True

            self.apply_idle_behavior("mute")
            self.behavior_timer.stop()
            if self.balloon:
                self.balloon.hide()
        elif action == unmute_action:
            self.muted = False
            self.wake_up()  # 또는 기본 gif로 되돌리기

        elif action == hide_action:
            self.hide_dani()

        elif action == quit_action:
            QtWidgets.QApplication.quit()
            #sys.exit(app.exec_())
            sys.exit(0)

    # 타이머 통합 관리 클래스 정의
# 다니 클래스 바깥에 TimerManager 정의
class TimerManager:
    def __init__(self, dani):
        self.dani = dani
        self.timers = [
            dani.timer,
            dani.move_timer,
            dani.behavior_timer,
            dani.hide_timer,
            dani.fetch_behavior_timer,
            dani.inactivity_check_timer
        ]

    def stop_all(self):
        for timer in self.timers:
            if timer.isActive():
                timer.stop()
        print("⏸️ 모든 타이머 중지")

    def start_all(self):
        self.dani.timer.start(msg_timer)
        self.dani.behavior_timer.start(5000)
        self.dani.fetch_behavior_timer.start(60000)
        self.dani.inactivity_check_timer.start(3000)
        print("▶️ 타이머 재시작 완료 (숨김 상태 제외)")


class DaniReceiver:
    def __init__(self, show_callback=None, autologin_instance=None):
        self.external_callback = show_callback
        self.show_callback = self.combined_show  # 둘 다 실행하도록 설정
        self.autologin_instance = autologin_instance

    def default_show(self, message):
        print(f"💬 기본 출력: {message}")
        # 기본 알림도 여기에 띄울 수 있음
        PopupManager.show_popup(
            title="전자 결재 알림",
            message=message
        )

    def combined_show(self, message):
        self.default_show(message)  # 기본 처리
        if self.external_callback:
            self.external_callback(message)  # 외부 함수도 실행


    async def start_local_server(self, port=9999):
        # 다니가 로컬에서 열 Websocket 서버 시작
        print(f"🚀 Dani WebSocket 서버 실행 중: ws://127.0.0.1:{port}")
        async with websockets.serve(self.handle_message, "127.0.0.1", port):
            await asyncio.Future() # 서버 유지

    async def handle_message(self, websocket):
        try:

            async for message in websocket:
                print(f"🚗 수신 메시지: {message}")
                try:
                    data = json.loads(message)

                    if data.get("type") == "hook_status" and data.get("status") == "success":
                        print("✅ 후킹 성공 패킷 수신")
                        if self.autologin_instance:
                            self.autologin_instance.set_hook_success()
                        if self.show_callback:
                            self.show_callback("✅ 전자결재 알림 설정이 완료되었어요!")
                        return

                    # 그 외 알림 메시지인 경우만 계속 처리
                    sender = data.get("sender","알 수 없음")
                    subject = data.get("subject","제목 없음")
                    receivedate = data.get("receivedate", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))


                    # 💬 말풍선 문구 조립
                    msg = f"📨 {sender}\n📌 {subject} ({receivedate})"
                    self.show_callback(msg)

                    #서버로 병행 전송 (선택)
                    await self.send_to_central_server(data)

                except Exception as e:
                    print("❌ JSON 파싱 실패 또는 처리 오류:", e)
        except websockets.exceptions.ConnectionClosed:
            print("🔴 연결 종료됨")

    async def send_to_central_server(self, data):
        # 중앙 서버로 병행 전송
        try:
            async with websockets.connect("ws://192.168.1.11:9090") as ws:
                await ws.send(json.dumps(data))
                print("📡 중앙 서버로 전송 완료")
        except Exception as e:
            print("⚠️ 중앙 서버 전송 실패:", e)



class PopupNotification2(QWidget):
    closed = pyqtSignal()  # ✅ 닫힐 때 외부에 알림

    def __init__(self, title: str, message: str, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)

        self.label = QLabel(self)
        self.label.setFixedSize(280, 60)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # ✂️ 긴 메시지는 자동 축약 (elide)
        metrics = QFontMetrics(self.label.font())
        elided = metrics.elidedText(message, Qt.ElideRight, self.label.width())
        self.label.setText(f"""
                    <span style="color:#FF9500; font-weight:500;">{title}</span><br>
                    <span style="color:#333;">{elided}</span>
                """)

        self.label.setStyleSheet("""
            QLabel {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #ccc;
            }
        """)

        self.full_tip = QLabel(message, self)
        self.full_tip.setStyleSheet("""
                    background-color: #fffce8;
                    border: 1px solid #aaa;
                    padding: 6px;
                    color: black;
                """)
        self.full_tip.setWindowFlags(Qt.ToolTip)
        self.full_tip.setWordWrap(True)
        #self.full_tip.setFixedWidth(500)
        self.full_tip.adjustSize()
        self.full_tip.hide()

        self.label.installEventFilter(self)

        self.setWindowOpacity(0.0)
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()

        #self.auto_close_timer = QTimer(self)
        #self.auto_close_timer.setSingleShot(True)
        #self.auto_close_timer.timeout.connect(self.close)
        #self.auto_close_timer.start(2500)

    def mousePressEvent(self, event):
        self.close()
        if self.callback:
            self.callback()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.label:
            if event.type() == QEvent.Enter:
                # 중앙 정렬 위치 계산 v2
                """
                screen = QApplication.primaryScreen().geometry()
                x = screen.center().x() - self.full_tip.width() // 2
                y = screen.center().y() - self.full_tip.height() // 2
                self.full_tip.move(x, y)
                self.full_tip.show()
                """


                """기존 버전"""
                global_pos = self.mapToGlobal(self.rect().topLeft())
                self.full_tip.move(global_pos.x() - self.full_tip.width() - 30, global_pos.y() - self.full_tip.height() - 10)
                self.full_tip.show()
            elif event.type() == QEvent.Leave:
                self.full_tip.hide()
        return super().eventFilter(obj, event)

class PopupManager:
        active_popups = []

        @classmethod
        def show_popup(cls, title, message, callback=None):
            popup = PopupNotification2(title, message, callback)
            cls.active_popups.append(popup)
            cls.reposition_popups()
            popup.closed.connect(lambda: cls.remove_popup(popup))
            popup.show()

        @classmethod
        def remove_popup(cls, popup):
            if popup in cls.active_popups:
                cls.active_popups.remove(popup)
                cls.reposition_popups()

        @classmethod
        def reposition_popups(cls):
            screen = QApplication.primaryScreen().availableGeometry()
            margin = 10
            popup_height = 60

            for i, popup in enumerate(reversed(cls.active_popups)):
                x = screen.right() - popup.width() - margin
                y = screen.bottom() - margin - ((i + 1) * popup_height)
                popup.move(x, y)

"""공지 전용 웹소켓 연결"""
class ChatSocketClient:
    def __init__(self, username, on_announce=None):
        self.username = username
        self.on_announce = on_announce  # 다니의 말풍선 react_to_message()
        self.ws = None


    async def connect(self):
        uri = f"ws://localhost:30006/notice/{self.username}"
        self.ws = await websockets.connect(uri)
        print("✅ WebSocket 연결 완료 (초기 알림용)")
        await self.receive_messages()

    async def receive_messages(self):
        try:
            async for message in self.ws:
                data = json.loads(message)

                # @공지 메시지 감지
                if data.get("type") == "announcement":
                    sender = data.get("sender", "알 수 없음")
                    content = data.get("message", "")

                    print(f"📣 공지 수신됨: {sender} → {content}")

                    # 1. 다니에게 전달
                    # 외부에서 지정된 콜백 함수 호출
                    if self.on_announce:
                        self.on_announce(sender, content)


        except Exception as e:
            print(f"❌ ChatSocketClient 수신 중 오류: {e}")

# PYQt 애플리케이션 실행
"""
 이 코드는 해당 파일이 직접 실행될 때만 아래 코드를 실행하라는 뜻
 다른 파일에서 import 될 경우엔 실행되지 않음
 파이썬에서 "이 파일이 실행 시작점인지" 판단할 때 표준적으로 사용
"""
if __name__ == "__main__":
    print("✅ Dani 실행 시작")
    """pyQt 프로그램을 시작할 때 반드시 필요한 기본 앱 객체
    이 객체가 전체 윈도우 이벤트 처리, 위젯 생성, 키보드,마우스 이벤트 등을 모두 관리
    sys.argv는 명령줄 인자를 전달하기 위해 포함"""
    # ✅ PyQt 애플리케이션 인스턴스 생성 (이벤트 루프 포함)
    app = QtWidgets.QApplication(sys.argv)  #PyQt 앱 생성


    """
    if is_already_running():
        
        QMessageBox.warning(None, "⚠️ 경고", "이미 실행 중입니다. 두 개 이상의 다니는 실행할 수 없습니다.")
        print("⚠️ 이미 실행 중입니다. 두 개 이상의 다니는 실행할 수 없습니다.")
        sys.exit(0)
    """ # 테스트시 미적용, 배포시 적용


    # ✅ 기본 폰트 적용
    font_path = resource_path("fonts/NanumSquareRoundR.ttf")
    apply_default_font(font_path)

    # ✅ Dani 캐릭터 생성 (말풍선, 애니메이션, 동작 타이머 등 초기화)
    dani = Dani()   #Dani 클래스 인스턴스 생성(self 포함된 내부 구조 초기화됨)
    # ✅ 사용자 입력(마우스/키보드) 감지를 위한 전역 모니터 설정
    global_monitor = GlobalActivityMonitor(dani) # 전역 입력 감지 시작
    # ✅ 화면에 다니 표시
    dani.show() # 화면에 다니 표시
    # ✅ 실행 직후 랜덤 메시지 한 번 표시
    dani.show_random_message()

    #window = TestWindow()
    #window.show()

    window = AutoLogin()
    #window.show()

    """이제 asyncio와 연결 시작"""
    """qsync에서 제공하는 PyQt + asyncio 통합 이벤트 루프
    원래 PyQt는 async def, await 등을 사용할 수 없지만
    이 루프를 통해 PyQt도 비동기 코드를 자연스럽게 처리 가능"""

    """asyncio가 내부적으로 사용할 기본 이벤트 루프를 등록
    create_tast()나 await를 사용할 때, asyncio는 어떤 루프를 쓸지 모르기 때문에, 우리가 지정"""

    #monitor = MemoryMonitor()
    #monitor.show()


    # ✅ DaniReceiver: 로컬 WebSocket 서버 실행 (브라우저 후킹 메시지 수신용)

    # show_callback으로 dani.show_balloon() 전달 → 메시지 수신 시 다니 말풍선으로 표시
    receiver = DaniReceiver(show_callback=dani.show_balloon, autologin_instance=window)  # Dani에 메시지 전달
    receiver.autologin_instance = window

    # ✅ PyQt5 + asyncio 통합 루프 생성 (qasync 필요)
    loop = QEventLoop(app)  # app을 루프에 연결
    # ✅ 이 루프를 전역 asyncio 루프로 등록 (이후 모든 await는 이 루프에 의해 관리됨)
    asyncio.set_event_loop(loop)  # asyncio    전역 루프로 등록

    # ✅ 로컬 WebSocket 서버 실행 (127.0.0.1:9999)
    loop.create_task(receiver.start_local_server())

    #loop.create_task(dani.chat_window.connect())


    dani.loop = loop  # 다니에게 루프 주입
    loop.create_task(dani.notice_client.connect()) # 그 후에 웹소켓 연결



    # ✅ 비동기 루프 실행 (Qt 앱이 종료될 때까지 무한 대기)
    with loop:
        loop.run_forever()

    #sys.exit(app.exec_())  # <- 사실 with loop 내에 있기 때문에 없어도 무방

