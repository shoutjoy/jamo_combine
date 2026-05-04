import json
import os
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


class NFCNormalizerApp:
    """
    macOS의 NFD 방식 파일명을 NFC 방식으로 일괄 변환하며, 
    윈도우 탐색기 우클릭 메뉴 등록 기능을 포함한 GUI 애플리케이션이다.
    """
    def __init__(self, root, *, launch_mode=None, positional_paths=None):
        self.root = root
        self.root.title("한글 자모 결합기 (NFD → NFC)")
        self.root.geometry("600x620")

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

    def setup_ui(self):
        # 상단 설명 레이블
        instruction = (
            "이 프로그램은 맥(macOS)에서 만들어져 자모가 분리된 파일명을\n"
            "윈도우 표준인 결합된 한글 형태로 복원합니다."
        )
        tk.Label(self.root, text=instruction, pady=10, justify="center").pack()

        # 경로 선택 영역
        path_frame = tk.LabelFrame(self.root, text="대상 폴더 경로", padx=10, pady=10)
        path_frame.pack(fill="x", padx=20, pady=5)
        
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_browse = ttk.Button(path_frame, text="폴더 선택", command=self.browse_folder)
        btn_browse.pack(side="right")

        # 익스플로러 메뉴 설정 영역
        explorer_frame = tk.LabelFrame(self.root, text="윈도우 탐색기 통합", padx=10, pady=10)
        explorer_frame.pack(fill="x", padx=20, pady=5)
        
        btn_register = ttk.Button(explorer_frame, text="우클릭 메뉴에 등록", command=self.register_context_menu)
        btn_register.pack(side="left", expand=True, padx=5)
        
        btn_unregister = ttk.Button(explorer_frame, text="우클릭 메뉴에서 제거", command=self.unregister_context_menu)
        btn_unregister.pack(side="left", expand=True, padx=5)

        start_frame = tk.LabelFrame(self.root, text="시작 메뉴 바로가기", padx=10, pady=10)
        start_frame.pack(fill="x", padx=20, pady=5)
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

        # 옵션 설정
        self.recursive_var = tk.BooleanVar(value=True)
        opts = tk.Frame(self.root)
        opts.pack(anchor="w", padx=20)
        tk.Checkbutton(opts, text="하위 폴더 포함", variable=self.recursive_var).pack(anchor="w")
        tk.Checkbutton(
            opts,
            text="변환 완료 후 프로그램 종료",
            variable=self.close_after_var,
            command=lambda: save_close_after_pref(self.close_after_var.get()),
        ).pack(anchor="w")

        # 결과 로그 영역
        tk.Label(self.root, text="처리 기록:").pack(anchor="w", padx=20, pady=(10, 0))
        self.log_text = tk.Text(self.root, height=12, state="disabled", bg="#f0f0f0")
        self.log_text.pack(fill="both", padx=20, pady=5, expand=True)

        # 실행 버튼
        self.btn_run = ttk.Button(self.root, text="변환 시작", command=self.run_normalization)
        self.btn_run.pack(pady=10)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)

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
        env["PY"] = py
        env["ARGS"] = args
        env["CWD"] = inst_dir
        env["DESC"] = desc
        try:
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
            messagebox.showinfo(
                "성공",
                "탐색기에 등록했습니다.\n"
                "· 폴더에서 우클릭\n"
                "· 폴더 안 빈 곳에서 우클릭",
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