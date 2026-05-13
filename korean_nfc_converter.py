import ctypes
import json
import os
import shutil
import subprocess
import sys
import unicodedata
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import winreg as reg


def parse_launch_args(argv):
    """--close-after-run / --keep-open 과 폴더 경로(위치 인자)를 분리한다.
    둘 다 없으면 mode는 None(설정 파일 기준). 나중에 나온 플래그가 우선한다."""
    mode = None  # None | "close" | "keep"
    positional = []
    for a in argv[1:]:
        if a == "--close-after-run":
            mode = "close"
        elif a == "--keep-open":
            mode = "keep"
        elif a.startswith("-"):
            continue
        else:
            positional.append(a)
    return mode, positional


def settings_path():
    d = os.path.join(os.environ.get("LOCALAPPDATA", ""), "JamoCombine")
    return os.path.join(d, "settings.json")


def load_close_after_pref():
    try:
        with open(settings_path(), encoding="utf-8") as f:
            return bool(json.load(f).get("close_after_run", False))
    except (OSError, json.JSONDecodeError, TypeError):
        return False


def is_frozen():
    """PyInstaller 등으로 패키징된 단일 실행 파일인지 여부."""
    return bool(getattr(sys, "frozen", False))


def app_install_dir():
    """실행 파일(.exe) 또는 스크립트가 있는 폴더."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def explorer_menu_command(path_placeholder):
    """탐색기 우클릭 레지스트리용 실행 문자열. path_placeholder는 %1 또는 %V."""
    if is_frozen():
        return f'"{os.path.abspath(sys.executable)}" "{path_placeholder}"'
    script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script}" "{path_placeholder}"'


def notify_shell_context_menus_changed():
    """레지스트리 shell 항목 변경 후 탐색기 등이 캐시를 갱신하도록 알린다."""
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        SHCNF_FLUSH = 0x1000
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED, SHCNF_IDLIST | SHCNF_FLUSH, None, None
        )
    except OSError:
        pass


# EXE 배포 시 고정 설치 경로 (사용자 요청: 시스템 드라이브\Program\Jamo)
_sd = os.environ.get("SystemDrive", "C:")
_sd_root = _sd if _sd.endswith(("/", "\\")) else _sd + os.sep
PROGRAM_JAMO_INSTALL_DIR = os.path.join(_sd_root, "Program", "Jamo")
PROGRAM_JAMO_EXE_NAME = "JamoCombine.exe"


def context_menu_success_hint():
    """Windows 11+ 기본 우클릭 메뉴에 레거시 항목이 숨겨질 수 있음을 안내한다."""
    try:
        v = sys.getwindowsversion()
        if v.major >= 10 and v.build >= 22000:
            return (
                "\n\nWindows 11에서는 기본 우클릭 메뉴 대신\n"
                "「추가 옵션 표시」또는 Shift+우클릭(전체 메뉴)에서 항목을 확인하세요."
            )
    except (TypeError, ValueError, AttributeError):
        pass
    return ""


def save_close_after_pref(value):
    d = os.path.dirname(settings_path())
    try:
        os.makedirs(d, exist_ok=True)
        data = {}
        if os.path.isfile(settings_path()):
            try:
                with open(settings_path(), encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, TypeError):
                pass
        data["close_after_run"] = bool(value)
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    except OSError:
        pass


def wsh_create_shortcut(link_path, target_path, arguments, working_dir, description):
    """WScript.Shell 로 .lnk 를 만든다."""
    link_dir = os.path.dirname(link_path)
    if link_dir:
        os.makedirs(link_dir, exist_ok=True)
    ps = (
        "$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LINK); "
        "$sc.TargetPath = $env:PY; "
        "$sc.Arguments = $env:ARGS; "
        "$sc.WorkingDirectory = $env:CWD; "
        "$sc.Description = $env:DESC; "
        "$sc.Save()"
    )
    env = os.environ.copy()
    env["LINK"] = link_path
    env["PY"] = target_path
    env["ARGS"] = arguments
    env["CWD"] = working_dir
    env["DESC"] = description
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps,
        ],
        check=True,
        env=env,
        creationflags=(
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0
        ),
    )


def taskbar_pinned_shortcut_path():
    """사용자 작업 표시줄 고정 폴더에 둘 JamoCombine 바로가기 경로."""
    return os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft",
        "Internet Explorer",
        "Quick Launch",
        "User Pinned",
        "TaskBar",
        "JamoCombine.lnk",
    )


class NFCNormalizerApp:
    """
    macOS의 NFD 방식 파일명을 NFC 방식으로 일괄 변환하며, 
    윈도우 탐색기 우클릭 메뉴 등록 기능을 포함한 GUI 애플리케이션이다.
    """
    def __init__(self, root, *, launch_mode=None, positional_paths=None):
        self.root = root
        self.root.title("한글 자모 결합기 (NFD → NFC)")
        self.root.geometry("640x800")
        self.root.minsize(520, 560)

        # UI 스타일 설정
        style = ttk.Style()
        style.configure("TButton", padding=5)

        if launch_mode == "close":
            close_initial = True
        elif launch_mode == "keep":
            close_initial = False
        else:
            close_initial = load_close_after_pref()
        self.close_after_var = tk.BooleanVar(value=close_initial)

        self.setup_ui()

        # 명령행·탐색기 등으로 넘어온 폴더 경로
        for p in positional_paths or []:
            if os.path.isdir(p):
                self.path_var.set(p)
                self.log(f"전달된 경로: {p}")
                break

    def _bind_scroll_canvas(self, canvas):
        def _wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

    def _make_scroll_body(self, parent):
        """세로 스크롤이 있는 (wrap, canvas, body) 튜플을 만든다."""
        wrap = tk.Frame(parent)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def on_body_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            w = max(event.width, 1)
            canvas.itemconfigure(inner_id, width=w)

        body.bind("<Configure>", on_body_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        self._bind_scroll_canvas(canvas)
        return wrap, canvas, body

    def setup_ui(self):
        instruction = (
            "이 프로그램은 맥(macOS)에서 만들어져 자모가 분리된 파일명을\n"
            "윈도우 표준인 결합된 한글 형태로 복원합니다."
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        tab_convert = tk.Frame(self.notebook)
        tab_convert.grid_columnconfigure(0, weight=1)
        tab_convert.grid_rowconfigure(3, weight=1)
        self.notebook.add(tab_convert, text="변환")

        # 상단(안내·폴더)은 내용 높이만큼만 — 스크롤 캔버스에 weight 를 주면 빈 여백이 커진다.
        body_main = tk.Frame(tab_convert)
        body_main.grid(row=0, column=0, sticky="new")

        tk.Label(body_main, text=instruction, pady=10, justify="center").pack()

        path_frame = tk.LabelFrame(body_main, text="대상 폴더 경로", padx=10, pady=10)
        path_frame.pack(fill="x", padx=20, pady=5)

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_browse = ttk.Button(path_frame, text="폴더 선택", command=self.browse_folder)
        btn_browse.pack(side="right")

        self.recursive_var = tk.BooleanVar(value=True)
        opts = tk.Frame(tab_convert)
        opts.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 4))
        tk.Checkbutton(opts, text="하위 폴더 포함", variable=self.recursive_var).pack(anchor="w")
        tk.Checkbutton(
            opts,
            text="변환 완료 후 프로그램 종료",
            variable=self.close_after_var,
            command=lambda: save_close_after_pref(self.close_after_var.get()),
        ).pack(anchor="w")

        tk.Label(tab_convert, text="처리 기록:").grid(
            row=2, column=0, sticky="w", padx=20, pady=(6, 0)
        )
        self.log_text = tk.Text(tab_convert, height=6, state="disabled", bg="#f0f0f0")
        self.log_text.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)

        self.btn_run = ttk.Button(tab_convert, text="변환 시작", command=self.run_normalization)
        self.btn_run.grid(row=4, column=0, pady=(0, 10))

        # —— 설정 탭: 앱 설치, 탐색기 통합, 시작 메뉴 바로가기 ——
        tab_settings = tk.Frame(self.notebook)
        tab_settings.grid_columnconfigure(0, weight=1)
        tab_settings.grid_rowconfigure(0, weight=1)
        self.notebook.add(tab_settings, text="설정")

        wrap_set, _canvas_set, body_set = self._make_scroll_body(tab_settings)
        wrap_set.grid(row=0, column=0, sticky="nsew")

        install_shell = tk.Frame(body_set)
        install_shell.pack(fill="x", padx=20, pady=5)
        self._install_expanded = False
        self.btn_install_fold = ttk.Button(
            install_shell,
            text="앱 설치 ▼ 펼치기 (최초 1회 권장)",
            command=self._toggle_install_fold,
        )
        self.btn_install_fold.pack(anchor="w")

        self._install_detail = tk.LabelFrame(
            install_shell,
            text="앱 설치",
            padx=10,
            pady=10,
        )
        ttk.Button(
            self._install_detail,
            text="설치 (Install) — C:\\Program\\Jamo 에 복사",
            command=self.install_to_program_jamo,
        ).pack(fill="x", padx=5, pady=2)
        self.install_add_start_menu_var = tk.BooleanVar(value=True)
        self.install_pin_taskbar_var = tk.BooleanVar(value=False)
        cb_row = tk.Frame(self._install_detail)
        cb_row.pack(fill="x", padx=5, pady=(2, 0))
        tk.Checkbutton(
            cb_row,
            text="설치 후 시작 메뉴에 바로가기 만들기",
            variable=self.install_add_start_menu_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            cb_row,
            text="작업 표시줄 고정용 바로가기 만들기 (자동 고정은 Windows에서 제한될 수 있음)",
            variable=self.install_pin_taskbar_var,
        ).pack(anchor="w")
        tk.Label(
            self._install_detail,
            text=(
                "JamoCombine.exe 로 실행 중일 때 설치 버튼으로 고정 폴더에 복사합니다. "
                "※ 같은 폴더에서 이미 실행 중이면 복사 없이, 체크한 바로가기만 만들 수 있습니다.\n"
                "바로가기의 실행 옵션(창 유지/종료)은 「변환」탭의 「변환 완료 후 프로그램 종료」와 동일합니다.\n"
                "Python 스크립트로만 실행 중이면 설치 시 안내 메시지가 표시됩니다."
            ),
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=5, pady=(4, 0))

        explorer_frame = tk.LabelFrame(body_set, text="윈도우 탐색기 통합", padx=10, pady=10)
        explorer_frame.pack(fill="x", padx=20, pady=5)

        btn_register = ttk.Button(
            explorer_frame,
            text="우클릭 메뉴에 등록",
            command=self.register_context_menu,
        )
        btn_register.pack(side="left", expand=True, padx=5)

        btn_unregister = ttk.Button(
            explorer_frame,
            text="우클릭 메뉴에서 제거",
            command=self.unregister_context_menu,
        )
        btn_unregister.pack(side="left", expand=True, padx=5)

        tk.Label(
            body_set,
            text=(
                "※ 탐색기에서「한글 자모 결합 (NFC 변환)」이 안 보이면: "
                "Windows 11은 우클릭 후 「추가 옵션 표시」 또는 Shift+우클릭으로 전체(클래식) 메뉴를 여세요. "
                "등록 직후에는 탐색기를 모두 닫았다가 다시 열거나, 안 되면 PC 재시작 후 확인하세요."
            ),
            justify="left",
            wraplength=520,
            fg="#333",
        ).pack(anchor="w", padx=20, pady=(0, 6))

        start_frame = tk.LabelFrame(body_set, text="시작 메뉴 바로가기 (수동)", padx=10, pady=10)
        start_frame.pack(fill="x", padx=20, pady=(5, 16))
        ttk.Button(
            start_frame,
            text="등록 · 변환 후에도 창 유지",
            command=lambda: self.register_start_menu_shortcut(close_after=False),
        ).pack(side="left", expand=True, padx=5)
        ttk.Button(
            start_frame,
            text="등록 · 변환 완료 후 종료",
            command=lambda: self.register_start_menu_shortcut(close_after=True),
        ).pack(side="left", expand=True, padx=5)

    def _toggle_install_fold(self):
        """앱 설치 블록 펼치기 / 접기."""
        self._install_expanded = not self._install_expanded
        if self._install_expanded:
            self._install_detail.pack(fill="x", pady=(6, 0))
            self.btn_install_fold.configure(text="앱 설치 ▲ 접기")
        else:
            self._install_detail.pack_forget()
            self.btn_install_fold.configure(
                text="앱 설치 ▼ 펼치기 (최초 1회 권장)"
            )

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)

    def install_to_program_jamo(self):
        """EXE만: Program\\Jamo 로 복사하고, 선택 시 시작 메뉴·작업 표시줄용 .lnk 를 만든다."""
        if not is_frozen():
            messagebox.showinfo(
                "알림",
                "이 설치(복사) 기능은 JamoCombine.exe 로 실행했을 때 사용할 수 있습니다.",
            )
            return

        dest_dir = os.path.normpath(PROGRAM_JAMO_INSTALL_DIR)
        dest_exe = os.path.join(dest_dir, PROGRAM_JAMO_EXE_NAME)
        norm_src = os.path.normcase(os.path.normpath(os.path.abspath(sys.executable)))
        norm_dest = os.path.normcase(os.path.normpath(dest_exe))

        want_sm = self.install_add_start_menu_var.get()
        want_tb = self.install_pin_taskbar_var.get()

        if norm_src == norm_dest:
            if not want_sm and not want_tb:
                messagebox.showinfo(
                    "알림",
                    f"이미 설치 경로에서 실행 중입니다.\n{dest_exe}\n"
                    "시작 메뉴·작업 표시줄 바로가기를 만들려면 체크한 뒤 다시 누르세요.",
                )
                self.log(f"설치: 이미 {dest_exe} (바로가기 옵션 없음)")
                return
        else:
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror(
                    "오류",
                    f"폴더를 만들 수 없습니다.\n{dest_dir}\n\n{e}\n\n"
                    "시스템 드라이브 루트에 쓰기 권한이 없을 수 있습니다. "
                    "앱을「관리자 권한으로 실행」한 뒤 다시 시도해 보세요.",
                )
                return
            try:
                shutil.copy2(os.path.abspath(sys.executable), dest_exe)
            except OSError as e:
                messagebox.showerror(
                    "오류",
                    f"파일을 복사할 수 없습니다.\n→ {dest_exe}\n\n{e}\n\n"
                    "대상 위치의 JamoCombine.exe 가 실행 중이면 종료한 뒤 다시 시도하세요.",
                )
                return
            self.log(f"복사 완료: {dest_exe}")

        close_after = self.close_after_var.get()
        args = "--close-after-run" if close_after else "--keep-open"
        desc = "한글 자모 결합기 (NFC)" + (
            " · 완료 후 종료" if close_after else " · 창 유지"
        )

        done = []
        warn = []

        if want_sm:
            name = (
                "JamoCombine (변환 후 종료).lnk"
                if close_after
                else "JamoCombine.lnk"
            )
            link_path = os.path.join(self._start_menu_programs_dir(), name)
            try:
                wsh_create_shortcut(link_path, dest_exe, args, dest_dir, desc)
                done.append(f"시작 메뉴: {name}")
                self.log(f"바로가기: {link_path}")
            except (OSError, subprocess.CalledProcessError) as e:
                warn.append(f"시작 메뉴 바로가기: {e}")

        if want_tb:
            tb_link = taskbar_pinned_shortcut_path()
            try:
                wsh_create_shortcut(
                    tb_link,
                    dest_exe,
                    args,
                    dest_dir,
                    desc + " · 작업 표시줄",
                )
                done.append("작업 표시줄 고정 폴더에 바로가기 저장")
                self.log(f"바로가기: {tb_link}")
            except (OSError, subprocess.CalledProcessError) as e:
                warn.append(f"작업 표시줄 바로가기: {e}")

        lines = [f"설치 경로: {dest_exe}", ""]
        if done:
            lines.append("\n".join(done))
        if warn:
            lines.append("")
            lines.append("주의:\n" + "\n".join(warn))
        lines.append("")
        lines.append(
            "우클릭 메뉴는 위 경로의 exe를 실행한 뒤 「우클릭 메뉴에 등록」하는 것을 권장합니다."
        )
        if want_tb:
            lines.append(
                "작업 표시줄에 안 보이면: 시작 메뉴에서 이 앱을 연 뒤 "
                "작업 표시줄 아이콘을 마우스 오른쪽 버튼 → 작업 표시줄에 고정."
            )

        messagebox.showinfo("완료", "\n".join(lines))

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    _REG_CLASSES = r"Software\Classes"
    _MENU_KEY_NAME = r"KOR_NFC_Converter"
    # 폴더 아이콘 우클릭: %1, 폴더 창 안 빈 곳 우클릭: %V (탐색기가 확장)
    _MENU_TARGETS = (
        (r"Directory\shell", "%1"),
        (r"Directory\Background\shell", "%V"),
    )

    def _write_one_context_menu(self, shell_parent_path, path_placeholder):
        hkey = reg.HKEY_CURRENT_USER
        key_path = rf"{self._REG_CLASSES}\{shell_parent_path}\{self._MENU_KEY_NAME}"
        with reg.CreateKey(hkey, key_path) as key:
            reg.SetValue(key, "", reg.REG_SZ, "한글 자모 결합 (NFC 변환)")
        command_path = key_path + r"\command"
        with reg.CreateKey(hkey, command_path) as key:
            reg.SetValue(key, "", reg.REG_SZ, explorer_menu_command(path_placeholder))

    def _start_menu_programs_dir(self):
        return os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        )

    def register_start_menu_shortcut(self, *, close_after):
        """시작 메뉴(사용자 Programs)에 .lnk를 만든다."""
        appdata = os.environ.get("APPDATA", "")
        if not appdata or not os.path.isdir(appdata):
            messagebox.showerror("오류", "시작 메뉴 경로를 찾을 수 없습니다.")
            return
        programs = self._start_menu_programs_dir()
        os.makedirs(programs, exist_ok=True)
        name = (
            "JamoCombine (변환 후 종료).lnk"
            if close_after
            else "JamoCombine.lnk"
        )
        link_path = os.path.join(programs, name)
        py = os.path.abspath(sys.executable)
        inst_dir = app_install_dir()
        if is_frozen():
            args = "--close-after-run" if close_after else "--keep-open"
        else:
            script = os.path.abspath(sys.argv[0])
            args = f'"{script}"'
            if close_after:
                args += " --close-after-run"
            else:
                args += " --keep-open"
        desc = "한글 자모 결합기 (NFC)" + (" · 완료 후 종료" if close_after else " · 창 유지")
        try:
            wsh_create_shortcut(link_path, py, args, inst_dir, desc)
            messagebox.showinfo("성공", f"시작 메뉴에 등록했습니다.\n{name}")
        except (OSError, subprocess.CalledProcessError) as e:
            messagebox.showerror("오류", f"바로가기 만들기 실패: {e}")

    def _delete_one_context_menu(self, shell_parent_path):
        hkey = reg.HKEY_CURRENT_USER
        key_path = rf"{self._REG_CLASSES}\{shell_parent_path}\{self._MENU_KEY_NAME}"
        reg.DeleteKey(hkey, key_path + r"\command")
        reg.DeleteKey(hkey, key_path)

    def register_context_menu(self):
        """윈도우 레지스트리에 우클릭 메뉴를 등록한다 (현재 사용자)."""
        try:
            for shell_parent, token in self._MENU_TARGETS:
                self._write_one_context_menu(shell_parent, token)
            notify_shell_context_menus_changed()
            self.log("우클릭 등록 — 폴더 아이콘: " + explorer_menu_command("%1"))
            self.log("우클릭 등록 — 폴더 안 빈 곳: " + explorer_menu_command("%V"))
            messagebox.showinfo(
                "성공",
                "탐색기에 등록했습니다.\n"
                "· 폴더에서 우클릭\n"
                "· 폴더 안 빈 곳에서 우클릭\n\n"
                "※ 우클릭 메뉴가 정상 동작하려면 PC를 다시 시작해 주세요."
                + context_menu_success_hint(),
            )
        except Exception as e:
            messagebox.showerror("오류", f"메뉴 등록 중 오류 발생: {e}")

    def unregister_context_menu(self):
        """윈도우 레지스트리에서 우클릭 메뉴를 제거한다."""
        missing = True
        err = None
        for shell_parent, _ in self._MENU_TARGETS:
            try:
                self._delete_one_context_menu(shell_parent)
                missing = False
            except FileNotFoundError:
                continue
            except OSError as e:
                err = e
        if err:
            messagebox.showerror("오류", f"메뉴 제거 중 오류 발생: {err}")
        elif missing:
            messagebox.showinfo("알림", "등록된 메뉴가 없습니다.")
        else:
            notify_shell_context_menus_changed()
            messagebox.showinfo("성공", "우클릭 메뉴에서 제거되었습니다.")

    def run_normalization(self):
        target_path = self.path_var.get()
        if not target_path or not os.path.exists(target_path):
            messagebox.showerror("오류", "유효한 폴더 경로를 선택하십시오.")
            return

        self.btn_run.config(state="disabled")
        self.log(f"--- 변환 작업 시작: {target_path} ---")
        
        count = 0
        try:
            if self.recursive_var.get():
                for root_dir, dirs, files in os.walk(target_path, topdown=False):
                    for name in dirs + files:
                        count += self.normalize_item(root_dir, name)
            else:
                for name in os.listdir(target_path):
                    count += self.normalize_item(target_path, name)
            
            self.log(f"--- 작업 완료: 총 {count}개의 파일/폴더 변환됨 ---")
            messagebox.showinfo("완료", f"총 {count}개의 항목이 성공적으로 변환되었습니다.")
            if self.close_after_var.get():
                self.root.destroy()
        except Exception as e:
            self.log(f"에러 발생: {str(e)}")
            messagebox.showerror("에러", f"작업 중 오류가 발생했습니다: {e}")
        finally:
            try:
                self.btn_run.config(state="normal")
            except tk.TclError:
                pass

    def normalize_item(self, root_dir, name):
        normalized_name = unicodedata.normalize('NFC', name)
        
        if name != normalized_name:
            old_path = os.path.join(root_dir, name)
            new_path = os.path.join(root_dir, normalized_name)
            
            if os.path.exists(new_path):
                self.log(f"[건너뜀] 이미 존재함: {normalized_name}")
                return 0
            
            try:
                os.rename(old_path, new_path)
                self.log(f"[변환] {name} -> {normalized_name}")
                return 1
            except Exception as e:
                self.log(f"[실패] {name}: {str(e)}")
                return 0
        return 0

if __name__ == "__main__":
    launch_mode, pos_paths = parse_launch_args(sys.argv)
    root = tk.Tk()
    app = NFCNormalizerApp(root, launch_mode=launch_mode, positional_paths=pos_paths)
    root.mainloop()