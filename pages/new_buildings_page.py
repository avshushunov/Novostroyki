import allure
from pages.base_page import BasePage
from locators.new_buildings_locators import NewBuildingsLocators
from urls import Urls


class NewBuildingsPage(BasePage):

    @allure.step("Открыть страницу новостроек в Барнауле")
    def open_page(self):
        self.open(Urls.NEW_BUILDINGS_BARNAUL)

    @allure.step("Закрыть cookie-баннер, если он есть")
    def close_cookie_banner(self):
        if self.is_element_present(NewBuildingsLocators.SEARCH_COOKIE_ACCEPT, timeout=3):
            self.click(NewBuildingsLocators.SEARCH_COOKIE_ACCEPT)

    @allure.step("Получить текст активного фильтра сортировки")
    def get_active_sort_label(self):
        return self.get_text(NewBuildingsLocators.SEARCH_ACTIVE_SORT_LABEL)

    @allure.step("Дождаться загрузки списка зданий")
    def wait_for_building_list(self):
        self.find_element_with_wait(
            NewBuildingsLocators.SEARCH_BUILDING_CARDS,
            timeout=20,
        )

    @allure.step("Получить список карточек зданий")
    def get_building_cards(self):
        return self.find_elements_with_wait(
            NewBuildingsLocators.SEARCH_BUILDING_CARDS,
            timeout=20,
        )

    @allure.step("Извлечь название здания из карточки")
    def _extract_name(self, card):
        title_element = card.find_element(
            *NewBuildingsLocators.SEARCH_BUILDING_TITLE
        )
        return title_element.text.strip()

    @allure.step("Извлечь адрес здания из карточки")
    def _extract_address(self, card):
        try:
            address_element = card.find_element(
                *NewBuildingsLocators.SEARCH_BUILDING_ADDRESS
            )
            return address_element.text.strip()
        except Exception:
            return "<адрес не найден>"

    @allure.step("Получить данные первого здания в списке (название + адрес)")
    def get_first_building_info(self):
        cards = self.get_building_cards()
        if not cards:
            raise AssertionError("Список карточек зданий пуст")

        first_card = cards[0]
        return {
            "name": self._extract_name(first_card),
            "address": self._extract_address(first_card),
        }

    @allure.step("Получить название первого здания в списке")
    def get_first_building_name(self):
        return self.get_first_building_info()["name"]

    @allure.step("Получить список данных зданий (первые {limit})")
    def get_building_list(self, limit=5):
        cards = self.get_building_cards()
        result = []
        for card in cards[:limit]:
            result.append({
                "name": self._extract_name(card),
                "address": self._extract_address(card),
            })
        return result