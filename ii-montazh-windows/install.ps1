# Установка «ИИ-монтажа» на Windows.
# Запуск (PowerShell в этой папке):
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
# Ключи:
#   -SkipModel   не скачивать модель Whisper заранее (~1,6 ГБ)
#   -SkipClaude  не ставить Claude Code

param([switch]$SkipModel, [switch]$SkipClaude)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Say($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "    OK: $t" -ForegroundColor Green }
function Warn($t) { Write-Host "    ВНИМАНИЕ: $t" -ForegroundColor Yellow }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

# Путь с кириллицей или пробелами ломает часть программ (Python, npm, Chrome).
if ($PSScriptRoot -match '[^\u0000-\u007F]' -or $PSScriptRoot -match ' ') {
    Warn "Папка набора: $PSScriptRoot"
    Warn "В пути есть русские буквы или пробелы. Надежнее положить набор в C:\montazh и запустить оттуда."
    $a = Read-Host "Продолжить все равно? (y/n)"
    if ($a -ne 'y') { exit 1 }
}

Say "Проверяю winget"
if (-not (Has 'winget')) {
    Write-Host "Нет winget. Обнови «Установщик приложений» (App Installer) в Microsoft Store и запусти снова." -ForegroundColor Red
    exit 1
}
Ok "winget есть"

$pkgs = @(
    @{ Id = 'Git.Git';            Cmd = 'git';    Name = 'Git (нужен Claude Code)' },
    @{ Id = 'OpenJS.NodeJS.LTS';  Cmd = 'node';   Name = 'Node.js LTS (Remotion)' },
    @{ Id = 'Python.Python.3.12'; Cmd = 'py';     Name = 'Python 3.12 (Whisper, скрипты)' },
    @{ Id = 'Gyan.FFmpeg';        Cmd = 'ffmpeg'; Name = 'FFmpeg' },
    @{ Id = 'yt-dlp.yt-dlp';      Cmd = 'yt-dlp'; Name = 'yt-dlp (скачать образцы)' }
)
foreach ($p in $pkgs) {
    Say $p.Name
    if (Has $p.Cmd) { Ok "уже стоит"; continue }
    winget install --id $p.Id -e --source winget --accept-source-agreements --accept-package-agreements --silent
    Refresh-Path
    if (Has $p.Cmd) { Ok "поставлен" } else { Warn "поставлен, но команда $($p.Cmd) пока не видна. Закрой окно PowerShell, открой заново и запусти install.ps1 еще раз." ; exit 1 }
}

Say "Python-окружение и faster-whisper"
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    $hasPy312 = $false
    try { & py -3.12 -c "import sys" 2>$null; $hasPy312 = ($LASTEXITCODE -eq 0) } catch {}
    if ($hasPy312) { & py -3.12 -m venv .venv } else { & python -m venv .venv }
    if (-not (Test-Path '.venv\Scripts\python.exe')) { Write-Host "Не удалось создать .venv" -ForegroundColor Red; exit 1 }
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r tools\requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "pip не смог поставить зависимости" -ForegroundColor Red; exit 1 }
Ok "окружение .venv готово"

Say "Remotion (npm)"
Push-Location remotion
& npm.cmd ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "npm ci завершился с ошибкой" -ForegroundColor Red; exit 1 }
& npx.cmd remotion browser ensure
Pop-Location
Ok "Remotion готов"

if (-not $SkipModel) {
    Say "Скачиваю модель Whisper large-v3-turbo (один раз, ~1,6 ГБ)"
    & .\.venv\Scripts\python.exe tools\transcribe.py --download-only
}

if (-not $SkipClaude) {
    Say "Claude Code"
    if (Has 'claude') { Ok "уже стоит" }
    else {
        Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
        Refresh-Path
        if (Has 'claude') { Ok "поставлен" } else { Warn "поставлен, откроется в новом окне PowerShell" }
    }
}

Say "Проверка"
& ffmpeg -hide_banner -version | Select-Object -First 1
& node -v
& .\.venv\Scripts\python.exe --version
& yt-dlp --version

Write-Host "`nГотово. Дальше:" -ForegroundColor Green
Write-Host "  1) Положи свой ролик в папку input, 4-5 образцов в samples, музыку в music, звуки в sfx."
Write-Host "  2) Открой эту папку в Claude Code (приложение Claude -> вкладка Code, или 'claude' в терминале)."
Write-Host "  3) Скопируй промпт из PROMPTS.md."
