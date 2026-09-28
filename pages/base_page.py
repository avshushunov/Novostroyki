import allure
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import parse_qs, urlparse


class BasePage:

    # Тексты страницы блокировки: дом.рф отдаёт её вместо контента, если
    # распознал автоматизированный браузер (headless) ИЛИ если IP клиента
    # относится к дата-центрам/зарубежным хостингам (антибот-защита сайта).
    ACCESS_BLOCKED_MARKERS = (
        "доступ заблокирован",
        "доступ к запрашиваемому ресурсу заблокирован",
    )

    def __init__(self, driver):
        self.driver = driver

    @allure.step("Открыть страницу: {url}")
    def open(self, url):
        self.driver.get(url)
        self.wait_for_page_ready()
        self.check_access_blocked()

    @allure.step("Дождаться полной загрузки страницы")
    def wait_for_page_ready(self, timeout=30):
        WebDriverWait(self.driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

    def is_access_blocked(self):
        """Признак того, что сайт вернул страницу блокировки вместо контента."""
        title = (self.driver.title or "").lower()
        if "блокирован" in title:
            return True
        source = (self.driver.page_source or "").lower()
        return any(marker in source for marker in self.ACCESS_BLOCKED_MARKERS)

    def get_blocked_request_ip(self):
        """IP клиента, зафиксированный антибот-системой в URL страницы блокировки."""
        try:
            query = urlparse(self.driver.current_url or "").query
            return (parse_qs(query).get("request_ip") or [""])[0]
        except Exception:  # noqa: BLE001 - диагностика не должна ломать тест
            return ""

    def check_access_blocked(self):
        """Падаем с понятным сообщением, а не с «голым» TimeoutException."""
        if not self.is_access_blocked():
            return
        request_ip = self.get_blocked_request_ip()
        ip_hint = f", request_ip={request_ip!r}" if request_ip else ""
        raise AssertionError(
            "Сайт вернул страницу блокировки вместо контента "
            f"(title={self.driver.title!r}, url={self.driver.current_url!r}{ip_hint}). "
            "дом.рф блокирует не только headless-браузеры, но и запросы с IP "
            "дата-центров, поэтому IP раннеров GitHub (Azure) сайт отклоняет. "
            "Нужен российский «бытовой» IP: self-hosted раннер либо прокси "
            "в переменной окружения SELENIUM_PROXY."
        )

    @allure.step("Найти элемент с ожиданием")
    def find_element_with_wait(self, locator, timeout=15):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
        except TimeoutException:
            # Проверяем самую частую причину — блокировку доступа антибот-защитой,
            # чтобы в отчёте было видно реальную причину падения
            self.check_access_blocked()
            raise

    @allure.step("Найти все элементы с ожиданием")
    def find_elements_with_wait(self, locator, timeout=15):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located(locator)
        )

    @allure.step("Получить текст элемента")
    def get_text(self, locator, timeout=15):
        return self.find_element_with_wait(locator, timeout).text.strip()

    @allure.step("Проверить наличие элемента на странице")
    def is_element_present(self, locator, timeout=3):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False

    @allure.step("Кликнуть на элемент")
    def click(self, locator, timeout=10):
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        ).click()