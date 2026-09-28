import allure
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class BasePage:

    # Тексты страницы блокировки: дом.рф отдаёт её вместо контента, если
    # распознал автоматизированный браузер (например, запущенный в headless).
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

    def check_access_blocked(self):
        """Падаем с понятным сообщением, а не с «голым» TimeoutException."""
        if not self.is_access_blocked():
            return
        raise AssertionError(
            "Сайт вернул страницу блокировки вместо контента "
            f"(title={self.driver.title!r}, url={self.driver.current_url!r}). "
            "дом.рф блокирует headless-браузеры. Запускайте Chrome в обычном "
            "режиме: в CI — через xvfb-run и без переменной окружения HEADLESS."
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