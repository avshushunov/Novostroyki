<#
    Локальный запуск selenium-теста новостроек (без GitHub Actions).

    Зачем: сайт наш.дом.рф отдаёт страницу «Доступ заблокирован [403]» запросам
    с IP дата-центров, поэтому на раннерах GitHub Actions тест работать не может
    (в URL страницы блокировки видно request_ip раннера). На домашнем компьютере
    с обычным российским IP тест проходит.

    Ручной запуск:
        powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily_test.ps1

    Что делает:
      * открывает Chrome в обычном режиме (headed) и проверяет активный фильтр
        и первый дом в списке новостроек Барнаула;
      * пишет лог в .\logs\run_<дата-время>.log и строку в .\logs\history.csv;
      * при падении оставляет скриншот и HTML страницы в .\artifacts\
        (они же прикладываются к Allure-отчёту), результаты — в .\allure_results\;
      * удаляет логи старше -KeepDays дней.

    Код возврата: 0 — тест прошёл, иначе код ошибки pytest (его видно
    в Планировщике задач как «Код последнего запуска»).

    Автозапуск при старте компьютера настраивается install_scheduled_task.ps1.
#>

[CmdletBinding()]
param(
    # Интерпретатор Python (по умолчанию берётся из PATH).
    [string]$Python = "python",
    # Каталог для логов: относительный (от корня проекта) или абсолютный путь.
    [string]$LogDirectory = "logs",
    # Сколько дней хранить логи.
    [int]$KeepDays = 30,
    # Запустить Chrome без окна. Для дом.рф бесполезно: сайт отдаст 403.
    [switch]$Headless
)

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# --- каталог для логов ------------------------------------------------------
if (-not [System.IO.Path]::IsPathRooted($LogDirectory)) {
    $LogDirectory = Join-Path $repoRoot $LogDirectory
}
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

Get-ChildItem -Path $LogDirectory -Filter "run_*.log" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
    Remove-Item -Force -ErrorAction SilentlyContinue

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logPath = Join-Path $LogDirectory "run_$stamp.log"

# --- проверка окружения -----------------------------------------------------
$resolved = Get-Command $Python -ErrorAction SilentlyContinue
$pythonExe = if ($resolved) { $resolved.Source } else { $Python }

$header = @(
    "=== Тест новостроек: запуск $stamp ==="
    "Каталог проекта : $repoRoot"
    "Python          : $pythonExe"
    "Пользователь    : $env:USERDOMAIN\$env:USERNAME"
    "Headless        : $($Headless.IsPresent)"
    "========================================================="
) -join [Environment]::NewLine
Add-Content -Path $logPath -Value $header -Encoding UTF8

if (-not $resolved) {
    $message = "ОШИБКА: Python не найден (команда '$Python' недоступна)."
    Add-Content -Path $logPath -Value $message -Encoding UTF8
    Write-Host $message
    exit 1
}

# --- окружение теста --------------------------------------------------------
# PYTHONIOENCODING/PYTHONUTF8 + OutputEncoding: чтобы pytest писал UTF-8,
# а PowerShell читал его вывод той же кодировкой (иначе в логе будут кракозябры)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # в задаче Планировщика консоль может быть недоступна — это не критично
}
if ($Headless) {
    $env:HEADLESS = "1"
} else {
    Remove-Item Env:\HEADLESS -ErrorAction SilentlyContinue
}

# --- запуск теста -----------------------------------------------------------
$pytestArgs = @(
    "-m", "pytest", "tests/test_new_buildings.py", "-v",
    "--alluredir=allure_results", "--clean-alluredir"
)
$startedAt = Get-Date
$output = & $pythonExe @pytestArgs 2>&1 | Out-String
$exitCode = $LASTEXITCODE
$elapsed = (Get-Date) - $startedAt
$duration = [int]$elapsed.TotalSeconds

$output | Out-File -FilePath $logPath -Append -Encoding UTF8

# --- итог -------------------------------------------------------------------
$result = if ($exitCode -eq 0) { "PASSED" } else { "FAILED" }

$artifactsPath = Join-Path $repoRoot "artifacts"
$artifactsCount = 0
if (Test-Path $artifactsPath) {
    $artifactsCount = @(Get-ChildItem -Path $artifactsPath -File -ErrorAction SilentlyContinue).Count
}

$summary = @(
    "========================================================="
    "Результат : $result (код возврата $exitCode), время $duration с"
    "Лог       : $logPath"
)
if ($exitCode -ne 0 -and $artifactsCount -gt 0) {
    $summary += "Артефакты : $artifactsPath (скриншот и HTML страницы, файлов: $artifactsCount)"
}
$summary = $summary -join [Environment]::NewLine
Add-Content -Path $logPath -Value $summary -Encoding UTF8

$historyPath = Join-Path $LogDirectory "history.csv"
if (-not (Test-Path $historyPath)) {
    Add-Content -Path $historyPath -Value "Запуск;Результат;Код;Секунды;Лог" -Encoding UTF8
}
Add-Content -Path $historyPath -Value ("{0};{1};{2};{3};{4}" -f $stamp, $result, $exitCode, $duration, "run_$stamp.log") -Encoding UTF8

Write-Host $summary
exit $exitCode
