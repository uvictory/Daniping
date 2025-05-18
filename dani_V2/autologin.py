import sys, os, json
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, Qt
from cryptography.fernet import Fernet

# resource_path() 함수 추가
def resource_path(relative_path):
    """PyInstaller 실행환경과 개발환경 모두에서 리소스를 불러올 수 있도록 경로 보정"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 실행 중일 때 생성되는 임시 폴더
    except Exception:
        base_path = os.path.abspath(".")  # 개발환경에서는 현재 경로 기준

    return os.path.join(base_path, relative_path)

CONFIG_FILE = resource_path("credentials.json")
KEY_FILE = resource_path("secret.key")

def load_key(path):
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(Fernet.generate_key())
    with open(path, 'rb') as f:
        return Fernet(f.read())


class AutoLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.fernet = load_key(resource_path("secret.key"))
        self.setWindowTitle("전자결재 자동 로그인")
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # 🌐 웹뷰
        self.webview = QWebEngineView()
        self.webview.load(QUrl("http://192.168.50.3:10000/index.jsp"))
        self.webview.loadFinished.connect(self.on_page_loaded)
        self.webview.urlChanged.connect(self.handle_login_redirect) # url 변경 감지 추가

        # ✅ 커스텀 로그인 버튼
        self.login_button = QPushButton("🔐 로그인 및 저장")
        self.login_button.clicked.connect(self.handle_login)

        # ✅ 시인성 높은 스타일 적용
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #005BBB;
            }
        """)

        layout.addWidget(self.webview)
        layout.addWidget(self.login_button)

        self.login_button.setDefault(True)

        # ✅ Enter 키 입력 시 로그인 실행
        self.shortcut = QShortcut(Qt.Key_Return, self)
        self.shortcut.activated.connect(self.login_button.click)    # 직접 클릭 이벤트 발생

        self.setFocusPolicy(Qt.StrongFocus)

        self.auto_login_mode = False # 자동 로그인 여부 플래그
        self.login_successful = False
        self.processing_login = False # 중복 방지용

        self.hook_success = False
        self.hook_timer = QTimer()
        self.hook_timer.setSingleShot(True)
        self.hook_timer.timeout.connect(self.check_hook_failure)
        """메시지박스 중복 방지용 플래그 초기화"""
        self.warned_once = False

        credentials = self.load_credentials("main")
        if credentials:
            print("전자결재 자동 로그인 정보 감지됨: 백그라운드 로그인 시도")
            self.auto_login_mode = True
            self.hide() # 시작 시 창 숨김
        else: # main 정보 없는 경우, 수동 로그인 시도
            print("전자결재 로그인 정보가 없습니다: 수동 로그인 시도")
            self.show()
            

        # 페이지 로딩 완료 시마다 URL 검사
        self.webview.loadFinished.connect(self.check_and_inject)

    def set_hook_success(self):
        self.hook_success = True
        print("✅ 후킹 성공 확인됨")
        self.hook_timer.stop()

    def check_hook_failure(self):
        from Dani import PopupManager  # 필요 시 경로 수정

        if not self.hook_success:
            print("❌ 후킹 실패: 사용자에게 알림 + 재시도")

            PopupManager.show_popup(
                title="❌ 전자결재 감지 실패",
                message="후킹에 실패했어요. 다시 시도합니다!"
            )

            # ✅ 말풍선 알림 (다니에게 전달)
            if hasattr(self, "dani") and self.dani:
                self.dani.show_balloon("❌ 후킹 실패!\n전자결재를 다시 연결할게요!")
            """
            QMessageBox.warning(
                self,
                "(전자결재)알림 감지 실패",
                "알림 시스템이 정상적으로 연결되지 않았습니다.\n전자결재 알림이 수신되지 않을 수 있어요."
            )
            """
            # ✅ 자동 재시도
            self.retry_login()

    def retry_login(self):

        if not self.login_successful:
            if self.isVisible():
                print("⚠️ 로그인 실패, 수동 로그인 중이라 새로고침 생략")
                return
        """후킹 실패 시 로그인부터 다시 시도"""
        print("🔁 후킹 실패 → 자동 로그인 재시작")
        self.login_successful = False
        self.auto_login_mode = True
        self.processing_login = False
        self.hook_success = False
        self.webview.load(QUrl("http://192.168.50.3:10000/index.jsp"))  # 처음 페이지로 재진입

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            print("(전자결재) 🔑 Enter 키 감지 – 커스텀 로그인 버튼 클릭 실행")
            self.login_button.click()

    def on_page_loaded(self):
        self.current_url = self.webview.url().toString()
        # 로그인 실패 대비 타이머 추가 (10초 내 frame.jsp 진입 못하면 복귀)
        if self.auto_login_mode:
            QTimer.singleShot(10000, self.check_login_timeout)

        # ✅ 웹페이지 내 Enter 기본동작 차단
        disable_enter_js = """
        document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();  // ✅ 부모에게 이벤트 전달도 막음
        console.log('⛔ Enter 키 기본 동작 차단됨');
    }
}, true);  // ✅ 캡처 단계에서 처리
"""
        self.webview.page().runJavaScript(disable_enter_js)

        # 기존 로그인 버튼 숨기기
        hide_js = """
        (function() {
            const btn = document.querySelector('.btn_login');
            if (btn) {
            
            //btn.style.display = 'none'; //❌ 클릭 불가
            btn.style.visibility = 'hidden';
            btn.onclick = function(e) { e.preventDefault(); return false; }
            //btn.style.visibility = 'hidden';    // 시각적으로만 숨김
            }
        })();
        """
        self.webview.page().runJavaScript(hide_js)

        # 저장된 ID/PW 있으면 자동 채우기 및 자동 로그인
        credentials = self.load_credentials("main")
        if credentials:
            js = f"""
            (function() {{
                const idInput = document.getElementsByName('Name')[0];
                const pwInput = document.getElementById('Password');
                if (idInput && pwInput) {{
                    idInput.value = "{credentials['id']}";
                    pwInput.value = "{credentials['password']}";
                    console.log("✅ 자동 입력 완료");
                }}
            }})();
            """
            self.webview.page().runJavaScript(js)

            # 자동 로그인 실행
            QTimer.singleShot(1500, self.login_button.click)

    def auto_login(self):
        login_js = """
        (function() {
            if (typeof NameCheck === 'function') {
                NameCheck();
            }else {
                    const btn = document.querySelector('.btn_login a');
                    if (btn) btn.click();
            }
            
            })"""
        self.webview.page().runJavaScript(login_js)

    def check_and_inject(self):

        self.hook_success = False  # 이 시점에 매번 초기화
        self.hook_timer.stop()  # 혹시라도 이전 타이머가 돌고 있다면 정지
        self.hook_timer.start(10000)

        current_url = self.webview.url().toString()
        print(f"(전자결재) 🔍 현재 URL: {current_url}")

        # 실제 업무 페이지로 이동한 이후만 inject 진행
        if "frame.jsp" in current_url:
            print("(전자결재)✅ 페이지 로딩 완료 → JS 삽입 시도")
            with open(resource_path("assets/content.js"), "r", encoding="utf-8") as f:
                js_code = f.read()
                self.webview.page().runJavaScript(js_code)
                print("(전자결재)✔📗🙏 JS 삽입 완료")
                self.hook_timer.start(10000)  # 10초 안에 후킹 성공 신호 안 오면 실패 처리
        else:
            print("(전자결재)⏳ 로그인 중 또는 다른 페이지")

    # 로그인 후 리디렉션 처리
    def handle_login_redirect(self,url):
        url_str = url.toString()
        print("(전자결재)현재 URL:", url_str)

        # ✅ 체크리스트 페이지 감지 → 메인 프레임으로 리디렉션
        if "chklist.jsp" in url_str:
            print("(전자결재)로그인 성공: 체크리스트 페이지 감지됨")
            self.webview.page().runJavaScript(
                """
                location.href = 'http://192.168.50.3:10000/jsp/main/frame.jsp';
                """)
        # ✅ 메인 프레임 페이지 감지 → 로그인 성공 최종 확인
        elif "frame.jsp" in url_str:
            print(" (전자결재)메인 페이지 도달: 후킹/크롤링 시작")
            self.login_successful = True


            # 이후 로직 실행
            self.check_and_inject()

            # ✅ 창이 떠 있는 경우에도 로그인 성공 시 무조건 숨김
            if self.isVisible():
                print("📦(전자결재) 창 숨김 처리 (자동/수동 로그인 모두 대응)")
                self.hide()

    def check_login_timeout(self):

        if not self.login_successful:
            if self.isVisible():
                print("⚠️ 로그인 실패, 수동 로그인 중이라 새로고침 생략")
                return

        if not self.login_successful and not self.warned_once:
            print("(전자결재)로그인 실패 - 다시 창 표시")
            self.show()
            if "index.jsp" not in self.current_url:  # 로그인 페이지일 경우 무시
                QMessageBox.warning(
                    self,
                    "(전자결재)자동 로그인 실패",
                    "자동 로그인에 실패했습니다.\n 수동으로 로그인해 주세요."
                )
                self.warned_once = True  # 이후엔 띄우지 않음

    def handle_login(self):
        # ID/PW를 JS로 추출 후 Python으로 전달
        js = """
        (function() {
            const idInput = document.getElementsByName('Name')[0];
            const pwInput = document.getElementById('Password');
            return {
                id: idInput ? idInput.value : "",
                password: pwInput ? pwInput.value : ""
            };
        })();
        """
        self.webview.page().runJavaScript(js, self.process_login_data)

    def process_login_data(self, data):
        if self.login_successful:
            print("🔁 로그인 성공 상태에서 중복 호출 → 무시")
            return

        # ✅ 이미 로그인 처리가 시작되었으면 중복 처리 방지
        if self.processing_login:
            print("(전자결재)⚠️ 이미 로그인 처리 중 - 중복 호출 방지")
            return
        self.processing_login = True # ✅ 로그인 처리 시작


        id_val = data.get('id', '').strip()
        pw_val = data.get('password', '').strip()

        # ✅ ID/PW 둘 다 채워져 있을 때 → 로그인 시도
        if id_val and pw_val:
            print("id, pw =", id_val, pw_val)
            self.save_credentials("main", id_val, pw_val)


        #if data and data.get('id') and data.get('password'):
            #print("id, pw =",data.get('id'), data.get('password'))
            #self.save_credentials("main", data['id'], data['password'])

            # ✅ JavaScript를 이용해 로그인 함수 실행
            login_js = """
            (function() {
                if (typeof NameCheck === 'function') {
                    NameCheck();
                } else {
                    const btn = document.querySelector('.btn_login a');
                    if (btn) btn.click();
                }
            })();
            """
            self.webview.page().runJavaScript(login_js)
        else:
            # ✅ 입력값이 없고, 자동 로그인 중이 아니라면 → 경고창 표시
            print("(전자결재)⚠️ ID/PW 입력 누락")
            if not self.auto_login_mode:
                QMessageBox.warning(self, "(전자결재)입력 확인", "아이디와 비밀번호를 입력해주세요.")

        # ✅ 2초 후 플래그 초기화 (다시 로그인 시도 가능하게)
        QTimer.singleShot(2000, lambda: setattr(self, "processing_login", False))

    def save_credentials(self, service, user_id, password):
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

        data[service] = {
            "id": self.fernet.encrypt(user_id.encode()).decode(),
            "password": self.fernet.encrypt(password.encode()).decode()
        }

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"(전자결재)✅ [{service}] 정보 저장 완료")

    def load_credentials(self, service):
        if not os.path.exists(CONFIG_FILE):
            return None
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if service not in data:
            return None
        try:
            return {
                "id": self.fernet.decrypt(data[service]["id"].encode()).decode(),
                "password": self.fernet.decrypt(data[service]["password"].encode()).decode()
            }
        except Exception as e:
            print("❌ 복호화 실패:", e)
            """
            # ✅ 사용자에게 알림 표시
            QMessageBox.warning(
                self,
                "(전자결재)자동 로그인 실패",
                "(전자결재)저장된 로그인 정보를 불러오지 못했습니다.\n수동으로 로그인해 주세요."
            )
            """

        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AutoLogin()

    # 자동 로그인 모드가 아닌 경우에만 창을 보여줌
    if not win.auto_login_mode:
        win.show()
    sys.exit(app.exec_())
