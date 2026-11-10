import json
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "quotes_data.json")

THEME_FILE = os.path.join(BASE_DIR, "theme.json")
AUTOSAVE_INTERVAL = 30_000  # 30초 (밀리초)

class QuoteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("잘생긴 프로그램")
        self.root.geometry("800x550")
        self.root.minsize(700, 500)

        self.dark_mode = self.load_theme()
        self.autosave_job = None

        # 데이터 구조: { "이름": {"quotes": ["어록1", "어록2"], "favorite": True/False} }
        self.data = {}
        self.current_person = None
        self.current_mode = "어록"

        self.load_data()
        self.create_widgets()
        self.apply_theme()
        self.start_autosave()
        
        # 창을 닫을 때 자동 저장 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                messagebox.showerror("오류", f"데이터를 불러오는 중 문제가 발생함.\n{e}")
                self.data = {}
        else:
            self.data = {}

    def save_data(self):
        self.save_current_input()

        temp_file = DATA_FILE + ".tmp"

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

            os.replace(temp_file, DATA_FILE)

        except (OSError, TypeError, ValueError) as e:
            messagebox.showerror(
                "오류",
                f"데이터 저장 실패:\n{e}"
            )

    def create_widgets(self):
        # 전체 레이아웃: 좌우 분할 (PanedWindow)
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 좌측 프레임 (즐겨찾기 + 전체 목록 + 추가/삭제 버튼) ---
        left_frame = tk.Frame(main_pane, width=250)
        main_pane.add(left_frame)

        # 1. 좌측 상단: 즐겨찾기 영역
        fav_frame = tk.LabelFrame(left_frame, text="⭐ 즐겨찾기", font=("맑은 고딕", 10, "bold"))
        fav_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5, ipadx=5, ipady=5)

        self.fav_listbox = tk.Listbox(fav_frame, height=5, font=("맑은 고딕", 10))
        self.fav_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fav_listbox.bind("<<ListboxSelect>>", self.on_fav_select)
        
        # ⬇️ 빈 공간 클릭 시 선택 해제 바인딩 추가
        self.fav_listbox.bind("<Button-1>", self.check_empty_click_fav)

        # 2. 좌측 하단: 전체 이름 목록 영역 (가나다순)
        all_frame = tk.LabelFrame(left_frame, text="👥 전체 (가나다순)", font=("맑은 고딕", 10, "bold"))
        all_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        list_container = tk.Frame(all_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.all_listbox = tk.Listbox(list_container, font=("맑은 고딕", 10))
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.all_listbox.yview)
        self.all_listbox.config(yscrollcommand=scrollbar.set)

        self.all_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.all_listbox.bind("<<ListboxSelect>>", self.on_all_select)
        
        # ⬇️ 빈 공간 클릭 시 선택 해제 바인딩 추가
        self.all_listbox.bind("<Button-1>", self.check_empty_click_all) 

        # 인물 추가, 삭제 및 선택 해제 버튼 영역 (두 줄 레이아웃)
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        # 1행: 추가 / 삭제 버튼
        row1_frame = tk.Frame(btn_frame)
        row1_frame.pack(fill=tk.X, pady=2)

        add_btn = tk.Button(row1_frame, text="추가", command=self.add_person, bg="#e0f7fa", font=("맑은 고딕", 9))
        add_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        del_btn = tk.Button(row1_frame, text="삭제", command=self.delete_person, bg="#ffebee", font=("맑은 고딕", 9))
        del_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=1)

        # 2행: 선택 해제 버튼 (아래쪽)
        row2_frame = tk.Frame(btn_frame)
        row2_frame.pack(fill=tk.X, pady=2)

        deselect_btn = tk.Button(row2_frame, text="선택 해제", command=self.clear_selection, bg="#f5f5f5", font=("맑은 고딕", 9))
        deselect_btn.pack(fill=tk.X, expand=True, padx=1)

        # --- 우측 프레임 (선택된 사람의 어록 편집 영역) ---
        right_frame = tk.Frame(main_pane)
        main_pane.add(right_frame)

        # 우측 상단 정보 및 모드 선택 콤보박스, 즐겨찾기 버튼
        top_bar = tk.Frame(right_frame)
        top_bar.pack(fill=tk.X, padx=5, pady=5)

        self.lbl_current_name = tk.Label(top_bar, text="선택해라.", font=("맑은 고딕", 14, "bold"))
        self.lbl_current_name.pack(side=tk.LEFT, padx=5)

        # ⬇️ 모드 선택 콤보박스 추가 (어록 / 정보)
        self.mode_combobox = ttk.Combobox(top_bar, values=["어록", "정보"], state="readonly", width=10, font=("맑은 고딕", 10))
        self.mode_combobox.set("어록")
        self.mode_combobox.pack(side=tk.LEFT, padx=10)
        self.mode_combobox.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.fav_btn = tk.Button(top_bar, text="⭐ 즐겨찾기 등록", command=self.toggle_favorite, state=tk.DISABLED, font=("맑은 고딕", 9))
        self.fav_btn.pack(side=tk.RIGHT, padx=5)

        self.theme_btn = tk.Button(
            top_bar,
            text="🌙 다크 모드",
            command=self.toggle_theme,
            font=("맑은 고딕", 9)
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=5)

        # 텍스트 박스 상단 라벨도 모드에 따라 바뀌도록 텍스트 프레임 구성
        quote_frame = tk.LabelFrame(right_frame, text="기록 상자", font=("맑은 고딕", 10, "bold"))
        quote_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.quote_text = scrolledtext.Text(quote_frame, wrap=tk.WORD, font=("맑은 고딕", 11), state=tk.DISABLED)
        self.quote_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 초기 목록 로드
        self.refresh_lists()

    def refresh_lists(self, select_name=None):
        # 데이터 정렬 (가나다순)
        sorted_names = sorted(self.data.keys())

        # 전체 목록 갱신
        self.all_listbox.delete(0, tk.END)
        for name in sorted_names:
            self.all_listbox.insert(tk.END, name)

        # 즐겨찾기 목록 갱신
        self.fav_listbox.delete(0, tk.END)
        for name in sorted_names:
            if self.data[name].get("favorite", False):
                self.fav_listbox.insert(tk.END, name)

        # 특정 이름 재선택 유지
        if select_name and select_name in sorted_names:
            idx = sorted_names.index(select_name)
            self.all_listbox.selection_set(idx)
            self.current_person = select_name
            self.load_person_quotes(select_name)

    def get_text_items(self):
        content = self.quote_text.get("1.0", tk.END).strip()
        return [
            line.strip()
            for line in content.splitlines()
            if line.strip()
        ]

    def save_current_input(self):
        if self.current_person and self.current_person in self.data:
            items = self.get_text_items()
            
            # 👈 "어록"이면 quotes, "정보"면 info 키 사용
            key = "quotes" if self.mode_combobox.get() == "어록" else "info"
            self.data[self.current_person][key] = items

    def load_person_quotes(self, name):
        self.current_person = name
        self.lbl_current_name.config(text=f"📖 {name}")
        self.fav_btn.config(state=tk.NORMAL)
        
        is_fav = self.data[name].get("favorite", False)
        self.fav_btn.config(text="⭐ 즐겨찾기 해제" if is_fav else "⭐ 즐겨찾기 등록")

        # 텍스트 박스 활성화 및 현재 모드에 맞는 데이터 로드
        self.quote_text.config(state=tk.NORMAL)
        self.quote_text.delete("1.0", tk.END)
        
        key = "quotes" if self.mode_combobox.get() == "어록" else "info"
        items = self.data[name].get(key, [])
        self.quote_text.insert(tk.END, "\n".join(items))
        
        # 모드가 실제로 바뀔 때만 처리
    def on_mode_change(self, event):
        new_mode = self.mode_combobox.get()
        
        if self.current_mode != new_mode:
            if self.current_person and self.current_person in self.data:
                # 1. 바뀌기 전 모드의 키에 현재 텍스트 저장
                content = self.quote_text.get("1.0", tk.END).strip()
                items = [line.strip() for line in content.split("\n") if line.strip()]
                old_key = "quotes" if self.current_mode == "어록" else "info"
                self.data[self.current_person][old_key] = items

            # 2. 현재 모드 갱신
            self.current_mode = new_mode

            # 3. 새로운 모드의 데이터를 텍스트박스에 로드
            if self.current_person:
                self.quote_text.config(state=tk.NORMAL)
                self.quote_text.delete("1.0", tk.END)
                
                new_key = "quotes" if self.current_mode == "어록" else "info"
                new_items = self.data[self.current_person].get(new_key, [])
                self.quote_text.insert(tk.END, "\n".join(new_items))

    def on_all_select(self, event):
        selection = self.all_listbox.curselection()
        if not selection:
            return
        
        # 이전 편집 내용 저장
        self.save_current_input()

        name = self.all_listbox.get(selection[0])
        # 즐겨찾기 리스트 선택 해제 (동기화)
        self.fav_listbox.selection_clear(0, tk.END)
        
        self.load_person_quotes(name)

    def on_fav_select(self, event):
        selection = self.fav_listbox.curselection()
        if not selection:
            return

        self.save_current_input()

        name = self.fav_listbox.get(selection[0])
        # 전체 리스트에서 해당 이름 선택 상태로 만들기
        sorted_names = sorted(self.data.keys())
        if name in sorted_names:
            idx = sorted_names.index(name)
            self.all_listbox.selection_clear(0, tk.END)
            self.all_listbox.selection_set(idx)
            self.all_listbox.see(idx)

        self.load_person_quotes(name)

    def toggle_favorite(self):
        if not self.current_person:
            return

        self.save_current_input()

        current_status = self.data[self.current_person].get("favorite", False)
        new_status = not current_status
        self.data[self.current_person]["favorite"] = new_status

        self.fav_btn.config(
            text="⭐ 즐겨찾기 해제" if new_status
            else "⭐ 즐겨찾기 등록"
        )

        self.refresh_lists(select_name=self.current_person)

    def add_person(self):
        # 간단한 입력 창 생성 (Toplevel)
        add_win = tk.Toplevel(self.root)
        add_win.title("추가")
        add_win.geometry("300x130")
        add_win.resizable(False, False)
        add_win.grab_set() # 모달 창 설정

        tk.Label(add_win, text="추가할 이름을 입력해라:", font=("맑은 고딕", 10)).pack(pady=10)
        
        name_entry = tk.Entry(add_win, font=("맑은 고딕", 11), width=25)
        name_entry.pack(pady=5)
        name_entry.focus()

        def confirm():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("경고", "이름을 입력해라.", parent=add_win)
                return
            if name in self.data:
                messagebox.showwarning("경고", "이미 존재하는 이름이다.", parent=add_win)
                return

            self.save_current_input()
            self.data[name] = {
                "quotes": [],
                "info": [],
                "favorite": False
            }
            add_win.destroy()
            self.refresh_lists(select_name=name)

        # 엔터키 입력 시 확인
        name_entry.bind("<Return>", lambda e: confirm())

        tk.Button(add_win, text="확인", command=confirm, bg="#e0f7fa", width=10, font=("맑은 고딕", 9)).pack(pady=5)

        # 다크모드 적용
        self.apply_widget_theme(add_win)

    def delete_person(self):
        if not self.current_person:
            messagebox.showwarning("경고", "삭제할 항목을 선택해라.")
            return

        if messagebox.askyesno("확인", f"'{self.current_person}'과 관련된 모든 데이터를 삭제할래?"):
            del self.data[self.current_person]
            self.current_person = None
            
            # 우측 화면 초기화
            self.lbl_current_name.config(text="선택해라.")
            self.fav_btn.config(state=tk.DISABLED, text="⭐ 즐겨찾기 등록")
            self.quote_text.config(state=tk.NORMAL)
            self.quote_text.delete("1.0", tk.END)
            self.quote_text.config(state=tk.DISABLED)

            self.refresh_lists()
            self.save_data()

    def clear_selection(self):
        # 현재 편집 중인 내용 저장 후 선택 초기화
        self.save_current_input()
        self.current_person = None

        # 리스트박스 선택 상태 해제
        self.all_listbox.selection_clear(0, tk.END)
        self.fav_listbox.selection_clear(0, tk.END)

        # 우측 화면 초기화 (입력창 비활성화 및 안내 문구 표시)
        self.lbl_current_name.config(text="선택해라.")
        self.fav_btn.config(state=tk.DISABLED, text="⭐ 즐겨찾기 등록")
        self.quote_text.config(state=tk.NORMAL)
        self.quote_text.delete("1.0", tk.END)
        self.quote_text.config(state=tk.DISABLED)

    def check_empty_click_all(self, event):
        # 클릭한 위치(y좌표)에 해당하는 아이템 index 확인
        index = self.all_listbox.nearest(event.y)
        bbox = self.all_listbox.bbox(index)
        # 리스트가 비어있거나, 실제 아이템 영역이 아닌 아래쪽 빈 공간을 클릭한 경우
        if bbox is None or event.y > bbox[1] + bbox[3]:
            self.clear_selection()

    def check_empty_click_fav(self, event):
        index = self.fav_listbox.nearest(event.y)
        bbox = self.fav_listbox.bbox(index)

        if bbox is None or event.y > bbox[1] + bbox[3]:
            self.clear_selection()

    def start_autosave(self):
        """자동 저장 시작"""
        if self.autosave_job is not None:
            self.root.after_cancel(self.autosave_job)

        self.autosave_job = self.root.after(
            AUTOSAVE_INTERVAL,
            self.autosave
        )

    def autosave(self):
        """현재 데이터 자동 저장"""
        try:
            self.save_data()
        finally:
            # 다음 자동 저장 예약
            self.autosave_job = self.root.after(
                AUTOSAVE_INTERVAL,
                self.autosave
            )

    def load_theme(self):
        """마지막 테마 불러오기"""
        try:
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                theme = json.load(f)

            return theme.get("dark_mode", False)

        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return False

    def save_theme(self):
        """현재 테마 저장"""
        try:
            with open(THEME_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"dark_mode": self.dark_mode},
                    f,
                    indent=4
                )

        except OSError as e:
            messagebox.showerror("오류", f"테마 저장 실패:\n{e}")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

        self.apply_theme()
        self.save_theme()

    def apply_theme(self):
        if self.dark_mode:
            colors = {
                "bg": "#1e1e1e",
                "fg": "#ffffff",
                "frame": "#252526",
                "text_bg": "#2d2d30",
                "entry_bg": "#333333",
                "select_bg": "#094771",
                "button_bg": "#3c3c3c",
                "border": "#555555"
            }
        else:
            colors = {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "frame": "#f0f0f0",
                "text_bg": "#ffffff",
                "entry_bg": "#ffffff",
                "select_bg": "#cce8ff",
                "button_bg": "#e0e0e0",
                "border": "#cccccc"
            }

        self.colors = colors

        self.apply_widget_theme(self.root)

        # ttk 위젯 스타일
        style = ttk.Style()

        # Windows 기본 테마 대신 색상 변경이 가능한 테마 사용
        style.theme_use("clam")

        # 콤보박스 기본 스타일
        style.configure(
            "TCombobox",
            fieldbackground=colors["entry_bg"],
            background=colors["button_bg"],
            foreground=colors["fg"],
            arrowcolor=colors["fg"],
            selectbackground=colors["select_bg"],
            selectforeground=colors["fg"]
        )

        # 콤보박스 상태별 글자색 및 배경색 설정
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", colors["entry_bg"]),
                ("disabled", colors["entry_bg"])
            ],
            foreground=[
                ("readonly", colors["fg"]),
                ("disabled", colors["fg"]),
                ("!disabled", colors["fg"])
            ],
            selectbackground=[
                ("readonly", colors["select_bg"])
            ],
            selectforeground=[
                ("readonly", colors["fg"])
            ],
            background=[
                ("active", colors["select_bg"])
            ]
        )

        # 드롭다운 목록 글자색과 배경색 설정
        self.root.option_add(
            "*TCombobox*Listbox*Background",
            colors["entry_bg"]
        )
        self.root.option_add(
            "*TCombobox*Listbox*Foreground",
            colors["fg"]
        )
        self.root.option_add(
            "*TCombobox*Listbox*selectBackground",
            colors["select_bg"]
        )
        self.root.option_add(
            "*TCombobox*Listbox*selectForeground",
            colors["fg"]
        )

        self.theme_btn.config(
            text="☀️ 라이트 모드" if self.dark_mode
            else "🌙 다크 모드"
        )

    def apply_widget_theme(self, parent):
        c = self.colors

        for widget in parent.winfo_children():
            widget_type = widget.winfo_class()

            try:
                if widget_type in ("Frame", "PanedWindow"):
                    widget.configure(
                        bg=c["bg"],
                        highlightbackground=c["border"]
                    )

                elif widget_type == "LabelFrame":
                    widget.configure(
                        bg=c["frame"],
                        fg=c["fg"]
                    )

                elif widget_type == "Label":
                    widget.configure(
                        bg=c["frame"],
                        fg=c["fg"]
                    )

                elif widget_type == "Button":
                    widget.configure(
                        bg=c["button_bg"],
                        fg=c["fg"],
                        activebackground=c["select_bg"],
                        activeforeground=c["fg"]
                    )

                elif widget_type == "Listbox":
                    widget.configure(
                        bg=c["text_bg"],
                        fg=c["fg"],
                        selectbackground=c["select_bg"],
                        selectforeground=c["fg"],
                        highlightbackground=c["border"]
                    )

                elif widget_type == "Text":
                    widget.configure(
                        bg=c["text_bg"],
                        fg=c["fg"],
                        insertbackground=c["fg"],
                        selectbackground=c["select_bg"]
                    )

                elif widget_type == "Entry":
                    widget.configure(
                        bg=c["entry_bg"],
                        fg=c["fg"],
                        insertbackground=c["fg"]
                    )

                elif widget_type == "Scrollbar":
                    widget.configure(
                        bg=c["button_bg"],
                        troughcolor=c["bg"],
                        activebackground=c["select_bg"]
                    )

            except tk.TclError:
                pass

            # 하위 위젯에도 테마 적용
            self.apply_widget_theme(widget)

    def on_closing(self):
        # 예약된 자동 저장 취소
        if self.autosave_job is not None:
            self.root.after_cancel(self.autosave_job)
            self.autosave_job = None

        # 데이터와 테마 저장
        self.save_data()
        self.save_theme()

        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuoteApp(root)
    root.mainloop()
