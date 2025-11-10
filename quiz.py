from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
import os
import sys
import random
import re
import threading
import json
from tkinter import filedialog, Tk

# ===== 작업 디렉터리 고정 =====
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
except:
    pass

# ===== 폰트 등록(Fallback) =====
PRIMARY_FONT = "fonts/TmoneyRoundWindRegular.otf"
FALLBACK_FONT = "fonts/TmoneyRoundWindRegular.ttf"

def register_app_font():
    chosen = None
    if os.path.exists(PRIMARY_FONT): chosen = PRIMARY_FONT
    elif os.path.exists(FALLBACK_FONT): chosen = FALLBACK_FONT
    if chosen:
        try:
            LabelBase.register(name="AppFont", fn_regular=chosen)
            print("[FONT] Using:", chosen); return "AppFont"
        except Exception as e:
            print("[FONT] Register failed:", e)
    print("[FONT] WARNING: No KR font registered. Using default Kivy font.")
    return ""

FONT_NAME = register_app_font()
APP_VERSION = "1.0.1"

# ===================================================================
# ✅ 1. 앱 버전 설정
# ===================================================================
# 현재 앱에 하드코딩된 버전입니다. 새 버전 출시 시 이 값을 변경해야 합니다.
# ===================================================================

RE_TIME_UNITS = re.compile(r'(\d+)\s*(분|초)')
RE_SPLIT = re.compile(r'[\t, ]+')
RE_DIGITS = re.compile(r'\d+')

def contains_ascii(s):
    for c in s:
        cl = c.lower()
        if 'a' <= cl <= 'z':
            return True
    return False

def sp(px):
    """UI 스케일 고정: 창 크기에 따라 줄어들지 않게"""
    return int(px * 2.5)

# ===== 공용 UI =====
class Card(BoxLayout):
    def __init__(self, radius, bg_color, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius; self.bg_color = bg_color
        with self.canvas.before:
            self.color = Color(*self.bg_color)
            self.rect = RoundedRectangle(radius=[(self.radius, self.radius)]*4)
        self.bind(pos=self._upd, size=self._upd)
    def _upd(self, *a):
        self.rect.pos = self.pos; self.rect.size = self.size

class RoundBtn(AnchorLayout):
    def __init__(self, text, font_size, bg, color, radius, height, width=None, **kwargs):
        super().__init__(size_hint=(1, None), height=height, **kwargs)
        if width: self.size_hint, self.width = (None, None), width
        self.wrap = AnchorLayout(size_hint=(1,1))
        with self.wrap.canvas.before:
            self.bg_color_canvas = Color(*bg)
            self.wrap.rect = RoundedRectangle(radius=[(radius, radius)]*4)
        self.wrap.bind(pos=lambda *_: self._upd(), size=lambda *_: self._upd())
        self.btn = Button(text=text, font_name=FONT_NAME, font_size=font_size, color=color,
                          background_normal='', background_color=(0,0,0,0), size_hint=(1,1))
        self.wrap.add_widget(self.btn); self.add_widget(self.wrap)
        self._radius = radius
    def _upd(self):
        self.wrap.rect.pos = self.wrap.pos; self.wrap.rect.size = self.wrap.size

class AnswerInput(TextInput):
    def __init__(self, on_enter_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.on_enter_callback = on_enter_callback
    
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[0] == 13:
            if self.on_enter_callback:
                self.on_enter_callback()
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)

class OutlineBtn(AnchorLayout):
    def __init__(self, text, font_size, border_color, text_color, radius, height, **kwargs):
        super().__init__(size_hint=(1,None), height=height, **kwargs)
        self.wrap = AnchorLayout(size_hint=(1,1))
        with self.wrap.canvas.before:
            Color(0,0,0,0); self.wrap.bg = RoundedRectangle(radius=[(radius, radius)]*4)
            self.border_color_canvas = Color(*border_color)
            self.wrap.border = RoundedRectangle(radius=[(radius, radius)]*4)
        self.wrap.bind(pos=lambda *_: self._upd(), size=lambda *_: self._upd())
        self.btn = Button(text=text, font_name=FONT_NAME, font_size=font_size, color=text_color,
                          background_normal='', background_color=(0,0,0,0), size_hint=(1,1))
        self.wrap.add_widget(self.btn); self.add_widget(self.wrap)
    def _upd(self):
        self.wrap.bg.pos = self.wrap.pos; self.wrap.bg.size = self.wrap.size
        self.wrap.border.pos = self.wrap.pos; self.wrap.border.size = self.wrap.size

# =============================================================================
# ENGLISH WORD QUIZ APP
# =============================================================================
class EnglishWordQuizApp(App):
    is_dark_mode = True

    # Q.13, Q.14 단어 목록
    word_sets = {
        "Q.13": [
            ("사과","apple"), ("학교","school"), ("책","book"), ("연필","pencil"), ("독점,전매","monopoly"),
            ("과학","science"), ("사랑","love"), ("기회","chance"), ("성공","success"), ("자유","freedom")
        ],
        "Q.14": [
            ("행복","happiness"), ("건강","health"), ("지식","knowledge"), ("용기","courage"), ("평화","peace"),
            ("성장","growth"), ("선택","choice"), ("능력","ability"), ("노력","effort"), ("여행","travel")
        ]
    }
    current_word_set_name = "기본"

    # ===== THEME & COLORS =====
    def get_colors(self):
        if self.is_dark_mode:
            return {"APP_BG":(0.10,0.10,0.10,1), "CARD_BG":(0.15,0.15,0.15,1),
                    "TEXT":(1,1,1,1), "PRIMARY":(0.20,0.50,0.80,1),
                    "BORDER":(0.5,0.5,0.5,1), "RED":(0.90,0.25,0.25,1)}
        return {"APP_BG":(0.96,0.97,0.98,1), "CARD_BG":(1,1,1,1),
                "TEXT":(0,0,0,1), "PRIMARY":(0.16,0.26,0.39,1),
                "BORDER":(0.82,0.85,0.90,1), "RED":(0.88,0.20,0.20,1)}

    # ===== APP INITIALIZATION =====
    def build(self):
        # 화면 크기 감지 및 자동 조절
        try:
            root = Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()

            # 화면 크기의 적절한 비율로 설정 (최소/최대 제한)
            width = max(400, min(440, int(screen_width * 0.2)))
            height = max(600, min(800, int(screen_height * 0.4)))
            Window.size = (width, height)
        except:
            # 실패 시 기본 크기 사용
            Window.size = (400, 600)

        Window.minimum_width = 400
        Window.minimum_height = 600
        Window.raise_window()  # 창을 앞으로 가져와서 포커스 확보
        Window.clearcolor = self.get_colors()["CARD_BG"]

        # 창 아이콘 설정
        icon_path = r"C:\Users\RMARKET\Downloads\EnglishWordQuiz\EnglishWordQuiz\images\hooi.png"
        if os.path.exists(icon_path):
            Window.set_icon(icon_path)
        else:
            print(f"[ICON] 아이콘 파일을 찾을 수 없습니다: {icon_path}")
        self.words = [("사과","apple"),("학교","school"),("책","book"),("연필","pencil"),("독점,전매","monopoly")]
        self.score = 0
        self.current_index = 0
        self.mode = None

        # 저장된 상태 불러오기
        success, message = self.load_app_state()
        if success:
            print(f"[LOAD] {message}")
            # 다크 모드 설정 적용
            Window.clearcolor = self.get_colors()["CARD_BG"]
        else:
            print(f"[LOAD] {message}")

        # 타이머(전체 지속형)
        self.time_limit = None
        self.remaining = None
        self.timer_event = None
        self.lbl_timer = None

        # 오답 기록
        self.wrong_list = []

        # 글로벌 키보드 핸들러
        self.showing_result = False
        Window.bind(on_keyboard=self._on_window_keyboard)
        Window.bind(on_back_button=self._on_back_button)  # 모바일 뒤로가기 버튼

        # UI 캐싱을 위한 변수들
        self.question_top = None
        self.question_info = None
        self.question_center = None
        self.question_bottom = None
        self.question_root = None

        self.root_layout = BoxLayout(orientation='vertical', padding=[0,0,0,10], spacing=0)
        self.main_menu()

        return self.root_layout

    def _set_screen(self, widgets):
        self.root_layout.clear_widgets()
        if not isinstance(widgets, list): widgets = [widgets]
        for w in widgets: self.root_layout.add_widget(w)
        colors = self.get_colors()
        footer = BoxLayout(orientation='horizontal', size_hint=(1,None), height=40)
        ver = Label(text=APP_VERSION, font_name=FONT_NAME, font_size=17, color=colors["TEXT"],
                    size_hint=(None,None), width=100, height=40, halign='left', valign='middle')
        ver.bind(size=lambda i,v: setattr(i,'text_size',v))
        made_by = Label(text="Made by hooi", font_name=FONT_NAME, font_size=15, color=colors["TEXT"],
                        size_hint=(None,None), width=100, height=40, halign='right', valign='middle')
        made_by.bind(size=lambda i,v: setattr(i,'text_size',v))
        footer.add_widget(ver)
        footer.add_widget(BoxLayout())
        footer.add_widget(made_by)
        self.root_layout.add_widget(footer)
    
    def _on_window_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 27:  # ESC 키
            self.main_menu()
            return True
        elif self.showing_result and key == 13:
            self.main_menu()
            return True
        return False

    def _on_back_button(self, window):
        """모바일 뒤로가기 버튼 핸들러"""
        self.main_menu()
        return True

    # ===== UI COMPONENTS =====
    def _top_bar(self, title_text="메인", show_back=True):
        colors = self.get_colors()
        bar = BoxLayout(orientation='horizontal', size_hint=(1,None), height=60)
        if show_back:
            back = Button(text="←", font_name=FONT_NAME, font_size=24,
                          size_hint=(None,None), width=60, height=60,
                          background_normal='', background_color=(0,0,0,0), color=colors["TEXT"])
            back.bind(on_release=lambda x: self.main_menu()); bar.add_widget(back)
        else:
            bar.add_widget(BoxLayout(size_hint_x=None, width=60))
        title = Label(text=title_text, font_name=FONT_NAME, font_size=20, color=colors["TEXT"],
                      halign='center', valign='middle')
        bar.add_widget(title)
        bar.add_widget(BoxLayout(size_hint_x=None, width=60))
        return bar

    # ===== MAIN MENU =====
    def main_menu(self):
        colors = self.get_colors()
        # 타이머 정리
        self._cancel_timer()
        self.time_limit = None; self.remaining = None

        card = Card(radius=0, bg_color=colors["CARD_BG"], orientation='vertical',
                    padding=[25, 30, 25, 25], spacing=25, size_hint=(0.95, 1))

        # ===== 헤더: 로고와 타이틀 =====
        header = BoxLayout(orientation='horizontal', size_hint=(1,None), height=100, spacing=20)
        logo_img = Image(source='images/logo.png', size_hint=(None,None), size=(95, 95))
        title = Label(text="Word Quiz", font_name=FONT_NAME, font_size=45, color=colors["TEXT"],
                      size_hint=(1,None), height=100, halign='center', valign='middle')
        title.bind(size=lambda i,v: setattr(i,'text_size',v))
        happy_img = Image(source='images/happy_apple.png', size_hint=(None, None), size=(95, 95))
        header.add_widget(logo_img)
        header.add_widget(title)
        header.add_widget(happy_img)
        card.add_widget(header)

        # ===== 퀴즈 시작 버튼들 =====
        quiz_section = BoxLayout(orientation='vertical', size_hint=(1,None), height=170, spacing=15)
        quiz_title = Label(text="", font_name=FONT_NAME, font_size=18, color=colors["TEXT"],
                          size_hint=(1,None), height=30, halign='center', valign='middle')
        quiz_title.bind(size=lambda i,v: setattr(i,'text_size',v))
        quiz_section.add_widget(quiz_title)

        grid = GridLayout(cols=2, spacing=15, size_hint=(1,None), height=120)
        btn_en = RoundBtn("영단어 보고 맞추기", 24, colors["PRIMARY"], (1,1,1,1), 15, 120)
        btn_ko = RoundBtn("한글 보고 맞추기", 24, colors["PRIMARY"], (1,1,1,1), 15, 120)
        btn_en.btn.bind(on_release=lambda x: self.start_quiz("english"))
        btn_ko.btn.bind(on_release=lambda x: self.start_quiz("korean"))
        grid.add_widget(btn_en); grid.add_widget(btn_ko)
        quiz_section.add_widget(grid)
        card.add_widget(quiz_section)

        # ===== 단어 관리 섹션 =====
        manage_section = BoxLayout(orientation='vertical', size_hint=(1,None), height=125, spacing=10)
        manage_title = Label(text="", font_name=FONT_NAME, font_size=16, color=colors["TEXT"],
                            size_hint=(1,None), height=25, halign='center', valign='middle')
        manage_title.bind(size=lambda i,v: setattr(i,'text_size',v))
        manage_section.add_widget(manage_title)

        manage_grid = GridLayout(cols=2, spacing=10, size_hint=(1,None), height=100)
        btn_manage = OutlineBtn("단어 관리", 24, colors["BORDER"], colors["TEXT"], 12, 100)
        btn_list = OutlineBtn("단어 목록", 24, colors["BORDER"], colors["TEXT"], 12, 100)
        btn_manage.btn.bind(on_release=lambda x: self.show_word_management_menu())
        btn_list.btn.bind(on_release=lambda x: self.show_word_list_screen(show_delete_buttons=False))
        manage_grid.add_widget(btn_manage)
        manage_grid.add_widget(btn_list)
        manage_section.add_widget(manage_grid)
        card.add_widget(manage_section)

        # ===== 추가 기능 =====
        extra_section = BoxLayout(orientation='vertical', size_hint=(1,None), height=100, spacing=8)
        extra_title = Label(text="", font_name=FONT_NAME, font_size=16, color=colors["TEXT"],
                           size_hint=(1,None), height=25, halign='center', valign='middle')
        extra_title.bind(size=lambda i,v: setattr(i,'text_size',v))
        extra_section.add_widget(extra_title)

        btn_other = OutlineBtn("다른 모드", 24, colors["BORDER"], colors["TEXT"], 12, 75)
        btn_other.btn.bind(on_release=lambda x: self.open_other_mode_picker())
        extra_section.add_widget(btn_other)
        card.add_widget(extra_section)

        # ===== 시스템 버튼들 =====
        system_section = BoxLayout(orientation='horizontal', size_hint=(1,None), height=75, spacing=15)
        btn_save = OutlineBtn("저장", 22, colors["BORDER"], colors["TEXT"], 10, 75, size_hint_x=None, width=80)
        btn_load = OutlineBtn("불러오기", 22, colors["BORDER"], colors["TEXT"], 10, 75, size_hint_x=None, width=95)
        btn_mode = OutlineBtn("다크 모드" if not self.is_dark_mode else "라이트 모드",
                              22, colors["BORDER"], colors["TEXT"], 10, 75, size_hint_x=None, width=120)
        btn_exit = RoundBtn("종료", 24, colors["RED"], (1,1,1,1), 12, 75, size_hint_x=None, width=80)

        btn_save.btn.bind(on_release=self.save_app_state_ui)
        btn_load.btn.bind(on_release=self.load_app_state_ui)
        btn_mode.btn.bind(on_release=self.toggle_dark_mode)
        btn_exit.btn.bind(on_release=lambda x: self.exit_app())

        system_section.add_widget(btn_save)
        system_section.add_widget(btn_load)
        system_section.add_widget(btn_mode)
        system_section.add_widget(BoxLayout())
        system_section.add_widget(btn_exit)
        card.add_widget(system_section)

        stage = AnchorLayout(anchor_x='center', anchor_y='top', padding=[0, 0, 0, 0], size_hint=(1, 1))
        stage.add_widget(card)
        self._set_screen(stage)

    # ===== SETTINGS =====
    def toggle_dark_mode(self, *a):
        self.is_dark_mode = not self.is_dark_mode
        Window.clearcolor = self.get_colors()["CARD_BG"]
        self.main_menu()

    def save_app_state_ui(self, *a):
        """UI에서 저장 기능 호출"""
        success, message = self.save_app_state()
        self._show_info(message)

    def load_app_state_ui(self, *a):
        """UI에서 불러오기 기능 호출"""
        success, message = self.load_app_state()
        self._show_info(message)
        if success:
            # 불러오기 성공 시 메인 메뉴 새로고침
            self.main_menu()

    # ===== WORD MANAGEMENT =====
    def show_contents_popup(self):
        colors = self.get_colors()
        content = BoxLayout(orientation='vertical', padding=sp(12), spacing=sp(10))
        title = Label(text="목차", font_name=FONT_NAME, font_size=sp(20), color=colors["TEXT"],
                      size_hint_y=None, height=sp(40), halign='center', valign='middle')
        title.bind(size=lambda i,v: setattr(i,'text_size',v))
        content.add_widget(title)

        scroll = ScrollView(size_hint=(1,1))
        btn_layout = GridLayout(cols=3, spacing=sp(8), size_hint_y=None)
        btn_layout.bind(minimum_height=btn_layout.setter('height'))

        sorted_keys = sorted(self.word_sets.keys(), key=lambda x: int(RE_DIGITS.search(x).group()) if RE_DIGITS.search(x) else 0)
        for key in sorted_keys:
            btn = RoundBtn(key, sp(16), colors["PRIMARY"], (1,1,1,1), sp(12), sp(50))
            btn.btn.bind(on_release=lambda x, k=key: self.set_word_set(k))
            btn_layout.add_widget(btn)

        scroll.add_widget(btn_layout)
        content.add_widget(scroll)

        # 하단 버튼: 왼쪽 닫기, 오른쪽 추가(→ 단어 추가(파일/수동))
        bottom = BoxLayout(orientation='horizontal', size_hint=(1,None), height=sp(54), spacing=sp(8))
        btn_close = OutlineBtn("닫기", sp(16), colors["BORDER"], colors["TEXT"], sp(14), sp(46))
        btn_add = RoundBtn("추가", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46), width=sp(100))
        bottom.add_widget(btn_close); bottom.add_widget(BoxLayout()); bottom.add_widget(btn_add)
        content.add_widget(bottom)

        self.contents_popup = Popup(title="", content=content, size_hint=(0.92, 0.8), auto_dismiss=False,
                                    background_color=colors["APP_BG"])
        btn_close.btn.bind(on_release=self.contents_popup.dismiss)
        btn_add.btn.bind(on_release=lambda x: (self.contents_popup.dismiss(), self.show_add_words_advanced()))
        self.contents_popup.open()

    def show_word_management_menu(self):
        """단어 관리 메뉴 - 목차 팝업 호출"""
        self.show_contents_popup()

    def _show_info(self, msg):
        colors = self.get_colors()
        box = BoxLayout(orientation='vertical', padding=(sp(12), sp(27), sp(12), sp(12)), spacing=sp(10))
        lbl = Label(text=msg, font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                    size_hint=(1,None), height=sp(36), halign='center', valign='middle')
        lbl.bind(size=lambda i,v: setattr(i,'text_size',v))
        ok = RoundBtn("확인", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        box.add_widget(lbl); box.add_widget(ok)
        p = Popup(title="", content=box, size_hint=(0.8,0.3), auto_dismiss=False, background_color=colors["APP_BG"])
        ok.btn.bind(on_release=p.dismiss); p.open()

    def set_word_set(self, set_name):
        # 팝업 닫기
        try:
            self.contents_popup.dismiss()
        except:
            pass

        # 단어 목록 변경
        self.words = list(self.word_sets[set_name])
        self.current_word_set_name = set_name

        # 안전한 번호 추출
        m = RE_DIGITS.search(set_name)
        qlabel = f"Q.{m.group()}" if m else set_name

        # 안내 메시지
        colors = self.get_colors()
        content = BoxLayout(orientation='vertical', padding=sp(16), spacing=sp(12))
        msg = Label(text=f"{qlabel}으로 설정되었습니다!",
                    font_name=FONT_NAME, font_size=sp(18), color=colors["TEXT"],
                    size_hint=(1,None), height=sp(44), halign='center', valign='middle')
        msg.bind(size=lambda i,v: setattr(i,'text_size',v))
        btn_ok = RoundBtn("확인", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        content.add_widget(msg); content.add_widget(btn_ok)
        info_popup = Popup(title="", content=content, size_hint=(0.86, 0.32), auto_dismiss=False,
                           background_color=colors["APP_BG"])
        btn_ok.btn.bind(on_release=lambda x: (info_popup.dismiss(), self.main_menu()))
        info_popup.open()

    # ===== 단어 목록 =====
    def show_word_list_screen(self, show_delete_buttons=True):
        colors = self.get_colors()
        top = self._top_bar("단어 목록")
        items = list(self.words); items.sort(key=lambda x:(x[0], x[1]))

        content = BoxLayout(orientation='vertical', spacing=sp(8), padding=sp(12))
        title = Label(text=f"총 {len(items)}개 단어", font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                      size_hint=(1,None), height=sp(28), halign='center', valign='middle')
        title.bind(size=lambda i,v: setattr(i,'text_size',v))
        content.add_widget(title)

        scroll = ScrollView(size_hint=(1,1))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=sp(6), padding=[0,0,0,sp(6)])
        list_layout.bind(minimum_height=list_layout.setter('height'))

        for kor, eng in items:
            row = BoxLayout(orientation='horizontal', size_hint=(1,None), height=sp(36), spacing=sp(8))
            lbl = Label(text=f"{kor}  -  {eng}", font_name=FONT_NAME, font_size=sp(14), color=colors["TEXT"],
                        size_hint=(1,None), height=sp(36), halign='left', valign='middle')
            lbl.bind(size=lambda i,v: setattr(i,'text_size',v))

            if show_delete_buttons:
                del_btn = Button(text="삭제", font_name=FONT_NAME, font_size=sp(13),
                                 size_hint=(None,None), width=sp(64), height=sp(32),
                                 background_normal='', background_color=(0,0,0,0), color=colors["RED"])
                del_btn.bind(on_release=lambda x, k=kor, e=eng: self.delete_word(k, e))
                row.add_widget(del_btn)

            row.add_widget(lbl)
            list_layout.add_widget(row)

        scroll.add_widget(list_layout); content.add_widget(scroll)
        btn_close = OutlineBtn("닫기", sp(16), colors["BORDER"], colors["TEXT"], sp(14), sp(46))
        btn_close.btn.bind(on_release=lambda x: self.main_menu())
        content.add_widget(btn_close)
        self._set_screen([top, content])

    def delete_word(self, kor, eng):
        self.words = [w for w in self.words if not (w[0]==kor and w[1]==eng)]
        self.show_word_list_screen(show_delete_buttons=True)

    # ===== QUIZ MODES =====
    def open_other_mode_picker(self):
        colors = self.get_colors()
        content = BoxLayout(orientation='vertical', spacing=sp(10), padding=sp(12))
        info = Label(text="다른 모드 선택", font_name=FONT_NAME, font_size=sp(18), color=colors["TEXT"],
                     size_hint=(1,None), height=sp(34), halign='center', valign='middle')
        info.bind(size=lambda i,v: setattr(i,'text_size',v))
        content.add_widget(info)
        btn_mix = RoundBtn("영어, 한글 섞은 모드", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(48))
        btn_time = RoundBtn("시간 제한 모드 (분/초 설정)", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(48))
        btn_close = OutlineBtn("닫기", sp(15), colors["BORDER"], colors["TEXT"], sp(14), sp(46))
        content.add_widget(btn_mix); content.add_widget(btn_time); content.add_widget(btn_close)
        popup = Popup(title="", content=content, size_hint=(0.92, 0.48), auto_dismiss=False,
                      background_color=colors["APP_BG"])
        btn_mix.btn.bind(on_release=lambda x: (popup.dismiss(), self.start_quiz("mixed")))
        btn_time.btn.bind(on_release=lambda x: (popup.dismiss(), self.show_timed_mode_screen()))
        btn_close.btn.bind(on_release=popup.dismiss)
        popup.open()

    def show_timed_mode_screen(self):
        colors = self.get_colors()
        top_bar = self._top_bar("시간 제한 모드")

        stage = AnchorLayout(anchor_x='center', anchor_y='center')
        card = Card(radius=sp(22), bg_color=colors["CARD_BG"],
                    orientation='vertical', padding=sp(16), spacing=sp(12),
                    size_hint=(0.92, None), height=sp(230))

        guide = Label(text="시간을 입력하세요 (예: 90초 / 1분 30초 / 1:30)",
                      font_name=FONT_NAME, font_size=sp(14), color=colors["TEXT"],
                      size_hint=(1,None), height=sp(40), halign='center', valign='middle')
        guide.bind(size=lambda i,v: setattr(i,'text_size',v))
        card.add_widget(guide)

        wrap_input = AnchorLayout(size_hint=(1,None), height=sp(54))
        self.ti_time = TextInput(text="1분 30초", multiline=False, font_name=FONT_NAME, font_size=sp(18),
                                 size_hint=(0.82,None), height=sp(46),
                                 foreground_color=colors["TEXT"], background_color=colors["CARD_BG"],
                                 cursor_color=colors["PRIMARY"])
        self.ti_time.bind(on_text_validate=lambda x: self.start_quiz_timed())
        wrap_input.add_widget(self.ti_time)
        card.add_widget(wrap_input)

        btn_row = BoxLayout(size_hint=(1,None), height=sp(50), spacing=sp(10))
        btn_cancel = OutlineBtn("취소", sp(15), colors["BORDER"], colors["TEXT"], sp(14), sp(46))
        btn_ok = RoundBtn("시작", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        btn_row.add_widget(btn_cancel); btn_row.add_widget(btn_ok)
        card.add_widget(btn_row)

        btn_cancel.btn.bind(on_release=lambda x: self.main_menu())
        btn_ok.btn.bind(on_release=lambda x: self.start_quiz_timed())

        stage.add_widget(card)

        root = BoxLayout(orientation='vertical', padding=[sp(10), sp(6), sp(10), sp(10)], spacing=sp(6))
        root.add_widget(top_bar); root.add_widget(BoxLayout()); root.add_widget(stage)
        self._set_screen(root)

    def parse_time_to_seconds(self, text):
        t = text.strip()
        m = RE_TIME_UNITS.findall(t)
        if m:
            total = 0
            for num, unit in m:
                v = int(num); total += v*60 if unit=='분' else v
            return max(1, total)
        if t.isdigit(): return max(1, int(t))
        if ':' in t:
            try:
                mm, ss = t.split(':'); return max(1, int(mm)*60 + int(ss))
            except: pass
        return 60

    # ===== QUIZ LOGIC =====
    def start_quiz_timed(self):
        # 타이머 '한 번만' 시작 (문제 넘어가도 유지)
        sec = self.parse_time_to_seconds(self.ti_time.text if hasattr(self,'ti_time') else "60")
        self.time_limit = sec
        self.mode = "timed"
        self.score = 0
        self.current_index = 0
        self.wrong_list = []
        self._cancel_timer()
        self.showing_result = False
        self.remaining = int(self.time_limit)
        self.timer_event = Clock.schedule_interval(self._tick, 1)
        random.shuffle(self.words)
        self.show_question()

    # ===== 일반 모드 시작 =====
    def start_quiz(self, mode):
        self.mode = mode; self.score = 0; self.current_index = 0; self.wrong_list = []
        self._cancel_timer(); self.time_limit = None; self.remaining = None
        self.showing_result = False
        random.shuffle(self.words); self.show_question()

    def show_question(self):
        self._graded = False
        colors = self.get_colors()
        if self.current_index >= len(self.words):
            return self.show_result()

        kor, eng = self.words[self.current_index]
        if self.mode == "english":
            question, self.correct_answer = eng, kor
        elif self.mode == "korean":
            question, self.correct_answer = kor, eng
        elif self.mode in ("mixed","timed"):
            if random.random() < 0.5: question, self.correct_answer = eng, kor
            else: question, self.correct_answer = kor, eng
        else:
            question, self.correct_answer = eng, kor

        # UI 재사용 또는 생성
        if self.question_top is None:
            self.question_top = self._top_bar("문제", show_back=True)
            self.question_info = BoxLayout(orientation='horizontal', size_hint=(1,None), height=sp(26), spacing=sp(8))
            self.lbl_progress = Label(text="", font_name=FONT_NAME, font_size=sp(15), color=colors["TEXT"],
                                      size_hint=(None,None), width=sp(80), height=sp(24),
                                      halign='center', valign='middle')
            self.lbl_progress.bind(size=lambda i,v: setattr(i,'text_size',v))
            self.question_info.add_widget(self.lbl_progress)

            self.lbl_timer = Label(text="", font_name=FONT_NAME, font_size=sp(15), color=colors["TEXT"],
                                   size_hint=(1,None), height=sp(24), halign='right', valign='middle')
            self.lbl_timer.bind(size=lambda i,v: setattr(i,'text_size',v))
            self.question_info.add_widget(self.lbl_timer)

            self.question_center = AnchorLayout(anchor_x='center', anchor_y='center')
            self.stack = BoxLayout(orientation='vertical', size_hint=(1,None), spacing=sp(8))
            self.stack.height = sp(70) + sp(48) + sp(22)

            self.lbl_q = Label(text="", font_size=sp(26), font_name=FONT_NAME, color=colors["TEXT"],
                               size_hint=(1,None), height=sp(70), halign='center', valign='middle')
            self.lbl_q.bind(size=lambda i,v: setattr(i,'text_size',v))

            self.entry = AnswerInput(on_enter_callback=self.on_bottom_click, multiline=False, font_size=sp(18), font_name=FONT_NAME,
                                     size_hint=(1,None), height=sp(48),
                                     foreground_color=colors["TEXT"], background_color=colors["CARD_BG"],
                                     cursor_color=colors["PRIMARY"])

            self.result_label = Label(text="", font_size=sp(15), font_name=FONT_NAME, color=colors["TEXT"],
                                      size_hint=(1,None), height=sp(22), halign='center', valign='middle')
            self.result_label.bind(size=lambda i,v: setattr(i,'text_size',v))

            self.stack.add_widget(self.lbl_q); self.stack.add_widget(self.entry); self.stack.add_widget(self.result_label)
            self.question_center.add_widget(self.stack)

            self.question_bottom = RoundBtn("제출", sp(18), colors["PRIMARY"], (1,1,1,1), sp(16), sp(52))
            self.question_bottom.btn.bind(on_release=self.on_bottom_click)
            self.bottom_btn_container = self.question_bottom

            self.question_root = BoxLayout(orientation='vertical', padding=[sp(10),sp(6),sp(10),sp(10)], spacing=sp(6))
            self.question_root.add_widget(self.question_top); self.question_root.add_widget(self.question_info)
            self.question_root.add_widget(BoxLayout()); self.question_root.add_widget(self.question_center); self.question_root.add_widget(BoxLayout()); self.question_root.add_widget(self.question_bottom)

        # UI 업데이트
        self.lbl_progress.text = f"{self.current_index+1}/{len(self.words)}"
        self.lbl_q.text = question
        self.entry.text = ""
        self.result_label.text = ""
        self.question_bottom.btn.text = "제출"

        self._set_screen(self.question_root)
        Clock.schedule_once(lambda dt: self._focus_entry(), 0.1)

        # 타이머는 여기서 재시작하지 않음(라벨만 갱신)
        if self.mode == "timed" and self.remaining is not None:
            self._update_timer_label()
        else:
            self.lbl_timer.text = ""

    def _sec_to_mmss(self, sec):
        m = sec // 60; s = sec % 60
        return f"{m:02d}:{s:02d}"

    def _update_timer_label(self):
        if self.lbl_timer is not None and self.remaining is not None:
            self.lbl_timer.text = f"남은 시간 {self._sec_to_mmss(max(0, self.remaining))}"

    def _tick(self, dt):
        if self.remaining is None: return
        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self._cancel_timer()
            self._graded = True
            self.result_label.text = "타임 아웃!"
            self.result_label.color = self.get_colors()["RED"]
            self._update_timer_label()
            if hasattr(self, "bottom_btn_container"):
                self.bottom_btn_container.btn.text = "메뉴로 돌아가기"
                self.bottom_btn_container.btn.unbind(on_release=self.on_bottom_click)
                self.bottom_btn_container.btn.bind(on_release=lambda x: self.main_menu())
        else:
            self._update_timer_label()

    def _focus_entry(self):
        try: self.entry.focus = True
        except: pass

    def on_bottom_click(self, instance=None):
        if not getattr(self, "_graded", False):
            self._grade_current()
            if hasattr(self, "bottom_btn_container"):
                self.bottom_btn_container.btn.text = "다음으로"
        else:
            self.current_index += 1
            if self.current_index >= len(self.words):
                self.show_result()
            else:
                self.show_question()

    def _split_kor_senses(self, kor_text):
        parts = [p.strip() for p in kor_text.split(",")]
        return {p for p in parts if p}

    def _grade_current(self, *args):
        if getattr(self, "_graded", False): return
        colors = self.get_colors()
        user_raw = self.entry.text.strip()
        if contains_ascii(self.correct_answer):
            is_correct = (user_raw.lower() == self.correct_answer.lower())
        else:
            kor_set = self._split_kor_senses(self.correct_answer)
            user_set = self._split_kor_senses(user_raw)
            is_correct = len(kor_set.intersection(user_set)) > 0

        if is_correct:
            self.result_label.text = "정답입니다!"
            self.result_label.color = colors["PRIMARY"]
            self.score += 1
        else:
            self.result_label.text = f"틀렸습니다! 정답: {self.correct_answer}"
            self.result_label.color = colors["RED"]
            kor, eng = self.words[self.current_index]
            if self.mode == "english": question = eng
            elif self.mode == "korean": question = kor
            elif self.mode in ("mixed","timed"):
                question = kor if contains_ascii(self.correct_answer) else eng
            else: question = eng
            self.wrong_list.append((question, self.correct_answer, user_raw if user_raw else "(빈 입력)"))

        self._graded = True

    # ===== QUIZ RESULTS =====
    def show_result(self):
        colors = self.get_colors()
        self._cancel_timer(); self.remaining = None

        total = len(self.words); correct = self.score; wrong = total - correct
        top = self._top_bar("결과", show_back=False)
        msg = f"총 {total}문제 중\n맞은 개수: {correct}\n틀린 개수: {wrong}"
        lbl = Label(text=msg, font_name=FONT_NAME, font_size=sp(20), color=colors["TEXT"],
                    size_hint=(1,None), height=sp(140), halign='center', valign='middle')
        lbl.bind(size=lambda i,v: setattr(i,'text_size',v))

        btns = BoxLayout(orientation='vertical', size_hint=(1,None), height=sp(120), spacing=sp(8))
        btn_wrong = OutlineBtn("틀린 단어 보기", sp(16), colors["BORDER"], colors["TEXT"], sp(16), sp(50))
        btn_wrong.btn.bind(on_release=lambda x: self.show_wrong_list_screen())
        btn_home = RoundBtn("메인으로", sp(18), colors["PRIMARY"], (1,1,1,1), sp(16), sp(50))
        btn_home.btn.bind(on_release=lambda x: self.main_menu())
        btns.add_widget(btn_wrong); btns.add_widget(btn_home)

        layout = BoxLayout(orientation='vertical', padding=[sp(10),sp(6),sp(10),sp(10)], spacing=sp(10))
        layout.add_widget(top); layout.add_widget(lbl); layout.add_widget(btns)
        
        hidden_input = AnswerInput(on_enter_callback=self.main_menu, size_hint=(1, None), height=0)
        layout.add_widget(hidden_input)
        
        self._set_screen(layout)
        Clock.schedule_once(lambda dt: setattr(hidden_input, 'focus', True), 0.1)
        
        self.showing_result = True

    def show_wrong_list_screen(self):
        colors = self.get_colors()
        top = self._top_bar("틀린 단어", show_back=True)
        content = BoxLayout(orientation='vertical', spacing=sp(8), padding=sp(12))
        title = Label(text=f"오답 {len(self.wrong_list)}개", font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                      size_hint=(1,None), height=sp(28), halign='center', valign='middle')
        title.bind(size=lambda i,v: setattr(i,'text_size',v))
        content.add_widget(title)

        scroll = ScrollView(size_hint=(1,1))
        list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=sp(6))
        list_layout.bind(minimum_height=list_layout.setter('height'))

        if not self.wrong_list:
            empty = Label(text="오답이 없습니다!", font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                          size_hint=(1,None), height=sp(40), halign='center', valign='middle')
            empty.bind(size=lambda i,v: setattr(i,'text_size',v))
            list_layout.add_widget(empty)
        else:
            for q, ans, ua in self.wrong_list:
                row = BoxLayout(orientation='vertical', size_hint=(1,None), height=sp(60), padding=[0,sp(2),0,sp(2)])
                l1 = Label(text=f"문제: {q}", font_name=FONT_NAME, font_size=sp(14), color=colors["TEXT"],
                           size_hint=(1,None), height=sp(20), halign='left', valign='middle')
                l2 = Label(text=f"정답: {ans}", font_name=FONT_NAME, font_size=sp(14), color=colors["PRIMARY"],
                           size_hint=(1,None), height=sp(20), halign='left', valign='middle')
                l3 = Label(text=f"내 답: {ua}", font_name=FONT_NAME, font_size=sp(14), color=colors["RED"],
                           size_hint=(1,None), height=sp(20), halign='left', valign='middle')
                for lab in (l1,l2,l3): lab.bind(size=lambda i,v: setattr(i,'text_size',v))
                row.add_widget(l1); row.add_widget(l2); row.add_widget(l3)
                list_layout.add_widget(row)

        scroll.add_widget(list_layout)
        content.add_widget(scroll)

        btn_home = RoundBtn("메인으로", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        btn_home.btn.bind(on_release=lambda x: self.main_menu())
        content.add_widget(btn_home)
        self._set_screen([top, content])

    # ===== FILE OPERATIONS =====
    def show_add_words_advanced(self):
        colors = self.get_colors()
        top = self._top_bar("단어 추가(파일/수동)")
        content = BoxLayout(orientation='vertical', padding=sp(16), spacing=sp(12))

        hint = "수동 입력 또는 파일로 단어를 추가할 수 있어요.\n형식: 한 줄에 '한글 영어' (쉼표/탭 구분도 가능)"
        hint_label = Label(text=hint, font_name=FONT_NAME, font_size=sp(14), color=colors["TEXT"],
                           size_hint_y=None, height=sp(60), halign='left', valign='top')
        hint_label.bind(size=lambda i,v: setattr(i,'text_size',v))
        content.add_widget(hint_label)

        self.txt_input = TextInput(text="", multiline=True, font_name=FONT_NAME, font_size=sp(16),
                                   size_hint=(1,1), background_color=colors["CARD_BG"],
                                   foreground_color=colors["TEXT"], cursor_color=colors["PRIMARY"])
        content.add_widget(self.txt_input)

        row1 = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(8))
        btn_close = OutlineBtn("닫기", sp(15), colors["BORDER"], colors["TEXT"], sp(14), sp(46))
        btn_add_manual = RoundBtn("수동 추가", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        row1.add_widget(btn_close); row1.add_widget(btn_add_manual)
        content.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=sp(50), spacing=sp(8))
        btn_add_txt = RoundBtn("TXT에서 추가", sp(15), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        btn_add_excel = RoundBtn("엑셀에서 추가", sp(15), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        row2.add_widget(btn_add_txt); row2.add_widget(btn_add_excel)
        content.add_widget(row2)

        btn_close.btn.bind(on_release=lambda x: self.main_menu())
        btn_add_manual.btn.bind(on_release=self._add_words_from_textinput)

        # 파일 선택(Tkinter filedialog) 연결
        btn_add_txt.btn.bind(on_release=lambda x: self._open_file_chooser(".txt 파일 선택", filters=["*.txt"], on_chosen=self._after_choose_txt))
        btn_add_excel.btn.bind(on_release=lambda x: self._open_file_chooser("엑셀(.xlsx) 파일 선택", filters=["*.xlsx"], on_chosen=self._after_choose_excel))

        self._set_screen([top, content])

    # ===== Kivy 파일 선택기 =====
    def _open_kivy_file_chooser(self, file_type):
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        colors = self.get_colors()

        # 파일 선택기 생성
        filechooser = FileChooserListView(path=os.path.expanduser("~"),
                                          filters=['*.txt'] if file_type == 'txt' else ['*.xlsx'])

        # 팝업 생성
        popup = Popup(title=".txt 파일 선택" if file_type == 'txt' else "엑셀(.xlsx) 파일 선택",
                      size_hint=(0.9, 0.9), background_color=colors["APP_BG"])

        # 선택 시 콜백
        def select_file(instance):
            if filechooser.selection:
                path = filechooser.selection[0]
                popup.dismiss()
                if file_type == 'txt':
                    self._after_choose_txt(path)
                else:
                    self._after_choose_excel(path)
            else:
                popup.dismiss()

        # 버튼 추가
        btn_select = Button(text="선택", font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                            background_color=colors["PRIMARY"], size_hint_y=None, height=sp(50))
        btn_select.bind(on_release=select_file)
        btn_cancel = Button(text="취소", font_name=FONT_NAME, font_size=sp(16), color=colors["TEXT"],
                            background_color=colors["BORDER"], size_hint_y=None, height=sp(50))
        btn_cancel.bind(on_release=popup.dismiss)

        layout = BoxLayout(orientation='vertical')
        layout.add_widget(filechooser)
        bottom = BoxLayout(size_hint_y=None, height=sp(50))
        bottom.add_widget(btn_select)
        bottom.add_widget(btn_cancel)
        layout.add_widget(bottom)

        popup.content = layout
        popup.open()

    # ===== 파일 선택 공용 팝업 =====
    def _open_file_chooser(self, title, start_dir=None, filters=None, on_chosen=None):
        if start_dir is None:
            start_dir = os.path.expanduser("~")
        def pick_file():
            root = Tk()
            root.withdraw()
            fts = [("All files", "*.*")]
            if filters:
                fl = " ".join(filters)
                if ("xlsx" in fl) or ("xls" in fl):
                    fts = [("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
                elif "txt" in fl:
                    fts = [("Text files", "*.txt"), ("All files", "*.*")]
            path = filedialog.askopenfilename(title=title, initialdir=start_dir, filetypes=fts)
            root.destroy()
            if path:
                if on_chosen:
                    Clock.schedule_once(lambda dt, p=path: on_chosen(p), 0)
            else:
                Clock.schedule_once(lambda dt: self._info_popup("파일이 선택되지 않았습니다"), 0)
        thread = threading.Thread(target=pick_file)
        thread.daemon = True
        thread.start()

    def _after_choose_txt(self, path):
        added, skipped = self._load_words_from_txt(path)
        self._info_popup(f".txt 추가 완료\n추가: {added}개 / 건너뜀: {skipped}개")
        self.main_menu()

    def _after_choose_excel(self, path):
        added, skipped, msg = self._load_words_from_excel(path)
        if msg:
            self._info_popup(msg)
        else:
            self._info_popup(f"엑셀 추가 완료\n추가: {added}개 / 건너뜀: {skipped}개")
        self.main_menu()

    # ===== 수동 입력 처리 =====
    def _add_words_from_textinput(self, *args):
        lines = [ln for ln in self.txt_input.text.split("\n") if ln.strip()]
        added = skipped = 0
        existing = set(tuple(w) for w in self.words)  # 중복 체크를 위한 세트
        for line in lines:
            parts = RE_SPLIT.split(line.strip())
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                kor, eng = parts[0].strip(), parts[1].strip().lower()
                word_tuple = (kor, eng)
                if kor and eng and word_tuple not in existing:
                    self.words.append(word_tuple); added += 1
                    existing.add(word_tuple)
                else:
                    skipped += 1
            else:
                skipped += 1
        self._info_popup(f"수동 추가 완료\n추가: {added}개 / 건너뜀: {skipped}개")
        self.main_menu()

    def _info_popup(self, msg):
        colors = self.get_colors()
        box = BoxLayout(orientation='vertical', padding=(sp(12), sp(27), sp(12), sp(12)), spacing=sp(10))
        lbl = Label(text=msg, font_name=FONT_NAME, font_size=sp(12), color=colors["TEXT"],
                    size_hint=(1,None), height=sp(40), halign='center', valign='middle')
        lbl.bind(size=lambda i,v: setattr(i,'text_size',v))
        ok = RoundBtn("확인", sp(16), colors["PRIMARY"], (1,1,1,1), sp(14), sp(46))
        box.add_widget(lbl); box.add_widget(ok)
        p = Popup(title="", content=box, size_hint=(0.78,0.32), auto_dismiss=False, background_color=colors["APP_BG"])
        ok.btn.bind(on_release=p.dismiss); p.open()

    # ===== .txt 로드 =====
    def _load_words_from_txt(self, path):
        added = skipped = 0
        existing = set(tuple(w) for w in self.words)  # 중복 체크
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    parts = RE_SPLIT.split(raw)
                    parts = [p for p in parts if p]
                    if len(parts) >= 2:
                        kor, eng = parts[0].strip(), parts[1].strip().lower()
                        word_tuple = (kor, eng)
                        if kor and eng and word_tuple not in existing:
                            self.words.append(word_tuple); added += 1
                            existing.add(word_tuple)
                        else:
                            skipped += 1
                    else:
                        skipped += 1
        except Exception as e:
            print("[TXT LOAD ERROR]", e)
            return 0, 0
        return added, skipped

    # ===== 엑셀 로드 =====
    def _load_words_from_excel(self, path):
        try:
            import pandas as pd
        except Exception:
            return 0, 0, "pandas가 필요합니다.\n'pandas'와 'openpyxl'을 설치하세요."
        added = skipped = 0
        existing = set(tuple(w) for w in self.words)  # 중복 체크
        try:
            df = pd.read_excel(path, header=None)
            for _, row in df.iterrows():
                kor = str(row[0]).strip() if 0 in row else ""
                eng = str(row[1]).strip().lower() if 1 in row else ""
                if kor.lower() == "nan": kor = ""
                if eng.lower() == "nan": eng = ""
                word_tuple = (kor, eng)
                if kor and eng and word_tuple not in existing:
                    self.words.append(word_tuple); added += 1
                    existing.add(word_tuple)
                else:
                    skipped += 1
            return added, skipped, ""
        except Exception as e:
            print("[EXCEL LOAD ERROR]", e)
            return 0, 0, "엑셀 읽기에 실패했습니다.\n경로/형식을 확인하세요."

    # ===== SAVE/LOAD =====
    def get_save_data(self):
        """현재 앱 상태를 저장할 데이터 구조를 반환"""
        return {
            "words": self.words,
            "current_word_set_name": self.current_word_set_name,
            "is_dark_mode": self.is_dark_mode,
            "custom_word_sets": {k: v for k, v in self.word_sets.items() if k not in ["Q.13", "Q.14"]}  # 기본 세트 제외
        }

    def save_app_state(self):
        """앱 상태를 JSON 파일로 저장"""
        try:
            save_data = self.get_save_data()
            save_path = os.path.join(base_dir, "quiz_save.json")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True, "저장되었습니다."
        except Exception as e:
            print(f"[SAVE ERROR] {e}")
            return False, f"저장 실패: {str(e)}"

    def load_app_state(self):
        """JSON 파일에서 앱 상태를 불러오기"""
        try:
            save_path = os.path.join(base_dir, "quiz_save.json")
            if not os.path.exists(save_path):
                return False, "저장 파일이 없습니다."

            with open(save_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)

            # 데이터 불러오기
            if "words" in save_data:
                self.words = save_data["words"]
            if "current_word_set_name" in save_data:
                self.current_word_set_name = save_data["current_word_set_name"]
            if "is_dark_mode" in save_data:
                self.is_dark_mode = save_data["is_dark_mode"]
            if "custom_word_sets" in save_data:
                # 기본 세트 유지하면서 커스텀 세트 추가
                for k, v in save_data["custom_word_sets"].items():
                    self.word_sets[k] = v

            return True, "불러오기가 완료되었습니다."
        except Exception as e:
            print(f"[LOAD ERROR] {e}")
            return False, f"불러오기 실패: {str(e)}"

    # ===== UTILITIES =====
    def _cancel_timer(self):
        if getattr(self,'timer_event', None):
            try: self.timer_event.cancel()
            except: pass
            self.timer_event = None



    def exit_app(self):
        App.get_running_app().stop()
        try: Window.close()
        except: pass
        sys.exit(0)

if __name__ == "__main__":
    EnglishWordQuizApp().run()