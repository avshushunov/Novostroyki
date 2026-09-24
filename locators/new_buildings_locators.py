from selenium.webdriver.common.by import By


class NewBuildingsLocators:
    # Активный фильтр сортировки (например, "По новизне")
    SEARCH_ACTIVE_SORT_LABEL = (
        By.XPATH,
        "//span[contains(@class, 'ActiveSortLabel')]"
    )

    # Карточки зданий в списке новостроек
    SEARCH_BUILDING_CARDS = (
        By.XPATH,
        "//div[contains(@class, 'NewBuildingItem__Wrapper')]"
    )

    # Название здания внутри карточки (ссылка-заголовок)
    SEARCH_BUILDING_TITLE = (
        By.XPATH,
        ".//a[contains(@class, 'NewBuildingItem__MainTitle')]"
    )

    # Адрес здания внутри карточки
    SEARCH_BUILDING_ADDRESS = (
        By.XPATH,
        ".//p[contains(@class, 'NewBuildingItem__Address')]"
    )

    # Cookie-баннер
    SEARCH_COOKIE_ACCEPT = (
        By.XPATH,
        "//button[contains(text(), 'Принять') or contains(text(), 'Согласен')]"
    )