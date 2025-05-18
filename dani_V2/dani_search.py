import base64
import json
import os
import sys
from PyQt5.QtWidgets import QMessageBox, QDialog, QLabel, QLineEdit, QFrame
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from PyQt5 import QtCore
# 상단 버튼 레이아웃 제거 후 중앙 정렬용 레이아웃 사용
from PyQt5.QtWidgets import QSpacerItem, QSizePolicy
from cryptography.fernet import Fernet


def get_base_dir():
    if getattr(sys, 'frozen', False):
        # 실행파일(.exe)로 빌드된 경우
        base_dir = os.path.dirname(sys.executable)
    else:
        # 파이썬 스크립트(.py)로 실행 중인 경우
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print(base_dir)
    return base_dir

TODAY_DATA_FILE = os.path.join(get_base_dir(), "today_attendance.json")

# credentials.json 경로 설정
CONFIG_FILE = os.path.join(get_base_dir(), "credentials.json")

# 키 생성
key = Fernet.generate_key()

# 파일로 저장
with open("secret.key", "wb") as f:
    f.write(key)
print("✅ 공통 Fernet 키가 secret.key 파일로 저장되었습니다.")

# 암복호화 도구 초기화
fernet = Fernet(key)


# 암호화 함수
def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

# 복호화 함수
def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()


class BrowserWindow(QWidget):
    dataReady = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dani 로그인')
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        # 버튼 추가
        self.save_button = QPushButton("🔒 로그인 정보 저장")
        self.save_button.setFixedSize(300, 60)  # 버튼 크기 크게 설정
        self.save_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.save_button.clicked.connect(self.save_login_info_clicked)
        # 👉 버튼 비활성화 상태로 시작 (ID/PW 입력 후 활성화)
        self.save_button.setEnabled(False)


        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.save_button, alignment=QtCore.Qt.AlignCenter)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        button_layout.addWidget(self.save_button)

        # 상단 버튼 레이아웃
        self.reset_button = QPushButton("🔄 로그인 정보 재설정")
        self.reset_button.clicked.connect(self.reset_login_info)
        button_layout.addWidget(self.reset_button)


        # 브라우저 뷰

        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        #로그인 정보 로드
        self.login_info = self.load_login_info("insa")

        """
        # ✅ DevTools 창 만들기
        self.devtools_view = QWebEngineView()  # devtools_view를 객체 변수로 저장
        self.browser.page().setDevToolsPage(self.devtools_view.page())

        # ✅ DevTools 창 띄우기
        self.devtools_view.resize(1000, 800)
        self.devtools_view.show()
        
        # ✅ 강제 DevTools 오픈 (진짜로 콘솔 뜨게 함)
        self.browser.page().triggerAction(self.browser.page().InspectElement)
        """
        # 로그인 페이지 띄우기
        self.browser.load(QUrl('http://192.168.50.13:8090/JG_INNER_PJ/login.html'))

        import time
        time.sleep(0.5)
        self.browser.loadFinished.connect(self.after_login_check)

        self.retry_count = 0 # 추출 재시도 횟수

    # ID/PW 입력 감지
    # 로그인 페이작 로드된 후 JS로 ID/PW 상태 감지 후 버튼 활성화
    def enable_save_button_when_ready(self):
        js = '''
        (function(){
            const idInput = document.getElementId('EMP_ID');
            const pwInput = document.getElementById('EMP_PW');
            if (idInput && pwInput) {
                idInput.addEventListener('input',check);
                pwInput.addEventListener('input',check);
        
        }
        function check() {
            const isReady = idInput.value.trim() !== ' && pwInput.value.trim() !== '';
            pyObj.setButtonEnabled(isReady);
        }
        })();
        '''
        self.browser.page().runJavaScript(js)

    # 오늘 데이터 저장
    def save_today_data(self, data):
        with open(TODAY_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 오늘 데이터 불러오기
    def load_today_data(self):
        if os.path.exists(TODAY_DATA_FILE):
            print("TODAY_DATA_FILE 파일 열기")
            with open(TODAY_DATA_FILE, 'r', encoding='utf-8') as f:
                print("파일 열기 성공!")
                return json.load(f)
        return None

    # 오늘 데이터 유효성 검사
    def is_today_data_valid(self):
        today_data = self.load_today_data()
        print("today_data", today_data)
        if not today_data:
            print("today_data 가 없습니다.")
            return False

        from datetime import datetime
        today_str = datetime.today().strftime('%Y-%m-%d')
        if today_data.get('todayRowDict', {}).get('일자') != today_str:
            print("오늘 일자가 아닙니다.")
            return False
        """
        dt = datetime.strptime(today_data.get('todayRowDict', {}).get('출근'), "%Y-%m-%d %H:%M:%S")
        date_only = dt.date()
        if date_only != today_str:
            print("date_only", date_only)
            print("today_str", today_str)
            print("출근이 오늘과 일치하지 않습니다.")
            return False
        """

        return today_data.get('todayRowDict', {}).get('일자')

    # 다니로 보내기
    def send_today_data_to_dani(self):
        if self.is_today_data_valid():
            print("self.is_today_data_valid =", self.is_today_data_valid)
            data = self.load_today_data()
            print(' 저장된 데이터 오늘 사용:', data)

            return data

            #self.data_extracted.emit(data)
        else:
            print("오늘 데이터 없음, 테이블 추출 시작")
            data = "오늘 데이터가 없어요!\n조회 후 메시지로 알려드릴게요!"
            self.dataReady.emit(data)
            #self.extract_table()

            #print("테이블 추출 후 받은 데이터:", data)
            #self.dataReady.emit(data)



    # ✅ 체크 함수
    def check_after_load(self):
        QTimer.singleShot(1000, self.after_login_check)

    def load_login_info(self, service: str):
        # 저장된 로그인 정보를 읽어옴 (없으면 None)

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                print(CONFIG_FILE)
                data = json.load(f)
                if service not in data:
                    print(f" [{service}] 정보 없음")
                    return None
                try:
                #user_id = base64.b64decode(data['user_id']).decode('utf-8')
                    user_id = fernet.decrypt(data[service]['user_id'].encode()).decode()
                    password = fernet.decrypt(data[service]['password'].encode()).decode()
                    return {'id': user_id, 'password': password}
                except Exception as e:
                    print(f" 복호화 실패: {e}")
                    return None
        else:
            print("load_login_info_로그인 정보가 없습니다.")
        return None

    def save_login_info(self, service: str, user_id: str, password: str):
        # 로그인 정보를 base64로 인코딩해서 저장
        print("save_login_info 호출")
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                data = json.load(f)

        data[service] = {
            'user_id': fernet.encrypt(user_id.encode()).decode(),
            'password': fernet.encrypt(password.encode()).decode()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ [{service}] 로그인 정보 저장 완료")

    def reset_login_info(self):
        # 로그인 정보를 초기화 (파일 삭제 후 프로그램 재시작)
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        print("로그인 정보가 초기화되었습니다. 프로그램을 다시 시작하세요.")

    def after_login_check(self):
        print("test")
        current_url = self.browser.page().url().toString()
        print("현재 URL:", current_url)

        if "login.html" in current_url:
            if self.login_info:
                print("자동 로그인 시도")
                # 저장된 정보로 자동 로그인 시도
                self.auto_login()
            else:
                print("📝 수동 로그인 필요. 로그인 후 정보를 저장합니다.")
                self.hook_login_button()
                self.enable_save_button_when_ready()  # ⭐ 여기 추가!

        elif "index.jsp" in current_url:
            print(" 로그인 성공! 수동 로그인 여부를 확인합니다.")
            # 로그인 성공했으면 그 시점에서 수동 로그인 정보 저장 시도
            if not self.login_info:
                # 기존에 저장된 로그인 정보가 없었다면, 이번에 입력한 걸 저장
                self.browser.page().runJavaScript(self.read_login_form_and_save)
            # 메뉴 클릭 진행
            self.navigate_menu()

        elif "index.jsp" in current_url:
            print("로그인 성공! 메뉴 이동 준비 중...")
            self.navigate_menu()

    def save_login_info_clicked(self):

        """로그인 정보를 입력 후에 누르도록 유도"""

        print("🔍 로그인 폼에서 ID/PW 읽기 시도...")
        js = '''
        (function() {
            const id_input = document.getElementById('EMP_ID');
            const pw_input = document.getElementById('EMP_PW');
            if (id_input && pw_input) {
                return {id: id_input.value, password: pw_input.value};
            } else {
                return null;
            }
        })();
        '''
        self.browser.page().runJavaScript(js, self.save_manual_login)

    def save_manual_login(self, credentials):
        if credentials and credentials.get('id') and credentials.get('password'):
            print(f"✅ 저장할 ID: {credentials['id']}")
            print(f"✅ 저장할 PW: {credentials['password']}")

            data = {
                'user_id': base64.b64encode(credentials['id'].encode('utf-8')).decode('utf-8'),
                'password': base64.b64encode(credentials['password'].encode('utf-8')).decode('utf-8')
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)

            print(f"✅ 로그인 정보 저장 완료! ({CONFIG_FILE})")
        else:
            print("❌ 로그인 정보를 읽을 수 없습니다. 입력폼 확인 필요!")




    # 1. 로그인 버튼 눌렀을 때 입력값 읽기
    def hook_login_button(self):
        js = '''
        (function() {
            const loginButton = document.querySelector('input[type="submit"]');
            if (loginButton) {
                loginButton.addEventListener('click', function() {
                    const id = document.getElementById('EMP_ID')?.value || '';
                    const pw = document.getElementById('EMP_PW')?.value || '';
                    window.tempLoginInfo = { id: id, password: pw };
                });
            }
        })();
        '''
        self.browser.page().runJavaScript(js)

    # 2. 로그인 성공 시 tempLoginInfo를 가져와서 저장
    def retrieve_temp_login_info(self):
        js = '''
        (function() {
            return window.tempLoginInfo || null;
        })();
        '''
        self.browser.page().runJavaScript(js, self.save_manual_login)

    # 3. after_login_check 수정
    def after_login_check(self):
        current_url = self.browser.page().url().toString()
        print("현재 URL:", current_url)

        if "login.html" in current_url:
            if self.login_info:
                self.auto_login()
            else:
                print("📝 수동 로그인 대기 중... 로그인 버튼 hook 설정")
                self.hook_login_button()

        elif "index.jsp" in current_url:
            print("✅ 로그인 성공! 수동 입력된 로그인 정보 저장 시도")
            if not self.login_info:
                self.retrieve_temp_login_info()
            self.navigate_menu()

    def auto_login(self):
        # 저장된 아이디/비밀번호로 로그인 자동 입력 및 제출
        user_id = self.login_info['id']
        password = self.login_info['password']

        js = f'''
        (function() {{
            const idInput = document.getElementById('EMP_ID');
            const pwInput = document.getElementById('EMP_PW');
            const loginButton = document.getElementById('Login');  // ✅ 여기 수정
            
            
            idInput.value = '{user_id}';
            pwInput.value = '{password}';

             if (idInput.value && pwInput.value) {{
                loginButton.click();
                console.log('✅ 로그인 버튼 클릭 완료');
            }} else {{
                console.error('❌ 아이디 또는 비밀번호 입력 실패');
            }}
        }})();
        '''

        self.browser.page().runJavaScript(js)

    def check_manual_login(self):

        print("check")
        # 수동 로그인 성공 여부 감지 및 저장 로직
        js = '''
        (function() {
            const id = document.getElementById('EMP_ID').value;
            const pw = document.getElementById('EMP_PW').value;
            return {id: id, password: pw};
        })();
        '''
        self.browser.page().runJavaScript(js, self.save_manual_login)

    def save_manual_login(self, credentials):
        print("save_maunal_login 호출")
        print(f"save_manual_login 호출: credentials={credentials}")
        if credentials and credentials.get('id') and credentials.get('password'):
            self.save_login_info("insa", credentials['id'], credentials['password'])
            print("✅ 로그인 정보 저장 완료. 다음부터 자동 로그인됩니다.")

    def navigate_menu(self):
        # menuFrame 접근해서 '근태관리 > 일별근무확인' 클릭
        js = """
        (function() {
            try {
                const menuFrame = document.querySelector('iframe[name="menuFrame"]');
                if (!menuFrame) {
                    console.error('❌ menuFrame을 찾을 수 없습니다.');
                    return;
                }
                const frameDoc = menuFrame.contentDocument || menuFrame.contentWindow.document;

                // 1. '근태관리' 버튼 찾고 클릭 (메뉴 확장)
                const attendButton = [...frameDoc.querySelectorAll('a')].find(a => a.innerText.includes('근태관리'));
                if (attendButton) {
                    attendButton.click();
                    console.log('✅ 근태관리 클릭 완료');
                } else {
                    console.error('❌ 근태관리 버튼을 찾을 수 없습니다.');
                    return;
                }

                // 2. '일별근무확인' 메뉴 찾고 클릭
                setTimeout(() => {
                    const dailyWorkButton = [...frameDoc.querySelectorAll('a')].find(a => a.innerText.includes('일별근무확인'));
                    if (dailyWorkButton) {
                        dailyWorkButton.click();
                        console.log('✅ 일별근무확인 클릭 완료');
                    } else {
                        console.error('❌ 일별근무확인 메뉴를 찾을 수 없습니다.');
                    }
                }, 1000); // 메뉴 펼쳐질 시간 기다림

            } catch (e) {
                console.error('⛔ 메뉴 클릭 중 오류:', e);
            }
        })();
        """

        self.browser.page().runJavaScript(js)

        # 이후에 특정 프레임 로드 감지해서 테이블 자동 크롤링하면 됨
        QTimer.singleShot(6000, self.extract_table)

    def extract_table(self):
        print('📋 테이블 크롤링 준비 시작')

        js = """
        (function() {
            try {
                console.log('📅 오늘 날짜:');
                const iframe = top.document.getElementById('mainFrame');
                if (!iframe) {
                    return "❌ mainFrame 없음";  // 여기서 바로 Python에 반환
                }

                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                
                if (!iframeDoc) {
                    console.error('❌ iframe 문서 접근 실패');
                    return "❌ ❌ iframe 문서 접근 실패 없음";  // 여기서 바로 Python에 반환
                }
                
                const observer = new MutationObserver((mutationsList, observer) => {
                    const tbody = iframeDoc.querySelector('#gbox_gridList table tbody');
                    if (tbody && tbody.querySelectorAll('tr').length > 0) {
                        console.log('✅ tbody와 tr 존재 확인. 데이터 추출 시작');
                        observer.disconnect();
                        extractRows(tbody);
                    }
                });
                
                observer.observe(iframeDoc.body, { childList: true, subtree: true });
                console.log('👀 테이블 생성 감시 시작');
                
                
                
                function extractRows(tbody) {
                
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    console.log('✅ 총 행 수:', rows.length);

                    const today = new Date();
                    const yyyy = today.getFullYear();
                    const mm = String(today.getMonth() + 1).padStart(2, '0');
                    const dd = String(today.getDate()).padStart(2, '0');
                    const todayStr = `${yyyy}-${mm}-${dd}`;
                    console.log('📅 오늘 날짜:', todayStr);
                    let todayRow = null;

                    rows.forEach((row, index) => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length > 2) {
                            const dateText = cells[2].innerText.trim();
                            if (dateText === todayStr) {
                                console.log(`✅ 오늘(${todayStr}) 행 찾음:`, row.innerText.trim());
                                todayRow = row;
                            }
                        }
                    });
                    
                    const lastRow = rows[rows.length - 1];
                    console.log('✅ 마지막 행 내용:', lastRow ? lastRow.innerText.trim() : '없음');
                    
                    // 여기: 결과를 window에 저장!
                    window.daniResult = {
                        
                        todayRowText: todayRow ? todayRow.innerText.trim() : null,
                        lastRowText: lastRow ? lastRow.innerText.trim() : null
                    };
                    console.log('🎯 최종 결과:', window.daniResult);
                    
                    
                }

            } catch (err) {
                console.error('⛔ 코드 실행 중 오류:', err);
                return "⛔ 코드 실행 중 오류";  // 여기서 바로 Python에 반환
            }
        })();
        """

        self.browser.page().runJavaScript(js)
        QTimer.singleShot(3000, self.retrieve_result)

    def retrieve_result(self):
        # 3초 뒤에 window.daniResult를 가져온다
        self.browser.page().runJavaScript("window.daniResult", self.handle_extracted_data)



    def handle_extracted_data(self, data):

        if data and data.get('todayRowText') is not None:
            print('🎯 원본 추출된 일자 목록:', data)

            def clean_row(row_text):
                # \xa0 제거 + 탭(\t)으로 분리
                if row_text:
                    cleaned = row_text.replace('\xa0', '').strip()
                    return cleaned.split('\t')
                return []

            today_row_list = clean_row(data.get('todayRowText'))
            last_row_list = clean_row(data.get('lastRowText'))

            # 컬럼 이름 목록
            columns = [
                "주차", "일자", "휴무", "이름", "시작", "종료",
                "출근", "퇴근", "초과근무", "야간", "휴일", "특매","특별근무"
            ]
            columns_last = [
                "이름", "일자", "휴무", "이름", "시작", "초과",
                "출근", "퇴근", "특매", "야간", "휴일", "특매", "특별근무"
            ]

            # 리스트를 딕셔너리로 매핑
            today_row_dict = dict(zip(columns, today_row_list))
            last_row_dict = dict(zip(columns_last, last_row_list))

            # ➡️ 여기서 '빈 값'이나 '0', '0분' 같은 무의미한 데이터 제거
            def filter_valid_data(row_dict):
                valid_data = {}
                for key, value in row_dict.items():
                    value = value.strip()
                    if value and value != '0' and value != '0분' and value != '0분':
                        valid_data[key] = value
                return valid_data

            today_valid = filter_valid_data(today_row_dict)

            # 여기서 오늘 날짜랑 비교
            from datetime import datetime
            today_str = datetime.now().strftime('%Y-%m-%d')

            extracted_date = today_valid.get('일자')
            if extracted_date and extracted_date != today_str:
                print(f"⚠️ 일치하지 않는 날짜 발견! (추출된: {extracted_date}, 오늘: {today_str})")
                # PyQt 팝업 띄우기
                QMessageBox.warning(self, "알림", f"⛔ 오늘 날짜({today_str})와 일치하지 않습니다!\n(추출된 일자: {extracted_date})")
            else:
                print(f"✅ 일자가 정상입니다: {extracted_date}")

            last_valid = filter_valid_data(last_row_dict)

            pretty_data = {
                "todayRowDict": today_valid,
                "lastRowDict": last_valid
            }

            print('🌟 이쁘게 정리된 데이터:', pretty_data)

            # ✅ 추가: 파일 저장
            try:
                with open(TODAY_DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(pretty_data, f, ensure_ascii=False, indent=4)
                print(f"✅ 데이터 저장 완료: {TODAY_DATA_FILE}")
            except Exception as e:
                print(f"❌ 데이터 저장 실패: {e}")

            # 여기서 pretty_data를 다니로 넘기면 됨

            self.dataReady.emit(pretty_data)

            return pretty_data

        else:
            print("! 추출 실패, 재시도 중...")
            if self.retry_count < 40:
                self.retry_count += 1
                QTimer.singleShot(2000, self.extract_table) # 2초 후 재시도
            else:
                print('❌ 데이터를 추출하지 못했습니다.')
                self.retry_count = 0

# 로그인 다이얼로그 (공지 추가)
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔐 시스템 로그인")
        self.setFixedSize(400,300) # 크기 좀 더 크게

        self.init_ui()
        self.setStyleSheet("""
            QWidget {
                font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif;
                font-size: 13px;
            }
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #0066CC;
                color: white;
                padding: 10px;
                font-size: 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #004C99;
            }
            QLabel {
                color: #555;
                font-size: 12px;
            }
        """)



    def init_ui(self):
            layout = QVBoxLayout(self)

            # 공지사항
            notice_label = QLabel(
                "📢NOTICE\n\n"
                "※ [월별근무확인], [서무초과확인],\n [서무야간확인] 시"
                " 교차확인 필요\n"
                "※ 문의사항: 경영지원부(02-2280-8381)"
            )
            notice_label.setWordWrap(True)
            notice_label.setStyleSheet("""
                QLabel {
                    color: #555;
                    font-size: 14px;
                    margin-bottom: 10px;
                }
            """)
            layout.addWidget(notice_label)

            # ID 입력
            self.id_input = QLineEdit()
            self.id_input.setPlaceholderText("아이디 입력")
            self.id_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                    font-size: 14px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
            """)
            layout.addWidget(self.id_input)

            # PW 입력
            self.pw_input = QLineEdit()
            self.pw_input.setPlaceholderText("비밀번호 입력")
            self.pw_input.setEchoMode(QLineEdit.Password)
            self.pw_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                    font-size: 14px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
            """)
            layout.addWidget(self.pw_input)

            # 버튼
            button_layout = QHBoxLayout()

            self.login_button = QPushButton("🔓 로그인")
            self.login_button.clicked.connect(self.try_login)
            self.login_button.setEnabled(False)
            self.login_button.setStyleSheet("""
                QPushButton {
                    background-color: #0066CC;
                    color: white;
                    padding: 10px;
                    font-size: 14px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #004C99;
                }
            """)

            button_layout.addStretch()
            button_layout.addWidget(self.login_button)
            button_layout.addStretch()

            layout.addLayout(button_layout)

            # 입력 감지 연결
            self.id_input.textChanged.connect(self.enable_login_button)
            self.pw_input.textChanged.connect(self.enable_login_button)


    def enable_login_button(self):
        # 둘 다 입력됐을 때만 버튼 활성화
        if self.id_input.text() and self.pw_input.text():
            self.login_button.setEnabled(True)
        else:
            self.login_button.setEnabled(False)

    def try_login(self):
        # 로그인 버튼 눌렀을 때
        self.accept()  # QDialog.accept() 호출 -> exec_()가 1 반환됨

    def get_credentials(self):
        # 입력값 반환
        return self.id_input.text(), self.pw_input.text()

if __name__ == '__main__':
    app = QApplication([])
    win = BrowserWindow()
    login = LoginDialog()
    login.show()

    #win.show()
    app.exec_()


























