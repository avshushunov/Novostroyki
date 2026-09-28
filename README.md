# Novostroyki

Ежедневная проверка каталога новостроек на сайте наш.дом.рф (Барнаул): активный фильтр
сортировки должен быть «ПО НОВИЗНЕ», а первый дом в списке — «Колизей». Если первым
оказался другой дом, тест падает и пишет в отчёте, что именно найдено — это и есть
сигнал «появилась новостройка».

## Структура проекта

| Путь | Назначение |
| --- | --- |
| `tests/test_new_buildings.py` | сам тест |
| `pages/` | Page Object (`base_page.py`, `new_buildings_page.py`) |
| `locators/new_buildings_locators.py` | локаторы элементов |
| `data/test_data.py` | ожидаемые значения: фильтр и первый дом |
| `conftest.py` | фикстура браузера, артефакты падений, переменные окружения |
| `urls.py` | адреса страниц |
| `run_daily_test.ps1` | локальный запуск теста с логом и историей прогонов |
| `install_scheduled_task.ps1` | автозапуск теста при входе в систему |

## Запуск теста вручную

```powershell
pip install -r requirements.txt
python -m pytest tests/test_new_buildings.py -v
```

То же, но с логом, историей и очисткой старых логов (именно это запускает Планировщик):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily_test.ps1
```

Переменные окружения:

* `HEADLESS=1` — Chrome без окна (на дом.рф бесполезно: сайт отдаёт «Доступ заблокирован [403]»);
* `BROWSER_WINDOW_SIZE=1920,1080` — размер окна браузера;
* `SELENIUM_PROXY=host:port` — прокси, если сайт блокирует IP (логин/пароль Chrome в
  `--proxy-server` не поддерживает, доступ нужно разрешать по IP).

## Автозапуск при старте компьютера

Задача `Novostroyki-DailyTest` запускается при входе в систему (то есть сразу после
включения компьютера) с задержкой 2 минуты, работает от текущего пользователя, права
администратора не нужны. Задачу видно в оснастке `taskschd.msc` (Планировщик заданий).

### Установка

```powershell
# запуск при входе в систему (задержка 2 минуты, чтобы браузер и сеть поднялись)
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1

# то же + немедленная проверка, что тест запускается
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1 -RunNow

# дополнительно ежедневно в 06:00 — если компьютер не перезагружается каждый день
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1 -AddDailyTrigger -DailyTime "06:00"

# другие параметры: -LogonDelayMinutes 5, -Python "C:\Python311\python.exe", -TaskName "Моё имя"
```

### Команды управления

```powershell
# запустить тест немедленно, не дожидаясь следующего входа в систему
Start-ScheduledTask -TaskName Novostroyki-DailyTest

# состояние: время последнего запуска, результат, число пропусков
Get-ScheduledTaskInfo -TaskName Novostroyki-DailyTest

# временно включить/выключить автозапуск, не удаляя задачу
Disable-ScheduledTask -TaskName Novostroyki-DailyTest
Enable-ScheduledTask -TaskName Novostroyki-DailyTest

# история прогонов и последний лог целиком
Get-Content .\logs\history.csv
Get-ChildItem .\logs\run_*.log | Sort-Object LastWriteTime | Select-Object -Last 1 | Get-Content

# HTML-отчёт Allure (нужен allure CLI)
allure serve allure_results

# полностью удалить автозапуск
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1 -Unregister
```

Расшифровка `LastTaskResult` из `Get-ScheduledTaskInfo`: `0` — тест прошёл;
`1` — тест упал (что именно — в `logs\`); `0x41301` — прогон ещё выполняется;
`0x41306` — прогон снят по лимиту 30 минут.

То же самое из Планировщика заданий: `Win+R` → `taskschd.msc` → «Библиотека планировщика
заданий» → `Novostroyki-DailyTest` (вкладки «Триггеры», «Действия», «История»).

### Куда смотреть результаты

* `logs\run_<дата-время>.log` — полный вывод прогона (по одному файлу на запуск);
* `logs\history.csv` — история: дата, результат, код возврата, длительность;
* `artifacts\` — при падении: скриншот и HTML страницы (они же вложены в Allure-отчёт);
* `allure_results\` — результаты для `allure serve allure_results`.

Почему триггер «при входе в систему», а не «при запуске компьютера»: до входа
пользователя нет интерактивного сеанса, Chrome может работать только в headless,
а headless сайт блокирует. Если компьютер входит в систему автоматически, задача
срабатывает сразу после загрузки.

## Про GitHub Actions

Сайт наш.дом.рф защищён антибот-системой и отклоняет запросы с IP дата-центров: раннеры
GitHub Actions работают в Azure, и сайт отдаёт им «Доступ заблокирован [403]» (в URL
страницы блокировки видно `request_ip` раннера). Проверено вручную: запрос из облака — 403,
через сторонний облачный сервис — 451. Сам workflow
`.github/workflows/daily_test.yml` настроен верно (Chrome запускается в обычном режиме
через `xvfb-run`, на падении выгружаются артефакты), но данные с GitHub-раннера получить
нельзя. Рабочие варианты: self-hosted раннер на компьютере с российским IP
(`runs-on: self-hosted`), прокси через секрет `SELENIUM_PROXY` либо локальный запуск по
расписанию — `install_scheduled_task.ps1`.
