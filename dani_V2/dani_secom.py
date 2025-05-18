import sys
import os
import json
import base64
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QDialog, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, Qt, pyqtSignal
from cryptography.fernet import Fernet
# ✅ 기본 경로 설정 함수
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# ✅ 리소스 경로 보정 함수 정의
def resource_path(relative_path):
    """PyInstaller 실행 환경과 개발 환경 모두에서 리소스를 불러올 수 있도록 경로 보정"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 실행 중일 때 생성되는 임시 폴더
    except Exception:
        base_path = os.path.abspath(".")  # 개발환경에서는 현재 경로 기준
    return os.path.join(base_path, relative_path)






# ✅ 파일 경로
BASE_DIR = get_base_dir()
CONFIG_FILE = resource_path("credentials.json")  # 🔄 경로 보정
TODAY_DATA_FILE = resource_path("today_attendance.json")  # 🔄 경로 보정
# 키 파일 경로


def load_key(path):
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(Fernet.generate_key())
    with open(path, 'rb') as f:
        return Fernet(f.read())

def get_current_month():
    return datetime.now().strftime('%Y-%m')

# ✅ 로그인 팝업창
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔒 로그인 필요")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()
        notice = QLabel("※ 각 팀 서무는 월별근무확인 등 교차확인 바랍니다.\n※ 문의사항: 경영지원부 02-2280-8381")
        notice.setAlignment(Qt.AlignCenter)
        notice.setStyleSheet("font-size: 12px; color: gray;")

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID 입력")
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Password 입력")
        self.pw_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.accept)

        # 스타일 적용
        self.setStyleSheet("""
            QDialog { background-color: #f0f0f5; }
            QLineEdit { padding: 10px; font-size: 14px; }
            QPushButton { background-color: #4CAF50; color: white; font-size: 15px; padding: 8px; }
            QPushButton:hover { background-color: #45a049; }
        """)

        layout.addWidget(notice)
        layout.addWidget(self.id_input)
        layout.addWidget(self.pw_input)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def get_credentials(self):
        return self.id_input.text(), self.pw_input.text()

# ✅ 메인 Dani 브라우저 창
class BrowserWindow(QWidget):
    dataReady = pyqtSignal(object)
    extractingStarted = pyqtSignal()
    extractingFinished = pyqtSignal()

    def is_extractiong(self):
        return self.extracting_in_progress


    def __init__(self):
        super().__init__()
        self.fernet = load_key(resource_path("secret2.key"))
        self.setWindowTitle('Dani 로그인')
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        self.retry_count = 0  # 추출 재시도 횟수
        self.navigation_started = False  # 중복 방지 플래그
        self.login_flow_started = False  # 🔒 로그인 창 중복 방지 플래그
        self.extracting_in_progress = False  # 📌 현재 추출이 진행 중인지 여부

        if self.is_today_data_valid():
            print("오늘 유효 데이터가 있기에 프로그램 종료합니다.")
            QTimer.singleShot(0, self.close)  # 0ms 뒤 안전하게 close
            return


        # ✅ 로그인 정보 로드
        self.login_info = self.load_login_info("insa")

        if self.login_info: # 로그인 정보 있을시, 자동 로그인 후 추출 시작
            self.extracting_in_progress = True # 자동 추출 시작 플래그 설정
            print("로그인 정보 있을시, 자동 로그인 후 추출 시작")

            self.browser.load(QUrl('http://192.168.50.13:8090/JG_INNER_PJ/login.html'))
            self.browser.loadFinished.connect(self.after_page_load)


        else:   #로그인 정보 없는 경우, 수동 로그인 
            self.browser.load(QUrl('http://192.168.50.13:8090/JG_INNER_PJ/login.html'))
            self.browser.loadFinished.connect(self.after_page_load)





    def __del__(self):
        print("💥 BrowserWindow 소멸됨 (메모리에서 해제됨)")

    # 쿠키, 캐시 삭제 함수
    def clear_browser_session(self):
        profile = self.browser.page().profile()

        # 쿠키 삭제
        profile.cookieStore().deleteAllCookies()

        # 캐시 삭제
        profile.clearHttpCache()

        print("🧹 세션 초기화 완료")
    
    

    # 세션 초기화 함수
    def reset_session_and_reload(self):
        profile = self.browser.page().profile()

        # 캐시와 쿠키 삭제
        profile.clearHttpCache()
        profile.cookieStore().deleteAllCookies()

        print("기존 세션 제거 완료 -> 로그인 페이지 새로고침")

        #로그인 페이지 새로 로드
        #self.browser.load(QUrl('http://192.168.50.13:8090/JG_INNER_PJ/login.html'))

        # 로그인 시도는 이후 페이지 로드 후 자동 수행됨

    # 🔥 1. 로그인 플로우 시작
    def start_login_flow(self):
        if self.login_flow_started:
            print("🚫 이미 로그인 요청됨 → 중복 호출 방지")
            return
        self.login_flow_started = True
        print("start_login_flow 호출")
        dialog = LoginDialog()
        if dialog.exec_() == QDialog.Accepted:
            user_id, password = dialog.get_credentials()
            self.perform_login(user_id, password)

        else:
            self.login_flow_started = False  # 로그인 창 닫힘 → 다시 시도할 수 있게 초기화

    # 🔥 2. 받아온 ID/PW로 로그인 시도
    def perform_login(self, user_id, password):
        # 이전 세션 제거
        print('🔄 로그인 수행')



        # 저장해서 이후 로그인 성공 시 저장
        self.input_id = user_id
        self.input_pw = password

        try:
            js = f"""
                    (function() {{
                        const idInput = document.getElementById('EMP_ID');
                        const pwInput = document.getElementById('EMP_PW');
                        const loginButton = document.getElementById('Login');
                        idInput.value = '{user_id}';
                        pwInput.value = '{password}';
                        loginButton.click();
                    }})();
                    """
        except Exception as e:
            print("로그인 정보가 유효하지 않습니다.")
            os.remove(CONFIG_FILE)
            print("🧹 로그인 정보가 초기화되었습니다.")
            self.start_login_flow()

        self.browser.page().runJavaScript(js)
        QTimer.singleShot(3000, self.check_login_result)

    # 🔥 3. 로그인 성공 여부 확인
    def check_login_result(self):
        print("check_login_result")
        current_url = self.browser.page().url().toString()
        print("current_url = ", current_url)
        if "index.jsp" in current_url:
            print("✅ 로그인 성공!")
            self.login_flow_started = False  # ✅ 초기화
            #self.save_login_info("insa",self.input_id, self.input_pw)   # 인스턴스 메서드 방식
            self.save_login_info("insa",self.input_id,self.input_pw) # 정적 메서드

            # ✅ 로그인 성공 시 메뉴 이동 → 거기서 extract_table 자동 호출
            self.navigate_menu()
        else:
            QMessageBox.warning(self, "로그인 실패", "❌ ID/PW를 다시 확인해주세요.")
            self.login_flow_started = False  # ✅ 다시 시도 가능하게 초기화
            self.start_login_flow()

    # ✅ 로그인 정보
    def save_login_info(self,service: str, user_id: str, password: str):
        """
        data = {
            'user_id': base64.b64encode(user_id.encode('utf-8')).decode('utf-8'),
            'password': base64.b64encode(password.encode('utf-8')).decode('utf-8')
        }"""
        data = {}

        # 기존 데이터 불러오기
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # 해당 서비스에 암호화된 정보 저장
        data[service] = {
            'user_id': self.fernet.encrypt(user_id.encode()).decode(),
            'password': self.fernet.encrypt(password.encode()).decode()
        }

        # 다시 저장
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ [{service}] 로그인 정보 저장 완료")



        print("✅ 로그인 정보 저장 완료")

    # ✅ 로그인 정보 로드
    def load_login_info(self, service: str):
        if os.path.exists(CONFIG_FILE):
            print("로그인 파일 존재!")
            try:
                with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                    if service not in data:
                        print(f" [{service}] 정보 없음")
                        return None
                    try:
                        # user_id = base64.b64decode(data['user_id']).decode('utf-8')
                        user_id = self.fernet.decrypt(data[service]['user_id'].encode()).decode()
                        password = self.fernet.decrypt(data[service]['password'].encode()).decode()
                        return {'id': user_id, 'password': password}
                    except Exception as e:
                        print(f" 복호화 실패: {e}")
                        return None
                    """
                    #base 64 디코딩 시도
                    return {
                        'id': base64.b64decode(data['user_id']).decode('utf-8'),
                        'password': base64.b64decode(data['password']).decode('utf-8')
                            }
                    """
            except Exception as e:
                print(f"로그인 정보 유효성 실패: {e}")
                os.remove(CONFIG_FILE)  # 파일 삭제
                print("로그인 창 다시 띄움")
                #self.start_login_flow()
                return False
        else:
            print("로그인 정보 파일 없음")
            #self.start_login_flow()
            return False


    # ✅ 첫 페이지 로딩 완료 시 처리
    def after_page_load(self):
        current_url = self.browser.page().url().toString()
        if "index.jsp" in current_url:
            print("✅ 세션 살아있음 → 바로 테이블 조회")
            self.navigate_menu()
        else:
            if self.login_info:
                print("✅ 저장된 정보로 자동 로그인 시도")
                self.perform_login(self.login_info['id'], self.login_info['password'])
            else:
                print("🔒 로그인 정보 없음 → 수동 로그인 요청")
                self.start_login_flow()





    # ✅ 메뉴 이동 및 테이블 크롤링 (여기는 기존 코드 활용)
    def navigate_menu(self):
        if self.navigation_started:
            print("navigated_menu 이미 실행됨. 중복 호출 방지")
            return 
        self.navigation_started = True # 한 번만 호출되게 설정

        print("➡️ 메뉴 이동 및 테이블 조회 시작")
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

                // 2. '개인근무설정' 메뉴 찾고 클릭
                setTimeout(() => {
                    const dailyWorkButton = [...frameDoc.querySelectorAll('a')].find(a => a.innerText.includes('개인근무설정'));
                    if (dailyWorkButton) {
                        dailyWorkButton.click();
                        console.log('✅ 개인근무설정 클릭 완료');
                    } else {
                        console.error('❌ 개인근무설정 메뉴를 찾을 수 없습니다.');
                    }
                }, 1000); // 메뉴 펼쳐질 시간 기다림


                // 3. '일별근무확인' 메뉴 찾고 클릭
                setTimeout(() => {
                    const dailyWorkButton = [...frameDoc.querySelectorAll('a')].find(a => a.innerText.includes('일별근무확인'));
                    if (dailyWorkButton) {
                        dailyWorkButton.click();
                        console.log('✅ 일별근무확인 클릭 완료');
                    } else {
                        console.error('❌ 일별근무확인 메뉴를 찾을 수 없습니다.');
                    }
                }, 2000); // 메뉴 펼쳐질 시간 기다림

            } catch (e) {
                console.error('⛔ 메뉴 클릭 중 오류:', e);
            }
        })();
        """


        self.browser.page().runJavaScript(js)
        QTimer.singleShot(5000, self.navigation_started_setFalse)  # 한 번만 호출되게 설정)

        # 이후에 특정 프레임 로드 감지해서 테이블 자동 크롤링하면 됨
        QTimer.singleShot(6000, self.extract_table)

    def navigation_started_setFalse(self):
        self.navigation_started = False

    def extract_table(self):

        print('📋 테이블 크롤링 준비 시작')
        self.extractingStarted.emit()  # 시작 알림
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
                 "야간", "휴일", "특매", "특별근무"
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
                QMessageBox.warning(self, "알림", f"⛔ 오늘 날짜({today_str})와 일치하지 않습니다!\n다니핑을 재실행 해주세요.\n(추출된 일자: {extracted_date})")
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
            self.extractingFinished.emit()  # ✅ 완료 알림
            self.extracting_in_progress = False # 성공적으로 데이터 처리 완료 시 추출 프래그 false


            self.retry_count = -1  # ✅ 재시도 방지 신호
            #self.browser.load(QUrl("http://192.168.50.13:8090/JG_INNER_PJ/login.jsp"))


            '''
            print("🧹 세션 종료 및 브라우저 닫기 완료")
            self.browser.setParent(None)
            self.browser.deleteLater()
            self.browser = None
            self.close()
            self.deleteLater()  # 메모리 해제 예약
            self.browser = None
            '''



            return pretty_data
        # ✅ 실패 시 재시도 조건 보완
        else:
            if self.retry_count == -1:
                print("이미 종료된 상태이므로 추출 중단")
                self.extractingFinished.emit()  # 실패로 종료 시
                self.extracting_in_progress = False
                return
            print("! 추출 실패, 재시도 중...")
            if self.retry_count < 80:
                self.retry_count += 1
                QTimer.singleShot(2000, self.extract_table) # 2초 후 재시도
            else:
                print('❌ 데이터를 추출하지 못했습니다.')

                self.retry_count = 0
                #self.close()
                #self.deleteLater()  # 메모리 해제 예약
                self.extractingFinished.emit()  # 실패로 종료 시
                self.extracting_in_progress = False

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
        # today_attendence.json이 없는 경우,
        if not today_data:
            print("today_data 가 없습니다.")
            return False

        # today_attendence.json이 있으나, 당월 조회 기록이 없을 경우 개인근무설정 자동 진입 후 일별근무확인
        # '일자'에서 년-월만 추출
        full_date = today_data['todayRowDict'].get('일자')  # "2025-04-07"
        if not full_date:
            return False
        year_month = full_date[:7]  # "2025-04"
        if year_month != get_current_month():
            data_first = "이번 달 데이터가 없어요!\n조회 후 메시지로 알려드릴게요!\n이번 달 개인근무설정은 잊지 않으셨나요?"
            self.dataReady.emit(data_first)
            print("get_current_month",get_current_month())
            print(year_month)
            print("이번 달 데이터가 없어요!\n조회 후 메시지로 알려드릴게요!\n이번 달 개인근무설정은 잊지 않으셨나요?")


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
        if self.extracting_in_progress:
            print("⚠️ 이미 추출이 진행 중입니다. 중복 호출 방지됨.")
            return None  # 중복 추출 방지



        if self.is_today_data_valid():
            data = self.load_today_data()
            print(' 저장된 데이터 오늘 사용:', data)
            #self.dataReady.emit(data)  # ✅ emit로 보내고
            #return None  # 직접 반환하지 않음
            self.extracting_in_progress = False  # ✅ 추출 안했으므로 바로 종료
            return data # ✅ 유효한 데이터가 있으므로 추출 안함

        print("🔍 유효한 데이터가 없어 새로 조회를 시도합니다...")

        # 유효한 데이터가 없으므로 새로 조회 시작
        if self.load_login_info("insa"):
            print("✅ 로그인 정보 로드 성공 → 자동 조회 시도")
            self.login_info = self.load_login_info("insa")

            if self.login_info:
                print("🔑 로그인 정보 디코딩 성공 → 테이블 추출 시작")
                self.extracting_in_progress = True  # ✅ 여기에서만 True 설정
                #self.extractingStarted.emit()
                self.extract_table()  # 🚀 비동기로 실행되며, 결과는 handle_extracted_data()에서 emit됨
                # ✅ 로그인만 하고 navigate_menu → 그 안에서 extract_table 호출
                #self.perform_login(self.login_info['id'], self.login_info['password'])
                print("로그인 수행")
            else:
                print("❌ 로그인 정보 디코딩 실패 → 수동 로그인 필요")
                self.extracting_in_progress = False  # ⛔ 추출 실패로 복원
                self.start_login_flow()

        else:
            print("❌ 로그인 정보 없음 → 수동 로그인 요청")
            self.extracting_in_progress = False  # ⛔ 추출 실패로 복원
            self.start_login_flow()

        # 현재 시점에서는 아직 데이터를 확보하지 못했으므로, 다니에게는 대기 메시지를 보냄
        wait_message = "오늘 데이터가 없어요!\n조회 후 메시지로 알려드릴게요!"
        self.dataReady.emit(wait_message)
        return None


# ✅ 메인 실행
if __name__ == '__main__':

    app = QApplication([])
    win = BrowserWindow()
    win.show()
    app.exec_()
