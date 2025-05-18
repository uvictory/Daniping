
TEST_FILE = "test.xlsx"
TODAY_DATA_FILE = "test.json"

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
            "출근", "퇴근", "초과근무", "야간", "휴일", "특매", "특별근무"
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
        self.extracting_in_progress = False  # 성공적으로 데이터 처리 완료 시 추출 프래그 false

        self.retry_count = -1  # ✅ 재시도 방지 신호
        # self.browser.load(QUrl("http://192.168.50.13:8090/JG_INNER_PJ/login.jsp"))

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