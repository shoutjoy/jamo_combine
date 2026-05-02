#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\JamoCombine'
$MenuRoots = @(
    'HKCU:\Software\Classes\Directory\shell\KOR_NFC_Converter'
    'HKCU:\Software\Classes\Directory\Background\shell\KOR_NFC_Converter'
)

foreach ($MenuRoot in $MenuRoots) {
    if (Test-Path $MenuRoot) {
        Remove-Item -Path $MenuRoot -Recurse -Force
    }
}

$Programs = [Environment]::GetFolderPath('Programs')
foreach ($name in @('JamoCombine.lnk', 'JamoCombine (변환 후 종료).lnk')) {
    $ShortcutPath = Join-Path $Programs $name
    if (Test-Path $ShortcutPath) {
        Remove-Item -Path $ShortcutPath -Force
    }
}

if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
}

Write-Host '[완료] 제거되었습니다. (레지스트리 메뉴, 시작 메뉴 바로가기, 설치 폴더)' -ForegroundColor Green
