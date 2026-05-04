# JamoCombine (한글 자모 결합기)

macOS에서 만든 뒤 Windows로 옮긴 **파일·폴더 이름**이 한글 자모가 풀어지거나 깨져 보일 때, 파일명을 Windows에서 쓰기 좋은 **NFC(결합형) 정규화**로 일괄 바꿔 주는 Windows용 도구입니다.

---

## 실행 파일(EXE) 다운로드

Python 없이 **Windows 64비트**에서 바로 쓰려면 GitHub **Releases**에서 `JamoCombine.exe`를 받으면 됩니다.

| 설명 | 링크 |
|------|------|
| **릴리스·Assets (항상 열림)** | [github.com/shoutjoy/jamo_combine/releases](https://github.com/shoutjoy/jamo_combine/releases) |
| **최신 EXE 고정 주소** | […/latest/download/JamoCombine.exe](https://github.com/shoutjoy/jamo_combine/releases/latest/download/JamoCombine.exe) |

마지막 주소는 GitHub 규칙상 **게시된 최신 릴리스**에 이름이 정확히 `JamoCombine.exe`인 파일이 붙어 있을 때만 열립니다. 릴리스가 없거나 파일 이름이 다르면 **404**가 납니다.

### 직접 링크를 살리는 방법 (저장소 관리자)

1. **태그로 자동 빌드·업로드 (권장)**  
   로컬에서 `build_exe.cmd`로 확인한 뒤, 저장소에 푸시합니다.
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   GitHub Actions(`.github/workflows/build-release-exe.yml`)가 Windows에서 EXE를 만들고, 같은 이름의 릴리스에 **`JamoCombine.exe`** 를 올립니다. 완료 후 위 “최신 EXE 고정 주소”가 동작합니다.

2. **수동 업로드**  
   GitHub 웹에서만 릴리스를 만들었다면 `build_exe.cmd`로 만든 `dist\JamoCombine.exe`를 Assets에 **파일 이름 그대로** `JamoCombine.exe`로 올리면 됩니다. (이름이 `JamoCombine_v1.exe`처럼 바뀌면 고정 다운로드 URL은 404가 납니다.)

EXE 사용 시: 원하는 폴더에 두고 실행하거나, 앱에서 **「우클릭 메뉴에 등록」**, **「시작 메뉴 바로가기」** 버튼으로 연동하면 됩니다. (소스 설치용 `install.cmd`는 필수가 아닙니다.)

---

## 제작자

**박중희**  
연세대학교 심리학과 겸임교수  
이메일: [shoutjoy1@yonsei.ac.kr](mailto:shoutjoy1@yonsei.ac.kr)

---

## 왜 이런 문제가 생기나요?

macOS는 파일 이름에 쓰는 유니코드 정규화 방식이 **NFD: 자모가 나뉜 형태**인 경우가 많고, Windows는 **NFC: 한 글자로 붙은 형태**에 가깝게 다루는 경우가 많습니다.  
같은 “보이는 글자”라도 **내부 코드 순서가 다르면** Windows 탐색기·다른 프로그램에서 **한글이 자모 단위로 쪼개져 보이거나**, 검색·정렬·일부 앱에서 **이상하게 보이는** 현상이 날 수 있습니다.

이 앱은 **이름이 달라지는 항목만** 골라, 가능한 범위에서 **NFC 형태의 같은 이름**으로 다시 저장(이름 바꾸기)합니다. (이미 NFC로만 된 이름은 그대로 둡니다.)

---

## 필요한 환경

- **Windows 10 / 11** (탐색기 우클릭 연동 기준), **64비트** (배포 EXE 기준)
- **실행 파일(EXE)만 쓸 때:** Python 불필요.
- **소스·`install.cmd`로 설치할 때:** **Python 3** 이 설치되어 있고 `python` 또는 `py` 로 실행 가능해야 합니다.  
  - [https://www.python.org/downloads/](https://www.python.org/downloads/)

---

## 개발자용: EXE 빌드 (PyInstaller)

저장소를 클론한 뒤 Windows에서:

1. `pip install -r requirements-build.txt`
2. **`build_exe.cmd`** 실행 (또는 `python -m PyInstaller --noconfirm JamoCombine.spec`)
3. 결과물: **`dist\JamoCombine.exe`**

빌드 설정은 루트의 **`JamoCombine.spec`** 에 있습니다. (`--onefile`, 콘솔 없음 GUI 전용)

---

## 설치 방법 (소스 + 스크립트)

1. 이 저장소(폴더)를 그대로 둡니다.
2. **`install.cmd`** 를 더블클릭합니다.  
   - `install.ps1`이 실행되며, 기본적으로 다음이 수행됩니다.  
     - 프로그램 파일을 `%LOCALAPPDATA%\Programs\JamoCombine` 으로 복사  
     - 탐색기 **우클릭 메뉴** 등록(아래 “탐색기에서 쓰는 법” 참고)  
     - 시작 메뉴에 바로가기 2개 생성(아래 “시작 메뉴” 참고)
3. Python을 찾지 못하면 스크립트가 안내 메시지를 띄우고 중단됩니다. PATH에 Python을 넣은 뒤 다시 시도하세요.

**제거**는 **`uninstall.cmd`** 를 실행합니다. (우클릭 메뉴·시작 메뉴 바로가기·설치 폴더를 정리합니다.)

---

## 실제 사용 방법

### 1) 탐색기에서 바로 쓰기 (권장)

설치가 끝나면 Windows 탐색기에서 아래 둘 다 사용할 수 있습니다.

| 동작 | 설명 |
|------|------|
| **폴더를 우클릭** | 변환할 **그 폴더**를 가리킨 채로 메뉴를 띄웁니다. |
| **폴더 안 빈 곳을 우클릭** | **지금 열어 둔 그 폴더**를 대상으로 메뉴를 띄웁니다. |

공통으로 **「한글 자모 결합 (NFC 변환)」** 을 누르면 프로그램이 뜨고, 해당 폴더 경로가 자동으로 채워집니다.

- 처음에 메뉴가 없다면, 앱을 한 번 실행한 뒤 **「우클릭 메뉴에 등록」** 을 누르거나, `install.cmd` 를 다시 실행해 보세요.

### 2) 앱을 직접 실행할 때

- **EXE 사용자:** `JamoCombine.exe` 더블클릭.
- **소스 사용자:** **`JmoCombinde.bat`** 을 더블클릭하거나, `install.cmd` 설치 후 시작 메뉴의 바로가기를 사용합니다.
- **「폴더 선택」** 으로 대상 폴더를 고릅니다.
- **「하위 폴더 포함」** : 켜 두면 그 아래 모든 하위 폴더·파일 이름도 함께 검사합니다.
- **「변환 시작」** 을 누르면 로그에 바뀐 항목이 표시됩니다.

### 3) 변환 후 창을 닫을지

- **「변환 완료 후 프로그램 종료」** 를 켜 두면, 오류 없이 끝났을 때 완료 창을 닫은 뒤 **프로그램이 자동으로 종료**됩니다. (오류가 나면 창을 유지합니다.)  
- 이 옵션은 `%LOCALAPPDATA%\JamoCombine\settings.json` 에 저장됩니다.

### 4) 시작 메뉴 바로가기 (원하는 방식으로)

앱 안 **「시작 메뉴 바로가기」** 영역에서:

- **「등록 · 변환 후에도 창 유지」** → 항상 변환 후에도 창을 남깁니다.  
- **「등록 · 변환 완료 후 종료」** → 항상 변환 성공 시 곧바로 끝낼 모드로 실행합니다.

`install.cmd` 로 설치할 때도 같은 이름의 바로가기 2개가 만들어집니다.

---

## 주의 사항

- **이미 같은 NFC 이름의 파일/폴더가 있으면** 덮어쓰지 않고 건너뜁니다(로그에 표시).
- **시스템 폴더·권한이 강한 위치**는 이름 변경이 실패할 수 있습니다. 가능하면 **일반 사용자 폴더**에서 시험한 뒤 사용하세요.
- 이 도구는 **파일 이름**만 바꿉니다. 파일 **내용** 인코딩(EUC-KR, UTF-8 등) 문제와는 별개입니다.

---

## 라이선스·저작권

저장소 정책에 맞게 별도 라이선스 파일이 있으면 그에 따릅니다. 없을 경우 제작자에게 문의하시면 됩니다.
