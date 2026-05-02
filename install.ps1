#Requires -Version 5.1
# JamoCombine: 사용자 폴더에 설치하고 탐색기 폴더 우클릭 메뉴에 등록합니다 (관리자 불필요).
$ErrorActionPreference = 'Stop'

function Get-PythonExecutable {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { return $pythonCmd.Source }
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return $out.Trim() }
    }
    return $null
}

$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\JamoCombine'
$PythonExe = Get-PythonExecutable

if (-not $PythonExe) {
    Write-Host '[오류] Python을 찾을 수 없습니다. python.org 에서 설치한 뒤 PATH에 등록하거나 py 런처를 설치하세요.' -ForegroundColor Red
    exit 1
}

Write-Host "설치 위치: $InstallDir" -ForegroundColor Cyan
Write-Host "Python: $PythonExe" -ForegroundColor Gray

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item (Join-Path $SourceRoot 'korean_nfc_converter.py') -Destination $InstallDir -Force
Copy-Item (Join-Path $SourceRoot 'JmoCombinde.bat') -Destination $InstallDir -Force

$ScriptPath = Join-Path $InstallDir 'korean_nfc_converter.py'
# 폴더 아이콘 우클릭: %1, 폴더 창 안 빈 곳 우클릭: %V
$CommandOnFolder = "`"$PythonExe`" `"$ScriptPath`" `"%1`""
$CommandInFolder = "`"$PythonExe`" `"$ScriptPath`" `"%V`""

$MenuLabel = '한글 자모 결합 (NFC 변환)'

$Pairs = @(
    @{ Root = 'HKCU:\Software\Classes\Directory\shell\KOR_NFC_Converter'; Command = $CommandOnFolder }
    @{ Root = 'HKCU:\Software\Classes\Directory\Background\shell\KOR_NFC_Converter'; Command = $CommandInFolder }
)

foreach ($p in $Pairs) {
    $MenuRoot = $p.Root
    $MenuCmd = Join-Path $MenuRoot 'command'
    if (-not (Test-Path $MenuRoot)) { New-Item -Path $MenuRoot -Force | Out-Null }
    Set-ItemProperty -Path $MenuRoot -Name '(default)' -Value $MenuLabel -Type String
    if (-not (Test-Path $MenuCmd)) { New-Item -Path $MenuCmd -Force | Out-Null }
    Set-ItemProperty -Path $MenuCmd -Name '(default)' -Value $p.Command -Type String
}

$Programs = [Environment]::GetFolderPath('Programs')
$Shell = New-Object -ComObject WScript.Shell

$ScKeep = $Shell.CreateShortcut((Join-Path $Programs 'JamoCombine.lnk'))
$ScKeep.TargetPath = $PythonExe
$ScKeep.Arguments = "`"$ScriptPath`" --keep-open"
$ScKeep.WorkingDirectory = $InstallDir
$ScKeep.Description = '한글 자모 결합기 · 변환 후 창 유지'
$ScKeep.Save()

$ScClose = $Shell.CreateShortcut((Join-Path $Programs 'JamoCombine (변환 후 종료).lnk'))
$ScClose.TargetPath = $PythonExe
$ScClose.Arguments = "`"$ScriptPath`" --close-after-run"
$ScClose.WorkingDirectory = $InstallDir
$ScClose.Description = '한글 자모 결합기 · 변환 완료 후 종료'
$ScClose.Save()

Write-Host ''
Write-Host '[완료] 설치되었습니다.' -ForegroundColor Green
Write-Host '  - 시작 메뉴: "JamoCombine" / "JamoCombine (변환 후 종료)"' -ForegroundColor Gray
Write-Host '  - 탐색기: 폴더에서 우클릭 또는 폴더 안 빈 곳 우클릭 -> 위 메뉴로 현재 폴더 기준 실행.' -ForegroundColor Gray
