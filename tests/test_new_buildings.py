import allure
import pytest
from pages.new_buildings_page import NewBuildingsPage
from data.test_data import TestData


@allure.feature("Новостройки")
@allure.story("Проверка первого здания в списке")
class TestNewBuildings:

    @allure.title("Проверка значения фильтра и первого здания в списке")
    @allure.description(
        "Переход на сайт, проверка активного фильтра 'По новизне' "
        "и наименования первого здания в списке (ожидается 'Колизей')"
    )
    def test_first_building_in_list(self, driver):
        page = NewBuildingsPage(driver)

        with allure.step("Открыть страницу новостроек"):
            page.open_page()
            page.close_cookie_banner()

        with allure.step(f"Проверить активный фильтр — '{TestData.EXPECTED_FILTER}'"):
            actual_filter = page.get_active_sort_label()
            assert actual_filter == TestData.EXPECTED_FILTER, (
                f"Ожидался фильтр '{TestData.EXPECTED_FILTER}', "
                f"но получен '{actual_filter}'"
            )

        with allure.step("Получить данные первых 5 зданий (для отладки)"):
            buildings = page.get_building_list(limit=5)
            debug_text = "\n".join(
                f"{i + 1}. {b['name']} — {b['address']}"
                for i, b in enumerate(buildings)
            )
            allure.attach(
                debug_text,
                name="Первые 5 зданий в списке",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step(f"Проверить первое здание — '{TestData.EXPECTED_FIRST_BUILDING}'"):
            first_building = page.get_first_building_info()
            first_name = first_building["name"]
            first_address = first_building["address"]

            if first_name != TestData.EXPECTED_FIRST_BUILDING:
                pytest.fail(
                    f"Новое здание!!! "
                    f"Найдено: '{first_name}' "
                    f"по адресу: '{first_address}'"
                )