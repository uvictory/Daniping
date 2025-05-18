import random
import os
import pygame
import sys
import math
import tkinter as tk
from tkinter import simpledialog,filedialog, messagebox
import datetime

# resource_path() 함수 추가
def resource_path(relative_path):
    """PyInstaller 실행환경과 개발환경 모두에서 리소스를 불러올 수 있도록 경로 보정"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 실행 중일 때 생성되는 임시 폴더
    except Exception:
        base_path = os.path.abspath(".")  # 개발환경에서는 현재 경로 기준

    return os.path.join(base_path, relative_path)

WIDTH, HEIGHT = 700, 700
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MAIN_COLOR = (255, 250, 250)

COLORS = [
    (255, 204, 204), (204, 255, 204), (204, 204, 255),
    (255, 255, 204), (255, 204, 255), (204, 255, 255),
    (255, 220, 240), (230, 240, 255), (255, 240, 180),
    (255, 220, 200)
]

BUTTON_COLOR = (255, 224, 230)
BUTTON_HOVER = (255, 179, 191)

def get_base_dir():
    if getattr(sys, 'frozen', False):  # exe 배포 시
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
MENU_SAVE_PATH = os.path.join(BASE_DIR, "menu.txt")

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🍱 점심메뉴 선택 미니게임")
FONT_PATH = resource_path("fonts/NanumSquareRoundR.ttf")

IMAGE_PATH = resource_path("images/lunch1.png")

bottom_image = pygame.image.load(IMAGE_PATH)
bottom_image = pygame.transform.smoothscale(bottom_image,(230, 230))

IMAGE_PATH2 = resource_path("images/lunch2.png")
bottom_image2 = pygame.image.load(IMAGE_PATH2)
bottom_image2 = pygame.transform.smoothscale(bottom_image2,(230, 230))

title_font = pygame.font.Font(FONT_PATH, 40)
question_font = pygame.font.Font(FONT_PATH, 28)
button_font = pygame.font.Font(FONT_PATH, 24)
result_font = pygame.font.Font(FONT_PATH, 26)
clock = pygame.time.Clock()

class Button:
    def __init__(self, rect, text, color):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color

    def draw(self, surface, mouse_pos):
        color = BUTTON_HOVER if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=12)
        text_surface = button_font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)
    
default_menu = [
    "가나안뼈해장탕", "하이가쯔", "금성회관", "마포우사미", "쿄오모 라멘",
    "옛날홍두깨 손칼국수", "해남순대국", "봉평메밀  막국수", "사랑방칼국수", "양평해장국 왕돈까스", "두부사랑", "뽕사부",
    "사가루가스", "영글찬김밥", "약수깡족발 순대국"
]

def version_select():
    running = True
    today_menu = random.choice(default_menu)

    while running:
        screen.fill(MAIN_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        title = title_font.render("점심메뉴 선택 미니게임", True, BLACK)
        title_rect = title.get_rect(center=(WIDTH//2, 100))
        screen.blit(title, title_rect)

        image_rect = bottom_image.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
        screen.blit(bottom_image, image_rect)

        buttons = [
            Button((200, 180, 300, 50), "1. 직접 메뉴 입력 룰렛", COLORS[0]),
            Button((200, 260, 300, 50), "2. 기분/날씨/피로도 추천", COLORS[1]),
            Button((200, 340, 300, 50), "3. 기본 메뉴 룰렛", COLORS[2])
        ]

        for btn in buttons:
            btn.draw(screen, mouse_pos)

        BALLOON_IMAGE = pygame.image.load(resource_path("images/random1.png"))
        BALLOON_IMAGE = pygame.transform.smoothscale(BALLOON_IMAGE, (230, 177))

        if image_rect.collidepoint(mouse_pos):
            # 말풍선 이미지 띄우기
            balloon_font = pygame.font.Font(FONT_PATH, 18)
            balloon_font2 = pygame.font.Font(FONT_PATH, 25)
            balloon_x = image_rect.right - 25
            balloon_y = image_rect.top - 70
            screen.blit(BALLOON_IMAGE, (balloon_x, balloon_y))

            # 풍선 중심 좌표
            balloon_center_x = balloon_x + 230 // 2 

            # 고정 문구 띄우기
            fixed_text_surface = balloon_font.render("다니의 추천 맛집", True, (80, 80, 80))
            fixed_text_rect = fixed_text_surface.get_rect(center=(balloon_center_x + 6, balloon_y + 70))
            screen.blit(fixed_text_surface, fixed_text_rect)

            if len(today_menu) <= 6:
                menu_surface = balloon_font2.render(today_menu, True, BLACK)
                menu_rect = menu_surface.get_rect(center=(balloon_center_x + 10, balloon_y + 110))
                screen.blit(menu_surface, menu_rect)
            else:
                first_line = today_menu[:6] 
                second_line = today_menu[6:] 

                first_surface = balloon_font2.render(first_line, True, BLACK)
                first_rect = first_surface.get_rect(center=(balloon_center_x + 10, balloon_y + 100))
                screen.blit(first_surface, first_rect)

                second_surface = balloon_font2.render(second_line, True, BLACK)
                second_rect = second_surface.get_rect(center=(balloon_center_x + 10, balloon_y + 128))
                screen.blit(second_surface, second_rect)


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if buttons[0].is_clicked(mouse_pos):
                    version_one()
                elif buttons[1].is_clicked(mouse_pos):
                    version_two()
                elif buttons[2].is_clicked(mouse_pos):
                    version_three()
                    return

        pygame.display.flip()
        clock.tick(60)

def save_menu_list(menu_list):
    try:
        with open(MENU_SAVE_PATH, 'w', encoding='utf-8') as f:
            for item in menu_list:
                f.write(item + "\n")
    except Exception as e:
        print(f"❌ 메뉴 저장 실패: {e}")

def load_menu_list():
    try:
        if not os.path.exists(MENU_SAVE_PATH):
            return []
        with open(MENU_SAVE_PATH, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"❌ 메뉴 불러오기 실패: {e}")
        return []
    
def menu_input_by_add():
    root = tk.Tk()
    root.title("🍽️ 메뉴 추가하기")
    root.geometry("420x430")
    root.configure(bg="#fff8f8")
    root.resizable(False, False)

    x = (root.winfo_screenwidth() // 2) - 240
    y = (root.winfo_screenheight() // 2) - 240
    root.geometry(f"+{x}+{y}")

    label = tk.Label(root, text="메뉴를 하나씩 입력하세요 (3개 ~ 10개)", bg="#fff8f8", font=("NanumGothic", 13))
    label.pack(pady=(20, 5))

    sub_label = tk.Label(root, text="엔터를 누르면 다음 칸으로 이동합니다.", bg="#fff8f8", font=("NanumGothic", 10), fg="#666666")
    sub_label.pack(pady=(0, 10))

    frame = tk.Frame(root, bg="#fff8f8")
    frame.pack()

    entries = []
    result = []

    def move_to_next(event, idx):
        if idx < 9:
            entries[idx + 1].focus_set()

    for i in range(5):
        for j in range(2):
            idx = i * 2 + j
            entry = tk.Entry(frame, font=("NanumGothic", 12), width=14, relief="flat",
                             highlightthickness=2, highlightbackground="#ffcccc", highlightcolor="#ff6666",
                             bg="#fffdfd", insertbackground="black")
            entry.grid(row=i, column=j, padx=12, pady=6, ipady=4)
            entry.bind('<Return>', lambda e, i=idx: move_to_next(e, i))
            entries.append(entry)

    def on_submit():
        result.clear()
        for entry in entries:
            text = entry.get().strip()
            if text:
                result.append(text)
        root.destroy()

    def on_save():
        menu_list = []
        for entry in entries:
            text = entry.get().strip()
            if text:
                menu_list.append(text)

        if not (3 <= len(menu_list) <= 10):
            messagebox.showerror("저장 오류", "메뉴는 3개 이상 10개 이하로 입력해야 합니다.")
            return

        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"menu_{now}.txt"
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=filename,
                                                filetypes=[("Text Files", "*.txt")])

        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    for item in menu_list:
                        f.write(item + "\n")
                messagebox.showinfo("저장 성공", f"메뉴가 {save_path}에 저장되었습니다.")
            except Exception as e:
                messagebox.showerror("저장 실패", str(e))

    def on_load():
        load_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not load_path:
            return

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not (3 <= len(lines) <= 10):
                raise ValueError("파일에는 3개 이상 10개 이하의 메뉴만 있어야 합니다.")

            for line in lines:
                if len(line) > 30 or not line.isprintable():
                    raise ValueError("메뉴 항목이 너무 길거나 잘못된 문자가 포함되어 있습니다.")

            for i, entry in enumerate(entries):
                entry.delete(0, tk.END)
                if i < len(lines):
                    entry.insert(0, lines[i])
        except Exception as e:
            messagebox.showerror("불러오기 오류", f"유효한 메뉴 파일이 아닙니다.\n{str(e)}")

    # 버튼들
    button_frame = tk.Frame(root, bg="#fff8f8")
    button_frame.pack(pady=15)

    submit_btn = tk.Button(root, text="✔ 완료", command=on_submit,
                           bg="#ffcccc", activebackground="#ff9999",
                           font=("NanumGothic", 12), width=12, relief="raised", bd=2)
    submit_btn.place(relx=0.5, rely=1.0, anchor="s", y=-80)

    save_btn = tk.Button(root, text="💾 저장하기", command=on_save,
                         bg="#ffe0cc", activebackground="#ffbf80",
                         font=("NanumGothic", 10), width=10)
    save_btn.place(x=20, rely=1.0, anchor="sw", y=-20)

    load_btn = tk.Button(root, text="📂 불러오기", command=on_load,
                         bg="#ddddff", activebackground="#ccccff",
                         font=("NanumGothic", 10), width=10)
    load_btn.place(x=120, rely=1.0, anchor="sw", y=-20)

    entries[0].focus_set()
    root.mainloop()
    return result

def version_one():
    menu_list = menu_input_by_add()

    if not menu_list:
        return version_select()

    if len(menu_list) < 3 or len(menu_list) > 10:
        error_message = "메뉴는 3개 이상 10개 이하로 입력해주세요."
        show_error_and_return(error_message)
        return version_select()

    run_pygame_roulette(menu_list)
    version_select()

def show_error_and_return(message):
    running = True
    while running:
        screen.fill(MAIN_COLOR)
        error_text = button_font.render(message, True, (200, 0, 0))
        screen.blit(error_text, (WIDTH // 2 - error_text.get_width() // 2, HEIGHT // 2 - 20))

        tip_text = button_font.render("ESC키를 눌러서 돌아가세요.", True, BLACK)
        screen.blit(tip_text, (WIDTH // 2 - tip_text.get_width() // 2, HEIGHT // 2 + 20))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                running = False

        pygame.display.flip()
        clock.tick(60)

def version_two():
    questions = [
        {"text": "현재 기분은?", "options": ["기분 최고", "평범함", "우울함"]},
        {"text": "오늘 날씨는?", "options": ["맑음", "흐림", "비옴", "눈"]},
        {"text": "피로도는?", "options": ["기운 넘침", "좀 피곤함", "매우 피곤함"]}
    ]
    answers = []
    question_idx = 0
    while question_idx < len(questions):
        screen.fill(MAIN_COLOR)
        mouse_pos = pygame.mouse.get_pos()
        q = questions[question_idx]
        title_surface = title_font.render("점심 메뉴 추천", True, BLACK)
        title_rect = title_surface.get_rect(center=(WIDTH // 2, 60))
        screen.blit(title_surface, title_rect)

        question_surface = question_font.render(q["text"], True, BLACK)
        question_rect = question_surface.get_rect(center=(WIDTH // 2, 120))
        screen.blit(question_surface, question_rect)
        
        image_rect2 = bottom_image2.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
        screen.blit(bottom_image2, image_rect2)

        buttons = []
        for i, opt in enumerate(q["options"]):
            btn = Button((200, 180 + i*70, 300, 50), opt, COLORS[i % len(COLORS)])
            btn.draw(screen, mouse_pos)
            buttons.append(btn)
        back_btn = Button((20, HEIGHT - 60, 120, 40), "← 이전", BUTTON_COLOR)
        back_btn.draw(screen, mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_btn.is_clicked(mouse_pos):
                    return version_select()
                for btn in buttons:
                    if btn.is_clicked(mouse_pos):
                        answers.append(btn.text)
                        question_idx += 1
        pygame.display.flip()
        clock.tick(60)
    show_result(*answers)
    version_select()

def version_three():
    default_menu = [
        "족발·보쌈", "찜·탕·찌개", "돈까스·회·일식", "피자", "분식",
        "양식", "패스트푸드", "중식", "아시안", "백반·죽·국수"
    ]
    run_pygame_roulette(default_menu)
    version_select()

def show_result(mood, weather, tired):
    def recommend():
        if tired == "매우 피곤함":
            return random.choice([
                "삼계탕", "설렁탕", "갈비탕", "영양죽", "한우국밥", "김치콩나물국밥", "순대국", "들깨칼국수"
            ]), "기운이 떨어졌을 땐 뜨끈한 보양식이 최고죠!"

        elif mood == "우울함" and weather == "비옴":
            return random.choice([
                "파스타", "짜장면", "매운 라면", "토마토리조또", "크림우동", "떡볶이"
            ]), "비 오는 날 우울한 기분엔 위로되는 따끈한 한 그릇!"

        elif mood == "기분 최고":
            return random.choice([
                "초밥", "찜닭", "연어덮밥", "치즈돈까스", "크림파스타", "닭강정", "불고기 정식", "회덮밥"
            ]), "좋은 기분엔 특별한 메뉴로 보상!"

        elif weather == "비옴":
            return random.choice([
                "부대찌개", "순두부찌개", "어묵우동", "짬뽕", "감자탕", "매운해물탕", "돼지국밥"
            ]), "비 오는 날엔 국물 있는 음식이 최고죠~"

        elif weather == "눈":
            return random.choice([
                "육개장", "칼국수", "떡국", "사골곰탕", "들깨수제비"
            ]), "눈 오는 날엔 따뜻하고 든든하게!"

        elif tired == "좀 피곤함":
            return random.choice([
                "돈까스", "쭈꾸미 볶음", "불고기덮밥", "카레라이스", "닭갈비", "낙곱새", "제육덮밥", "매운돼지불백", "오므라이스"
            ]), "지친 몸엔 든든한 한 끼가 필요해요."

        elif mood == "평범함":
            return random.choice([
                "제육볶음", "비빔밥", "김치볶음밥", "우삼겹덮밥", "순두부계란찜 정식", "치킨마요덮밥"
            ]), "오늘은 무난한 한 끼 어때요?"

        elif weather == "맑음" and tired == "기운 넘침":
            return random.choice([
                "샐러드볼", "냉모밀", "쌈밥", "토스트", "치킨랩", "과일요거트볼"
            ]), "날씨 좋고 기분도 좋을 땐 가볍게 먹는 것도 좋아요!"

        else:
            return random.choice([
                "김치찌개", "된장찌개", "라면", "햄버거", "김밥", "편의점 도시락"
            ]), "언제 먹어도 만족스러운 익숙한 맛이에요!"

    menu, reason = recommend()
    running = True
    while running:
        screen.fill(WHITE)
        title_surface = title_font.render("오늘의 추천 메뉴!", True, BLACK)
        title_rect = title_surface.get_rect(center=(WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)

        menu_surface = question_font.render(f"{menu}", True, (200, 50, 50))
        menu_rect = menu_surface.get_rect(center=(WIDTH // 2, 160))
        screen.blit(menu_surface, menu_rect)

        for idx, line in enumerate([reason[i:i+30] for i in range(0, len(reason), 30)]):
            surface = result_font.render(line, True, BLACK)
            reason_surface = result_font.render(line, True, BLACK)
            reason_rect = reason_surface.get_rect(center=(WIDTH // 2, 230 + idx * 30))
            screen.blit(reason_surface, reason_rect)

        tip = button_font.render("ESC 키를 누르면 종료됩니다.", True, (100, 100, 100))
        screen.blit(tip, (WIDTH//2 - 150, HEIGHT - 40))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        pygame.display.flip()
        clock.tick(60)

def run_pygame_roulette(menu_list):
    pygame.display.set_caption("🍱 점심 룰렛 돌리기")
    font = pygame.font.Font(FONT_PATH, 28)
    result_font = pygame.font.Font(FONT_PATH, 24)
    center = (WIDTH // 2, HEIGHT // 2)
    radius = 250
    angle_per_item = 360 / len(menu_list)
    current_angle = 0
    is_spinning = False
    spin_speed = 0
    back_button = Button((10, 10, 80, 40), "← 뒤로", BUTTON_COLOR)

    def draw_roulette(current_angle):
        for i, item in enumerate(menu_list):
            start_angle = angle_per_item * i + current_angle
            end_angle = angle_per_item * (i + 1) + current_angle
            points = [center]
            for j in range(31):
                angle = math.radians(start_angle + (end_angle - start_angle) * (j / 30))
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                points.append((x, y))
            pygame.draw.polygon(screen, COLORS[i % len(COLORS)], points)
            mid_angle = math.radians((start_angle + end_angle) / 2)
            x = center[0] + (radius * 0.6) * math.cos(mid_angle)
            y = center[1] + (radius * 0.6) * math.sin(mid_angle)
            text = font.render(item, True, BLACK)
            text_rect = text.get_rect(center=(x, y))
            screen.blit(text, text_rect)
        pygame.draw.polygon(screen, BLACK, [(WIDTH//2 - 15, 60), (WIDTH//2 + 15, 60), (WIDTH//2, 80)])
        mouse_pos = pygame.mouse.get_pos()
        back_button.draw(screen, mouse_pos)

        # 스페이스바 안내 문구 추가
        if not is_spinning and keydown_time is None:
            tip_font = pygame.font.Font(FONT_PATH, 18)
            tip_surface = tip_font.render("스페이스바를 눌러 룰렛을 돌리세요!", True, (120, 120, 120))
            tip_rect = tip_surface.get_rect(center=(WIDTH//2, HEIGHT - 25))
            screen.blit(tip_surface, tip_rect)

    clock = pygame.time.Clock()
    running = True
    keydown_time = None
    has_spun = False  # 한 번이라도 돌았는지 여부

    while running:
        screen.fill(WHITE)
        if keydown_time and not is_spinning:
            duration = (pygame.time.get_ticks() - keydown_time) / 1000
            ratio = min(duration / 3, 1.0)
            bar_w = int(WIDTH * 0.8 * ratio)
            pygame.draw.rect(screen, (200,200,200), (60, HEIGHT-40, WIDTH*0.8, 20))
            pygame.draw.rect(screen, (100,100,255), (60, HEIGHT-40, bar_w, 20))
        
        if has_spun and not is_spinning and spin_speed < 0.05 and keydown_time is None:
            # 오늘의 선택 표시
            normalized_angle = current_angle % 360
            pointer_angle = (270 - normalized_angle) % 360
            picked_index = int(pointer_angle // angle_per_item) % len(menu_list)
            picked_menu = menu_list[picked_index]

            label_surface = result_font.render("오늘의 선택 : ", True, (0, 0, 0))
            bold_result_font = pygame.font.Font(FONT_PATH, 26)
            bold_result_font.set_bold(True)

            menu_surface = bold_result_font.render(f"{picked_menu}", True, (255, 160, 180))

            total_width = label_surface.get_width() + menu_surface.get_width()
            x_start = (WIDTH - total_width) // 2
            y_pos = HEIGHT - 70
            
            screen.blit(label_surface, (x_start, y_pos))
            screen.blit(menu_surface, (x_start + label_surface.get_width(), y_pos - 2))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_button.is_clicked(pygame.mouse.get_pos()):
                    return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not is_spinning:
                keydown_time = pygame.time.get_ticks()
            if event.type == pygame.KEYUP and event.key == pygame.K_SPACE and not is_spinning and keydown_time:
                held = (pygame.time.get_ticks() - keydown_time) / 1000
                keydown_time = None
                spin_speed = min(5 + held * 5, 20)
                is_spinning = True

        if is_spinning:
            current_angle += spin_speed
            spin_speed *= 0.993
            if spin_speed < 0.05:
                is_spinning = False
                has_spun = True

        draw_roulette(current_angle)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    version_select()
    pygame.quit()