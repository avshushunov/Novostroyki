import os

import pytest
from selenium import webdriver

# Настройки браузера
# ---------------------------------------------------------------------------
# Сайт дом.рф защищён антибот-системой: вместо каталога новостроек headless-браузер
# получает страницу «Доступ заблокирован [403]» и тест падает на ожидании элемента.
# Поэтому Chrome запускается в ОБЫЧНОМ (headed) режиме, а в CI для него поднимается
# виртуальный дисплей Xvfb (см. .github/workflows/daily_test.yml).
# Headless можно включить явно переменной окружения HEADLESS=1, но на дом.рф
# он гарантированно попадает на страницу блокировки.
IS_HEADLESS = os.environ.get("HEADLESS", "").strip().lower() in {"1", "true", "yes", "on"}
WINDOW_SIZE = os.environ.get("BROWSER_WINDOW_SIZE", "1920,1080")
# Необязательный прокси (например, если сайт блокирует IP раннера):
# SELENIUM_PROXY=http://host:port
# ВНИМАНИЕ: Chrome игнорирует логин/пароль в --proxy-server, поэтому для прокси
# с авторизацией нужен отдельный механизм (например, расширение с авторизацией).
PROXY = os.environ.get("SELENIUM_PROXY", "").strip()
ARTIFACTS_DIR = "artifacts"


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--window-size={WINDOW_SIZE}")
    options.add_argument("--lang=ru-RU")
    # Прячем признаки автоматизации, чтобы антибот-защита не блокировала доступ.
    # ВАЖНО: подменять User-Agent нельзя — рассинхрон с Client Hints (sec-ch-ua)
    # сам по себе приводит к странице «Доступ заблокирован»
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if PROXY:
        options.add_argument(f"--proxy-server={PROXY}")

    if IS_HEADLESS:
        options.add_argument("--headless=new")

    if os.environ.get("CI"):
        # В CI мало /dev/shm и нет прав root
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    # Явный таймаут загрузки страницы: иначе Selenium может ждать 300 секунд
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(5)

    yield driver

    driver.quit()


def _save_failure_artifacts(driver, test_name):
    """Сохраняет скриншот и HTML страницы падения и прикладывает их к Allure."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    screenshot_path = os.path.join(ARTIFACTS_DIR, f"failure_{test_name}.png")
    html_path = os.path.join(ARTIFACTS_DIR, f"failure_{test_name}.html")

    try:
        driver.save_screenshot(screenshot_path)
        print(f"Скриншот сохранён: {screenshot_path}")
    except Exception as exc:  # noqa: BLE001 - сохранение артефактов не должно ломать тест
        print(f"Не удалось сохранить скриншот: {exc}")

    try:
        with open(html_path, "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print(f"HTML страницы сохранён: {html_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось сохранить HTML страницы: {exc}")

    try:
        import allure
    except ImportError:
        return

    try:
        if os.path.exists(screenshot_path):
            allure.attach.file(
                screenshot_path,
                name="Скриншот падения",
                attachment_type=allure.attachment_type.PNG,
            )
        if os.path.exists(html_path):
            allure.attach.file(
                html_path,
                name="HTML страницы на момент падения",
                attachment_type=allure.attachment_type.HTML,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось приложить артефакты к Allure: {exc}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            test_name = item.name.replace("/", "_").replace("\\", "_")
            _save_failure_artifacts(driver, test_name)