<#
    Регистрация задачи Планировщика Windows, которая запускает тест новостроек
    при входе в систему (то есть сразу после включения компьютера).

    Почему триггер «при входе в систему», а не «при запуске компьютера»:
    до входа пользователя нет интерактивного сеанса, а Chrome в таком режиме
    умеет работать только в headless, который сайт наш.дом.рф блокирует
    («Доступ заблокирован [403]»). При входе в систему сеанс интерактивный,
    Chrome запускается обычным окном и тест проходит. Если компьютер
    включается с автоматическим входом — тест стартует сразу после загрузки.

    Установка (права администратора не нужны):
        powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1

    Установка с немедленной проверкой (тест запустится сразу):
        powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1 -RunNow

    Дополнительно ежедневно в 06:00 (на случай, если ПК не перезагружается):
        ... -AddDailyTrigger -DailyTime "06:00"

    Проверить состояние задачи:
        Get-ScheduledTaskInfo -TaskName Novostroyki-DailyTest

    Удалить задачу:
        powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1 -Unregister
#>

[CmdletBinding()]
param(
    # Имя задачи в Планировщике.
    [string]$TaskName = "Novostroyki-DailyTest",
    # Интерпретатор Python (по умолчанию берётся из PATH).
    [string]$Python = "python",
    # Задержка после входа в систему, минут: браузеру и сети нужно подняться.
    [int]$LogonDelayMinutes = 2,
    # Добавить ежедневный триггер.
    [switch]$AddDailyTrigger,
    # Время ежедневного запуска.
    [string]$DailyTime = "06:00",
    # Сразу запустить задачу после регистрации.
    [switch]$RunNow,
    # Удалить задачу и выйти.
    [switch]$Unregister
)

$user = "$env:USERDOMAIN\$env:USERNAME"

if ($Unregister) {
    if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        Write-Host "Задача '$TaskName' не найдена — удалять нечего."
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Задача '$TaskName' удалена, автозапуск теста отключён."
    exit 0
}

$repoRoot = $PSScriptRoot
$runner = Join-Path $repoRoot "run_daily_test.ps1"
if (-not (Test-Path $runner)) {
    Write-Host "ОШИБКА: не найден скрипт запуска $runner"
    exit 1
}

$pythonExe = $Python
$resolved = Get-Command $Python -ErrorAction SilentlyContinue
if ($resolved) {
    $pythonExe = $resolved.Source
} else {
    Write-Host "ПРЕДУПРЕЖДЕНИЕ: команда '$Python' не найдена в PATH."
    Write-Host "              Укажите путь явно: -Python C:\путь\к\python.exe"
}

# Действие задачи: скрытое окно PowerShell запускает run_daily_test.ps1
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Python "{1}"' -f $runner, $pythonExe
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $repoRoot

$triggers = @()
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $user
try {
    $logonTrigger.Delay = "PT{0}M" -f $LogonDelayMinutes
} catch {
    Write-Host "ПРЕДУПРЕЖДЕНИЕ: не удалось задать задержку после входа в систему."
}
$triggers += $logonTrigger

if ($AddDailyTrigger) {
    $triggers += New-ScheduledTaskTrigger -Daily -At $DailyTime
}

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$description = "Запуск selenium-теста новостроек (pytest) при входе в систему. Логи: $repoRoot\logs. Удаление: install_scheduled_task.ps1 -Unregister"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description $description -Force | Out-Null

$triggersInfo = "вход в систему (+$LogonDelayMinutes мин)"
if ($AddDailyTrigger) {
    $triggersInfo = "$triggersInfo, ежедневно в $DailyTime"
}

Write-Host "Задача '$TaskName' зарегистрирована."
Write-Host "  Пользователь : $user"
Write-Host "  Python       : $pythonExe"
Write-Host "  Триггеры     : $triggersInfo"
Write-Host "  Логи теста   : $(Join-Path $repoRoot 'logs')"
$nextRun = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
if ($nextRun) {
    Write-Host ("  Следующий запуск: {0}" -f $nextRun)
} else {
    Write-Host "  Следующий запуск: при следующем входе в систему"
}

if ($RunNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Тест запущен немедленно: окно Chrome откроется и закроется само."
    Write-Host "Результат смотрите в logs\history.csv и в Get-ScheduledTaskInfo -TaskName $TaskName"
}
