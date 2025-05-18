# chat_widget.py
import base64
import os
import shutil
import sys
import json
import asyncio
import base64
import websockets
from datetime import datetime
from io import BytesIO
from PIL import Image
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QDialog, QDialogButtonBox, QScrollArea, QFrame,
    QSizePolicy, QFileDialog, QTextEdit, QComboBox, QListWidget, QListWidgetItem, QTextBrowser, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QCoreApplication
from qasync import asyncSlot, QtCore, QtGui
from PyQt5.QtGui import QFont, QFontDatabase, QPixmap, QTextOption, QIcon
from qasync import QEventLoop, asyncSlot
from websockets.exceptions import ConnectionClosed
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QSize, QEasingCurve
from datetime import datetime, timedelta
from Dani import PopupManager

# 다니 기분 리스트
dani_moods = ["행복한", "우울한", "기쁜", "신난", "졸린", "화난", "편안한", "조용한"]


# 이미지 파일을 리사이즈하고 base64로 인코딩
def resize_image_to_base64(image_path, size=(128, 128)):
    img = Image.open(image_path)
    img = img.resize(size)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def resource_path(relative_path):
    """PyInstaller 실행환경과 개발환경 모두에서 리소스를 불러올 수 있도록 경로 보정"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 실행 중일 때 생성되는 임시 폴더
    except Exception:
        base_path = os.path.abspath(".")  # 개발환경에서는 현재 경로 기준

    return os.path.join(base_path, relative_path)


# 실행 중인 파일 위치 기준으로 캐시 저장
CACHE_FILE = resource_path("users_cache.json")


def load_user_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"캐시 로딩 실패: {e}")
        return {}


def save_user_cache(nickname, image_path):
    try:
        users = load_user_cache()
        cache_dir = os.path.join(os.path.dirname(CACHE_FILE), "cache_images")
        os.makedirs(cache_dir, exist_ok=True)

        # 프로필 이미지 복사
        new_path = os.path.join(cache_dir, f"{nickname}.png")
        if os.path.abspath(image_path) != os.path.abspath(new_path):
            shutil.copy(image_path, new_path)
        shutil.copy(image_path, new_path)
        users[nickname] = new_path

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f" 캐시 저장 실패: {e}")


"닉네임 등록 화면"


class NicknameDialog(QDialog):
    def __init__(self, existing_usernames=None):
        super().__init__()
        self.setWindowTitle("닉네임 입력")
        self.setFixedSize(300, 200)
        self.image_path = None
        self.cached_users = load_user_cache() or {}
        self.existing_usernames = existing_usernames or set()  # 중복 검사용 닉네임 목록

        layout = QVBoxLayout()
        self.label = QLabel("닉네임을 선택하거나 새로 입력하세요")

        # 닉네임 선택 콤보박스 + 입력
        self.nickname_combo = QComboBox()
        self.nickname_combo.setEditable(True)
        self.nickname_combo.addItems(self.cached_users.keys())
        self.nickname_combo.setPlaceholderText("예: 다니")

        self.nickname_combo.currentIndexChanged.connect(self.load_selected_user)

        self.image_button = QPushButton("프로필 이미지 선택")
        self.image_button.clicked.connect(self.select_image)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self.label)
        layout.addWidget(self.nickname_combo)
        layout.addWidget(self.image_button)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        color: #333;
                    }

                    QLineEdit {
                        background-color: #f9f9f9;
                        border: 1px solid #ccc;
                        border-radius: 6px;
                        padding: 5px;
                    }

                    QPushButton {
                        background-color: #FFAE0F;
                        color: white;
                        border: none;
                        padding: 8px 14px;
                        border-radius: 6px;
                        font-size: 13px;
                    }

                    QPushButton:hover {
                        background-color: #EE9F05;
                    }

                    QDialogButtonBox QPushButton {
                        background-color: white;
                        border: 1px solid #ccc;
                        border-radius: 6px;
                        padding: 6px 12px;
                        color: #333;
                        font-size: 13px;
                    }

                    QDialogButtonBox QPushButton:hover {
                        background-color: #f2f2f2;
                        border: 1px solid #bbb;
                    }
                """)

    def load_selected_user(self, index):
        nickname = self.nickname_combo.currentText()
        if nickname in self.cached_users:
            self.image_path = self.cached_users[nickname]
            self.image_button.setText("자동 선택됨")

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "이미지 선택", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            self.image_button.setText("✅ 선택됨")

    def get_nickname_and_image(self):
        while True:
            if self.exec_() != QDialog.Accepted:
                return None, None  # 사용자가 취소한 경우 종료

            nickname = self.nickname_combo.currentText().strip()

            # ❌ 금지된 닉네임 검사
            if nickname.lower() == "none":
                QMessageBox.warning(self, "입력 오류", "'None'은 닉네임으로 사용할 수 없습니다.")
                continue  # 다시 입력

            # ❌ 중복 닉네임 검사
            if nickname in self.existing_usernames:
                QMessageBox.warning(self, "중복 닉네임", f"'{nickname}' 닉네임은 이미 사용 중입니다.")
                continue  # 다시 입력

            # ✅ 캐시된 닉네임일 경우 이미지 자동 보완
            if nickname in self.cached_users and self.image_path is None:
                self.image_path = self.cached_users[nickname]
                self.image_button.setText("자동 선택됨")

            # ✅ 새 닉네임 + 이미지 선택 안 된 경우 기본 이미지
            if nickname and self.image_path is None:
                default_image_path = resource_path("images/face.png")
                self.image_path = default_image_path
                print(f"✅ 이미지 미선택 → 기본 이미지로 대체: {self.image_path}")

            if nickname and self.image_path:
                save_user_cache(nickname, self.image_path)
                return nickname, self.image_path


class PopupNotification(QWidget):
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)

        self.label = QLabel(self)
        self.label.setFixedSize(280, 60)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.label.setTextInteractionFlags(Qt.NoTextInteraction)

        self.label.setText(f"""
            <span style="color:#FF9500; font-weight:500;">{title}</span><br>
            <span style="color:#333;">{message}</span>
        """)

        self.label.setStyleSheet("""
            QLabel {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #ccc;
            }
        """)

        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60
        self.move(QPoint(x, y))

        self.setWindowOpacity(0.0)
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()

        QTimer.singleShot(2500, self.close)


class ChatWidget(QWidget):
    message_received = pyqtSignal(str, str)  # sender, message
    on_announced = pyqtSignal(str, str)  # sender, message

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                asyncio.create_task(self._send_file_task(file_path))

    def __init__(self, username: str, image_path=None, server_url: str = "ws://localhost:30006/ws/", parent=None):
        super().__init__(parent)
        self.username = username
        self.server_url = server_url
        self.websocket = None  # 여기선 새로 연결함
        self.profile_image = None
        self.profiles = {}  # 유저명 -> 프로필 이미지
        self.setWindowTitle("✨ 다니 알림방")
        self.setAcceptDrops(True)  # ← 드래그앤드롭 허용

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.message_map = {}  # reply_id → {"bubble": QLabel, "frame": QFrame}
        self.thinking_timers = {}  # reply_id → QTimer

        self.image_history = []  # base64 디코딩된 QPixmap 리스트
        self.current_image_index = 0  # 현재 미리보기 인덱스
        self.current_user_list = {}  # 현재 유저 리스트

        """ 메시치 창이 항상 위"""
        # self.setWindowFlags(
        #    QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)

        # 폰트 설정
        font_path = os.path.join("fonts", "NanumSquareRoundR.ttf")
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)
            self.setFont(QFont("NanumSquareRoundR", 10))

        self.resize(500, 550)  # 창 크기 조절 가능하게 변경
        self.setStyleSheet("""
            QWidget {
            background-color: #f5f5f5;
            border-radius: 15px;
        }
        """)

        # 유저 목록 토글 버튼 추가
        self.user_toggle_button = QPushButton("▼ 접속 중 유저 보기")
        self.user_toggle_button.setCheckable(True)
        self.user_toggle_button.setChecked(False)
        self.user_toggle_button.clicked.connect(self.toggle_user_list)
        self.user_toggle_button.setStyleSheet("""
            QPushButton {
        background-color: #eee;
        border: 1px solid #ccc;
        padding: 4px;
        font-size: 12px;
        border-radius: 5px;
        }
        """)

        self.layout.addWidget(self.user_toggle_button)

        # 🧑‍🤝‍🧑 유저 리스트 (QListWidget)
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("""
                QListWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    padding: 5px;
                    font-size: 13px;
                }
            """)
        self.user_list.itemDoubleClicked.connect(self.open_private_chat)  # 더블클릭하여 개인 채팅방 개설

        # QScrollArea에 유저 리스트 삽입
        self.user_list_area = QScrollArea()
        self.user_list_area.setWidgetResizable(True)
        self.user_list_area.setFixedHeight(100)
        self.user_list_area.setWidget(self.user_list)
        self.user_list_area.hide()  # ⛔ 기본값: 안 보이게
        self.layout.addWidget(self.user_list_area)

        # 접속 중 유저 표시
        self.user_list_label = QLabel("접속 중: ", self)
        self.user_list_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                padding: 6px;
                font-size: 12px;
                color: #333;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
            """)
        self.layout.addWidget(self.user_list_label)

        # ✅ 채팅 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background-color: f5f5f5;
                    }
                """)

        self.scroll_content = QWidget()
        self.chat_layout = QVBoxLayout(self.scroll_content)
        self.chat_layout.setSpacing(0)
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

        # ✅ 메시지 입력창과 버튼
        input_layout = QHBoxLayout()
        self.file_button = QPushButton("📤")
        self.file_button.setFixedSize(40, 30)
        self.file_button.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        font-size: 18px;
                    }
                    QPushButton:hover {
                        background-color: #f2f2f2;
                        border: 1px solid #bbb;
                    }
                    QPushButton:pressed {
                        background-color: #e6e6e6;
                        border: 1px solid #aaa;
                    }
                """)
        self.file_button.clicked.connect(self.send_file)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("메시지를 입력하세요.")
        self.input_line.setStyleSheet("""
                    QLineEdit {
                        background-color: white;
                        border-radius: 10px;
                        padding: 6px;
                        font-size: 14px;
                        border: 1px solid #ccc;
                        margin-right: 10px;
                    }
                """)

        self.send_button = QPushButton("전송")
        self.send_button.setStyleSheet("""
                    QPushButton {
                        background-color: #FFAE0F;
                        border-radius: 10px;
                        padding: 10px 20px;
                        font-size: 14px;
                        color: white;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #EE9F05;
                    }
                """)

        input_layout.addWidget(self.file_button)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(self.send_button)
        # input_layout.addWidget(self.gpt_button)

        self.layout.addLayout(input_layout)
        # self.setLayout(self.layout)

        self.send_button.clicked.connect(self.send_message)
        self.input_line.returnPressed.connect(self.send_message)

        """로딩 문구용 QLABEL 추가"""
        self.loading_label = QLabel("💬 채팅 기록 불러오는 중...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: gray; font-size: 12px; margin: 10px;")
        self.chat_layout.insertWidget(0, self.loading_label)
        self.loading_label.hide()

        # 읽은 시점 반영 위한 상태 변수
        self.history_loaded = False
        self.separator_shown = False
        self.last_received_message_id = None  # 메시지 ID 기반 읽은 위치 초기화
        self.private_chats = {}  # 개인 채팅방 저장용 딕셔너리 초기화
        self.last_read_id = 1  # 마지막 읽은 메시지의 id

        self.input_line.installEventFilter(self)

        nickname_dialog = NicknameDialog(existing_usernames=set(self.current_user_list))
        self.username, image_path = nickname_dialog.get_nickname_and_image()
        print("current_user_list", self.current_user_list)
        # 닉네임 입력이 안 되었을 때
        if not self.username:
            mood = random.choice(dani_moods)
            number = random.randint(100, 999)
            self.username = f"{mood}_다니{number}"

        if image_path:
            self.profile_image = resize_image_to_base64(image_path)

    def toggle_user_list(self):
        if self.user_toggle_button.isChecked():
            self.user_toggle_button.setText("▲ 접속 중 유저 숨기기")
            self.user_list_area.show()
        else:
            self.user_toggle_button.setText("▼ 접속 중 유저 보기")
            self.user_list_area.hide()

    async def check_nickname_available(self, nickname):
        async with websockets.connect(self.server_url) as ws:
            await ws.send(json.dumps({"type": "validate", "nickname": nickname}))
            response = await ws.recv()
            result = json.loads(response)
            return result.get("available", False)

    def set_loading_state(self, loading: bool):
        if loading:
            print("로딩 중입니다..")
            self.loading_label.show()

        else:
            print("로딩이 완료되었습니다.")
            self.loading_label.hide()

    async def _send_file_task_from_data(self, filename, data_b64, ext):
        try:
            packet = {
                "sender": self.username,
                "message": f"[파일] {filename}",
                "profile": self.profile_image,
                "file": {
                    "name": filename,
                    "data": data_b64,
                    "type": ext
                }
            }
            await self.websocket.send(json.dumps(packet))
            self.add_file_message(filename, data_b64, ext, from_self=True, profile=self.profile_image)

        except Exception as e:
            self.add_message(f"❌ 파일 전송 실패: {e}")

    def send_clipboard_image(self, qimage):
        try:
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.WriteOnly)
            qimage.save(buffer, "PNG")  # ✅ QImage를 직접 PNG로 저장
            data = buffer.data()
            data_b64 = base64.b64encode(data).decode("utf-8")

            filename = f"clipboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            asyncio.create_task(self._send_file_task_from_data(filename, data_b64, ".png"))
            print("📎 클립보드 이미지 전송됨")
        except Exception as e:
            print(f"❌ 클립보드 이미지 처리 실패: {e}")

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress:
            # Ctrl+V 입력 감지
            if event.matches(QtGui.QKeySequence.Paste):
                clipboard = QApplication.clipboard()
                if clipboard.mimeData().hasImage():
                    image = clipboard.image()
                    if not image.isNull():
                        # 이미지를 base64로 인코딩하여 전송
                        self.send_clipboard_image(image)
                        return True  # 이벤트 소비
        return super().eventFilter(source, event)

    def show_gpt_input_box(self):
        print("show_gpt_input_box 호출")
        self.gpt_frame = QFrame(self)
        self.gpt_frame.setStyleSheet("background: #f9f9f9; border: 1px solid #ccc; border-radius: 10px;")
        layout = QVBoxLayout(self.gpt_frame)

        self.gpt_input = QLineEdit()
        self.gpt_input.setPlaceholderText("GPT에게 물어보세요...")
        self.gpt_input.returnPressed.connect(self.send_gpt_question)

        self.gpt_answer = QLabel()
        self.gpt_answer.setWordWrap(True)
        self.gpt_answer.setStyleSheet("padding: 8px; font-size: 13px;")

        layout.addWidget(self.gpt_input)
        layout.addWidget(self.gpt_answer)

        self.chat_layout.addWidget(self.gpt_frame)

    """gpt 질문 전송 -> 서버로 중계"""

    async def send_gpt_question(self):
        print("send_gpt_question 호출!")
        question = self.gpt_input.text().strip()
        if not question:
            return

        await self.websocket.send(json.dumps({
            "type": "chatbot",
            "message": question

        }))
        self.gpt_input.setDisabled(True)
        self.gpt_input.setText("⌛ 응답 기다리는 중...")

    async def connect(self):
        try:

            self.websocket = await websockets.connect(
                self.server_url + self.username, max_size=None)  # ← 제한 해제

            # 알림용 소켓 받아서 연결
            # uri = f"ws://localhost:30006/ws/{self.username}"
            # self.websocket = await websockets.connect(uri)
            print("🆕 WebSocket 새로 연결")

            await self.receive_messages()
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            self.add_message(f"❌ 연결 실패: {e}", is_system=True)

    @asyncSlot()
    async def send_message(self):
        message = self.input_line.text().strip()
        # if not message:
        #    return #공백 메시지 차단
        if message and self.websocket:
            packet = {
                "sender": self.username,
                "message": message,
                "profile": self.profile_image,
            }

            asyncio.create_task(self._safe_send(json.dumps(packet)))

            self.add_message(message, from_self=True, profile=self.profile_image)
            self.input_line.clear()

            # 센트 시그널 발신 [공지] 키워드 적용
            if message.startswith("@"):
                # message = message[1:]
                # self.message_received.emit(self.username,message)
                self.on_announced.emit(self.username, message)

    async def _safe_send(self, data: str):
        try:
            # closed 속성이 없으면 기본값으로 False 반환
            if self.websocket and not getattr(self.websocket, "closed", False):
                await self.websocket.send(data)
            else:
                print("⚠️ WebSocket 연결이 닫혀 있어 메시지 전송 생략")
        except ConnectionClosed as e:
            self.add_message(f"❌ 전송 오류: {e}")
            if getattr(e, "code", None) == 1000:
                print("✅ WebSocket 정상 종료 상태에서 전송 시도됨 → 무시")
            else:
                print(f"❌ WebSocket 연결 종료됨: {e}")
        except Exception as e:
            print(f"❌ 전송 중 예외 발생: {e}")

    @asyncSlot()
    async def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "All Files (*)")
        if file_path:
            loop = asyncio.get_event_loop()
            loop.create_task(self._send_file_task(file_path))

    async def _send_file_task(self, file_path):
        try:
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")

            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()

            packet = {
                "sender": self.username,
                "message": f"[파일] {filename}",
                "profile": self.profile_image,
                "file": {
                    "name": filename,
                    "data": data,
                    "type": ext
                }
            }

            await self.websocket.send(json.dumps(packet))
            self.add_file_message(filename, data, ext, from_self=True, profile=self.profile_image)

        except Exception as e:
            self.add_message(f"❌ 파일 전송 실패: {e}")

    async def receive_messages(self):
        # 현재 날짜 기준 이번 주 월요일과 일요일 계산
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())  # 월요일
        end_of_week = start_of_week + timedelta(days=6)  # 일요일

        try:
            async for raw in self.websocket:
                packet = json.loads(raw)

                """유저 리스트 갱신 처리"""
                if packet.get("type") == "user_list":
                    self.update_user_list(packet["users"])
                    self.current_user_list = packet["users"]
                    print("current_userl_lsit", self.current_user_list)

                """개인톡 분기 처리"""
                if packet["type"] == "private_room":
                    sender = packet["sender"]
                    receiver = packet["receiver"]
                    msg = packet["message"]
                    profile = packet.get("profile")

                    if not profile:
                        profile = self.profiles.get(sender)

                    # 현재 내가 수신자 or 발신자인 경우만 해당 창 띄우기
                    if receiver == self.username or sender == self.username:
                        partner = sender if sender != self.username else receiver
                        if partner not in self.private_chats:
                            self.open_private_chat(QListWidgetItem(partner))
                        self.private_chats[partner].receive_message(sender, msg)

                # if packet["type"] == "chatbot_response":
                # self.dani.react_to_message("GPT", packet["message"])  # 또는 채팅창에 표시




                if "sender" in packet and "message" in packet:
                    sender = packet["sender"]
                    message = packet["message"]
                    profile = packet.get("profile")

                    # 👉 공지 여부 판단
                    is_notice = message.startswith("@")
                    if is_notice:
                        message = f"🎯 공지\n{message[1:].strip()}"

                    if not profile:
                        profile = self.profiles.get(sender)

                    is_me = (sender == self.username)
                    is_private = packet.get("type") == "private_room"

                    if sender != self.username:
                        prefix = f"🔒[개인톡] {sender}" if is_private else sender
                        self.add_message(
                            f"{prefix}: {message}",
                            from_self=False,
                            profile=profile,
                            is_system=False,
                            is_private=is_private,
                            is_notice=is_notice, # ✅ 공지 여부 전달
                        )

                    # 히스토리 이후, 처음 도착한 타인 메세지에 구분선 삽입
                    if self.history_loaded and not is_me and not self.separator_shown:
                        self.add_separator()
                        self.separator_shown = True

                    file_info = packet.get("file")
                    if file_info:
                        if sender == self.username:
                            continue

                        self.add_file_message(
                            filename=file_info["name"],
                            data_b64=file_info["data"],
                            ext=os.path.splitext(file_info["name"])[1].lower(),
                            from_self=False,
                            profile=profile,
                            sender_name=sender,  # 여기 추가
                        )
                        continue

                    self.profiles[sender] = profile
                    if sender != self.username:
                        # self.add_message(
                        #   f"{sender}: {message}", from_self=False, profile=profile,
                        # is_system = False)
                        # 시그널 발신: 나 포함 모든 메시지에 대해 발신
                        """
                         @공지를 채팅방안에서 받았을 때, emit!! ,이건 필요 없지. 공지는 채팅방과 상관 없으니"""
                        if message.startswith("@"):
                            print("전체 발신")
                            # message = message[1:]
                            # self.message_received.emit(sender, message)
                            # self.on_announced.emit(sender, message)

                        popup = PopupNotification(sender, message)
                        popup.show()



                # type에 히스토리 있을 시, 이전 대화 불러옴(당일 한정)
                elif packet.get("type") == "history":
                    self.set_loading_state(True)  # ⬅️ 로딩 시작 표시

                    self.last_read_id = packet.get("last_read_id")

                    for i, msg in enumerate(packet["messages"]):
                        message_id = msg["id"]
                        is_me = (msg["sender"] == self.username)

                        # 내 메시지는 sender 없이 메시지만
                        if is_me:
                            text = msg['message']
                        else:
                            text = f"{msg['sender']}: {msg['message']}"
                        self.add_message(
                            text=text,
                            from_self=is_me,
                            profile=msg.get("profile"),
                            timestamp=msg.get("timestamp"),  # time 추가
                            is_system=False

                        )

                        if self.last_read_id is not None and message_id == self.last_read_id:
                            print(f"👁 구분선 삽입 위치: {i}")
                            self.add_separator()

                    # 상태 초기화
                    self.history_loaded = True
                    self.separator_shown = False
                    self.set_loading_state(False)  # ⬅️ 로딩 끝

                    # 최하단 말고, 구분선 위치로 이동
                    QTimer.singleShot(1000, self.scroll_to_separator)

                # 메시지 수신할 때마다 마지막 ID 저장
                # 안전하게 접근하기
                self.last_received_message_id = packet.get("id", self.last_received_message_id)

        except Exception as e:
            self.add_message(f"❌ 연결 종료: {e}", is_system=True)
            print(f"❌ 연결 종료: {e}")

    """ 오버라이드해서 종료 직전에 읽은 메시지 수를 서버에 전송"""

    def closeEvent(self, event):
        event.ignore()  # ❗ 먼저 무시해두고 (바로 닫히는 것 방지)

        async def send_and_exit():
            # 1. 마지막 읽은 메시지 ID 전송
            if self.websocket and self.last_received_message_id:
                try:
                    await self._safe_send(json.dumps({
                        "type": "update_read_id",
                        "username": self.username,
                        "message_id": self.last_received_message_id
                    }))
                    print("📤 마지막 읽은 ID 전송 완료")
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"❌ 전송 실패: {e}")
            # 2. 웹소켓 연결 안전 종료
            if self.websocket:
                try:
                    if hasattr(self.websocket, "closed"):
                        if not self.websocket.closed and not self.websocket.close_code:
                            await self.websocket.close()
                            print("✅ WebSocket 정상 종료")
                    else:
                        await self.websocket.close()
                        print("✅ WebSocket 강제 종료")
                except Exception as e:
                    print(f"❌ WebSocket 종료 실패: {e}")

            # 3. 창 닫기 (한 번만)
            def really_close():
                print("ChatWidget 정상 종료")
                event.aceept()  # QT에게 창 닫기 허용

            # 창 안전하게 닫기 (메인 스레드에서)
            # QTimer.singleShot(0, really_close)

        try:
            # 현재 이벤트 루프에 비동기 연결 해제 작업 등록
            asyncio.create_task(send_and_exit())
            # asyncio.create_task(self.disconnect())
        except Exception as e:
            print(f" 연결 해제 중 오류: {e}")
        event.accept()  # 창 닫기 허용

    async def disconnect(self):
        """WebSocket 연결 종료 함수 (버전 호환 고려)"""
        if self.websocket:
            try:
                # websockets v10 이상 기준: is_closing()
                if not self.websocket.closed and not self.websocket.close_code:
                    await self.websocket.close()
                    print("✅ WebSocket 연결 해제 완료")
                else:
                    print("ℹ️ 이미 종료된 연결입니다.")
            except AttributeError:
                # 버전에 따라 closed 속성이 없을 수 있으므로 그냥 close()만 시도
                await self.websocket.close()
                print("✅ WebSocket 강제 종료 완료")

    """구분선 함수 정의"""

    def add_separator(self):
        print("✅ 구분선 추가됨")
        separator = QLabel("🔽 이후 새 메시지")
        separator.setAlignment(Qt.AlignCenter)
        separator.setStyleSheet("color: #999; font-size: 11px; margin: 8px;")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, separator)

        self.separator_label = separator  # 나중에 스크롤 위치 확인용으로 저장
        print("✅ separator_label 설정 완료")

        # 삽입 후 렌더링 완료되면 스크롤 이동
        QTimer.singleShot(2000, self.scroll_to_separator)

    def add_message(self, text, reply_id=None, from_self=False, is_system=False, profile=None, timestamp=None,
                    is_private=False, is_notice=False):
        if timestamp:
            try:
                # ✅ ISO 포맷 대응: 'T'를 공백으로 바꾸고 마이크로초 제거
                time_str = datetime.strptime(timestamp.split('.')[0].replace('T', ' '), "%Y-%m-%d %H:%M:%S").strftime(
                    "%H:%M")
            except Exception as e:
                print(f"⛔ timestamp 파싱 실패: {timestamp}, 오류: {e}")
                time_str = timestamp  # 형식이 맞지 않으면 그대로 출력
        else:
            time_str = datetime.now().strftime("%H:%M")

        # 이름: 메시지 형식일 경우, 분리
        if not from_self and not is_system and ":" in text:
            sender, message = text.split(":", 1)
        else:
            message = text

        """ gpt 로딩 후 말풍선 내용 교체"""
        # 👉 reply_id가 있을 경우 기존 말풍선을 찾아 업데이트만 수행
        if reply_id and hasattr(self, "message_map") and reply_id in self.message_map:
            # 기존 QLabel 가져와서 텍스트만 교체

            bundle = self.message_map[reply_id]
            bubble = bundle["bubble"]

            bubble.setText(message.strip())  # 텍스트 교체

            # 타이머 중단
            if reply_id in self.thinking_timers:
                self.thinking_timers[reply_id].stop()
                del self.thinking_timers[reply_id]

            return  # 업데이트만 하고 말풍선 새로 추가는 하지 않음

        # 말풍선 + 시간
        bubble = QLabel(message.strip())
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(340)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        bubble.setStyleSheet(f"""
            background-color: {
                '#FFCF71' if from_self else (
                '#D6E4FF' if is_notice else (
                '#FFF7E6' if is_private else '#ffffff'))};
            padding: 8px 8px;
            border-radius: 14px;
            color: black;
        """)
        bubble.adjustSize()

        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: gray; font-size: 10px; margin: 1px;")

        # 상대방 이름 라벨 (본인 메시지는 표시 안 함)
        if not from_self and not is_system:
            name_label = QLabel(sender)
            name_label.setStyleSheet("color: black; font-size: 11px; margin-bottom: 0;")
            layout_name = QVBoxLayout()
            layout_name.setContentsMargins(10, 0, 10, 0)
            layout_name.addWidget(name_label, alignment=Qt.AlignLeft)
            self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout_name)

        # 말풍선 + 시간 묶기
        bubble_container = QVBoxLayout()
        bubble_container.addWidget(bubble)
        bubble_container.addWidget(time_label, alignment=Qt.AlignRight if from_self else Qt.AlignLeft)

        # 프로필 이미지
        profile_label = QLabel()
        profile_label.setFixedSize(36, 36)

        if profile:
            try:
                # base64 길이 보정
                missing_padding = len(profile) % 4
                if missing_padding:
                    profile += '=' * (4 - missing_padding)

                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(profile))
            except Exception as e:
                print(f"❌ 프로필 이미지 디코딩 실패: {e}")
                default_path = resource_path("images/face.png")  # ✅ 여기 수정!
                pixmap = QPixmap(default_path)
        else:
            default_path = resource_path("images/face.png")  # ✅ 여기도 수정!
            pixmap = QPixmap(default_path)
            if pixmap.isNull():
                print("❌ QPixmap failed to load face.png at", default_path)

        profile_label.setPixmap(pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # 말풍선 프레임 구성
        bubble_frame = QFrame()
        layout = QHBoxLayout(bubble_frame)
        layout.setContentsMargins(10, 4, 10, 4)

        if from_self:
            layout.addStretch()
            layout.addLayout(bubble_container)
            layout.addWidget(profile_label)
        else:
            layout.addWidget(profile_label)
            layout.addLayout(bubble_container)
            layout.addStretch()

        # 말풍선 추가
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble_frame)

        # reply_id가 있으면 해당 말풍선을 기억해 둠 (GPT 응답 시 업데이트용)
        if reply_id:
            if not hasattr(self, "message_map"):
                self.message_map = {}  # 최초 생성
            self.message_map[reply_id] = {
                "bubble": bubble,
                "frame": bubble_frame
            }
            self.start_thinking_animation(reply_id)  # 👈 여기에 애니메이션 시작 호출!

        # 스크롤 맨 아래로
        QTimer.singleShot(10, self.scroll_to_bottom)

    """깜빡이는 함수 추가"""

    def start_thinking_animation(self, reply_id):
        if reply_id not in self.message_map:
            return

        bubble = self.message_map[reply_id]["bubble"]
        self.thinking_dots = 0  # 점 개수 초기화

        def update_text():
            self._thinking_dots = (self.thinking_dots + 1) % 4
            dots = "." * self._thinking_dots
            bubble.setText(f"⏳ 답변을 생성 중입니다{dots}")

        timer = QTimer(self)
        timer.timeout.connect(update_text)
        timer.start(500)
        self.thinking_timers[reply_id] = timer

    """사진 추가"""

    def add_file_message(self, filename, data_b64, ext, from_self=False, profile=None, sender_name=None):
        time_str = datetime.now().strftime("%H:%M")
        is_image = ext in [".png", ".jpg", ".jpeg", ".gif"]

        # 이름 라벨 처리 (본인이 보낸 게 아닐 때만, 그리고 sender_name이 존재할 때만)
        if not from_self and sender_name:
            name_label = QLabel(sender_name)
            name_label.setStyleSheet("color: black; font-size: 11px; margin-bottom: 0;")
            layout_name = QVBoxLayout()
            layout_name.setContentsMargins(10, 0, 10, 0)
            layout_name.addWidget(name_label, alignment=Qt.AlignLeft)
            self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout_name)

        profile_label = QLabel()
        profile_label.setFixedSize(36, 36)
        if profile:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(profile))
        else:
            default = QPixmap(resource_path("images/face.png"))
            pixmap = default
        profile_label.setPixmap(pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 4, 10, 4)

        if is_image:
            image_container = QFrame()
            image_container.setStyleSheet("border: none;")
            image_layout = QVBoxLayout(image_container)
            image_layout.setContentsMargins(0, 0, 0, 0)

            image_label = QLabel()
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(data_b64))

            # 이미지 히스토리에 추가
            self.image_history.append(pixmap)

            image_label.setPixmap(pixmap.scaledToWidth(180))
            image_label.setCursor(Qt.PointingHandCursor)

            # 현재 인덱스를 캡쳐해서 넘김
            index = len(self.image_history) - 1
            image_label.mousePressEvent = lambda e, idx=index: self.show_full_image(idx)

            image_layout.addWidget(image_label)
            layout.addWidget(image_container)

            file_label = QLabel(f"💾 {filename}")
            file_label.setStyleSheet("color: blue; text-decoration: underline;")
            file_label.setCursor(Qt.PointingHandCursor)
            file_label.mousePressEvent = lambda e: self.save_file(filename, data_b64)
            layout.addWidget(file_label)
        else:
            # ✅ 이미지가 아닌 경우도 파일명은 표시
            file_label = QLabel(f"📄 {filename}")
            file_label.setStyleSheet("color: blue; text-decoration: underline;")
            file_label.setCursor(Qt.PointingHandCursor)
            file_label.mousePressEvent = lambda e: self.save_file(filename, data_b64)
            layout.addWidget(file_label)

        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(time_label, alignment=Qt.AlignRight if from_self else Qt.AlignLeft)

        bubble_frame = QFrame()
        bubble_layout = QHBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(10, 4, 10, 4)

        if from_self:
            bubble_layout.addStretch()
            bubble_layout.addWidget(content_widget)
            bubble_layout.addWidget(profile_label)
        else:
            bubble_layout.addWidget(profile_label)
            bubble_layout.addWidget(content_widget)
            bubble_layout.addStretch()

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble_frame)
        QTimer.singleShot(10, self.scroll_to_bottom)

    # 이미지 눌렀을 때 크게 해서 미리보기
    def show_full_image(self, index):
        self.current_image_index = index

        class ImageDialog(QDialog):
            def __init__(dialog_self):
                super().__init__(self)
                dialog_self.setWindowTitle("이미지 보기")
                dialog_self.setFixedSize(600, 640)
                dialog_self.setModal(True)

                # 레이아웃 설정
                dialog_self.layout = QVBoxLayout(dialog_self)
                dialog_self.layout.setContentsMargins(10, 10, 10, 10)
                dialog_self.layout.setSpacing(10)

                # 이미지 라벨
                dialog_self.label = QLabel()
                dialog_self.label.setAlignment(Qt.AlignCenter)
                dialog_self.layout.addWidget(dialog_self.label)

                # 인덱스 표시 라벨
                dialog_self.page_label = QLabel()
                dialog_self.page_label.setAlignment(Qt.AlignCenter)
                dialog_self.page_label.setStyleSheet("color: black; font-size: 12px;")
                dialog_self.layout.addWidget(dialog_self.page_label)

                dialog_self.update_image()

            def update_image(dialog_self):
                pixmap = self.image_history[self.current_image_index]
                dialog_self.label.setPixmap(pixmap.scaled(
                    580, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation))

                # 인덱스 정보 표시
                dialog_self.page_label.setText(
                    f"{self.current_image_index + 1} / {len(self.image_history)}"
                )

            def keyPressEvent(dialog_self, event):
                if event.key() == Qt.Key_Right and self.current_image_index < len(self.image_history) - 1:
                    self.current_image_index += 1
                    dialog_self.update_image()
                elif event.key() == Qt.Key_Left and self.current_image_index > 0:
                    self.current_image_index -= 1
                    dialog_self.update_image()
                elif event.key() == Qt.Key_Escape:
                    dialog_self.reject()

            def wheelEvent(dialog_self, event):
                delta = event.angleDelta().y()
                if delta < 0 and self.current_image_index < len(self.image_history) - 1:
                    self.current_image_index += 1
                    dialog_self.update_image()
                elif delta > 0 and self.current_image_index > 0:
                    self.current_image_index -= 1
                    dialog_self.update_image()

        dialog = ImageDialog()
        dialog.exec_()

    def save_file(self, filename, data_b64):
        save_path, _ = QFileDialog.getSaveFileName(self, "파일 저장", filename)

        if not save_path:
            return

        _, ext = os.path.splitext(filename)
        if ext and not save_path.lower().endswith(ext):
            save_path += ext

        try:
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(data_b64))
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")

    def update_user_list(self, users):
        self.user_list.clear()

        # ✅ None 제거 + 자기 자신 제거
        # "None"(문자열), None(객체), 자기 자신 제거
        filtered_users = [user for user in users if user and user != "None" and user != self.username]

        for user in filtered_users:
            self.user_list.addItem(user)
        self.user_list_label.setText(f"접속 중: {', '.join(filtered_users)}")

    # 채팅방 개설함수
    def open_private_chat(self, item):
        partner = item.text()
        chat_window = PrivateChatWindow(self.username, partner, self.websocket)
        chat_window.setWindowTitle(f"{self.username} ↔ {partner}")
        chat_window.show()
        self.private_chats[partner] = chat_window

    def scroll_to_bottom(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        if scroll_bar:
            scroll_bar.setValue(scroll_bar.maximum())

    # 스크롤 함수 추가: 구분선 위치로 이동
    def scroll_to_separator(self):
        """
        이후 새 메시지 라벨이 보이도록 스크롤을 이동
        :return:
        """
        print("scroll_to_separator 호출")
        if hasattr(self, "separator_label") and self.separator_label is not None:
            print("🔽 구분선까지 이동 시도")
            self.scroll_area.ensureWidgetVisible(self.separator_label, yMargin=20)
        else:
            print("⚠️ 구분선이 아직 존재하지 않음!")

    # 수신 전용 함수
    def receive_announcement(self, sender, message):
        # popup 등 표시
        self.add_message(f"[공지] {sender}: {message}", from_self=False)


class PrivateChatWindow(QDialog):
    def __init__(self, sender, receiver, websocket):
        super().__init__()
        self.sender = sender
        self.receiver = receiver
        self.websocket = websocket

        self.setWindowTitle(f"{self.sender} ↔ {self.receiver}")
        self.resize(400, 300)

        self.chat_area = QTextBrowser()
        self.input = QLineEdit()
        self.send_button = QPushButton("보내기")

        layout = QVBoxLayout()  # ✅ 수직 레이아웃 명확히 지정
        self.setLayout(layout)
        layout.addWidget(self.chat_area)
        layout.addWidget(self.input)
        layout.addWidget(self.send_button)

        self.send_button.clicked.connect(self.send_private_message)
        self.input.returnPressed.connect(self.send_private_message)

    def send_private_message(self):
        msg = self.input.text().strip()
        if msg:
            packet = {
                "type": "private_room",
                "sender": self.sender,
                "receiver": self.receiver,
                "message": msg
            }
            asyncio.create_task(self.websocket.send(json.dumps(packet)))
            # self.chat_area.append(f"나: {msg}")
            self.input.clear()

    def receive_message(self, sender, message):  # ✅ 메서드명 수정 (recieve → receive)
        self.chat_area.append(f"{sender}: {message}")

    """닫기 버튼시 소켓 종료"""

    async def disconnect(self):
        """WebSocket 연결 종료 함수 (버전 호환 고려)"""
        if self.websocket:
            try:
                # websockets v10 이상 기준: is_closing()
                if not self.websocket.closed and not self.websocket.close_code:
                    await self.websocket.close()
                    print("✅ WebSocket 연결 해제 완료")
                else:
                    print("ℹ️ 이미 종료된 연결입니다.")
            except AttributeError:
                # 버전에 따라 closed 속성이 없을 수 있으므로 그냥 close()만 시도
                await self.websocket.close()
                print("✅ WebSocket 강제 종료 완료")

    """
    def closeEvent(self, event):
        #창 닫을 때 Websocket 연결 종료
        try:
            # 현재 이벤트 루프에 비동기 연결 해제 작업 등록
            asyncio.create_task(self.disconnect())
        except Exception as e:
            print(f" 연결 해제 중 오류: {e}")
        event.accept()  # 창 닫기 허용
    """