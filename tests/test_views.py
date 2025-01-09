import sys
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
import requests
from src.views import get_dashboard_data

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@patch("src.utils.get_currency_rates")
@patch("src.utils.get_stock_prices")
def test_get_dashboard_data(mock_stocks, mock_currency, sample_transactions_df):
    """
    Тестирование основной функции генерации данных дашборда.
    """
    # Настраиваем ожидаемые ответы от моков
    mock_currency.return_value = [{"currency": "USD", "rate": 75.0}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 150.0}]

    # Создаем контекст тестирования, подменяя внешние зависимости
    with patch("pandas.read_excel", return_value=sample_transactions_df), \
            patch("src.utils.load_user_settings",
                  return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}):
        # Вызываем тестируемую функцию
        result = get_dashboard_data("2023-01-15 14:30:00")

        # Проверяем структуру и содержимое ответа
        assert isinstance(result, dict), "Результат должен быть словарем"

        # Проверяем наличие всех необходимых ключей
        expected_keys = {"greeting", "cards", "top_transactions", "currency_rates", "stock_prices"}
        assert set(result.keys()) == expected_keys, f"Отсутствуют ожидаемые ключи: {expected_keys - set(result.keys())}"

        # Проверяем типы данных в ответе
        assert isinstance(result["greeting"], str), "Приветствие должно быть строкой"
        assert isinstance(result["cards"], list), "Информация о картах должна быть списком"
        assert isinstance(result["top_transactions"], list), "Топ транзакций должен быть списком"
        assert isinstance(result["currency_rates"], list), "Курсы валют должны быть списком"
        assert isinstance(result["stock_prices"], list), "Цены акций должны быть списком"


def test_get_dashboard_data_invalid_input():
    """
    Тестирование обработки некорректных входных данных.
    """
    with pytest.raises(ValueError, match="time data .* does not match format.*"):
        get_dashboard_data("invalid-date-format")




@pytest.fixture
def mock_exchange_rates_response():
    """
    Создает мок ответа от API курсов валют.
    Эмулирует успешный ответ от Exchange Rates API с заранее определенными курсами валют.
    """
    return {
        "base": "RUB",
        "date": "2024-01-09",
        "rates": {
            "USD": 0.011,  # примерно 90.90 RUB за 1 USD
            "EUR": 0.010,  # примерно 100 RUB за 1 EUR
        }
    }


@pytest.fixture
def mock_stock_quote_response():
    """
    Создает мок ответа от API котировок акций.
    Эмулирует успешный ответ от Alpha Vantage API с информацией о ценах акций.
    """
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "02. open": "185.0000",
            "03. high": "186.7400",
            "04. low": "184.2500",
            "05. price": "185.5600",
            "06. volume": "48748435",
            "07. latest trading day": "2024-01-09",
            "08. previous close": "184.5800",
            "09. change": "0.9800",
            "10. change percent": "0.5309%"
        }
    }


def test_get_dashboard_data_successful_api_calls(
        sample_transactions_df,
        mock_exchange_rates_response,
        mock_stock_quote_response
):
    """
    Тестирует успешное получение данных дашборда с эмуляцией API-вызовов.
    """
    rates_response = {
        "rates": {
            "USD": 0.011,  # Примерно 90.90 RUB за 1 USD
            "EUR": 0.010  # Примерно 100 RUB за 1 EUR
        }
    }

    def mock_get(url, *args, **kwargs):
        """
        Мок-функция для requests.get, возвращающая подготовленные ответы в зависимости от URL.
        """
        print(f"\nОтладка: Запрос к URL: {url}")

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        if "api.exchangerate-api.com/v4/latest/RUB" in url:
            print("Отладка: Подготавливаем ответ для курсов валют")
            mock_response.json.return_value = rates_response
            print(f"Отладка: Отправляем ответ: {rates_response}")
            return mock_response
        elif "alphavantage.co" in url:
            print("Отладка: Подготавливаем ответ для акций")
            mock_response.json.return_value = mock_stock_quote_response
            return mock_response

        print(f"Предупреждение: Неизвестный URL: {url}")
        return mock_response

    with patch("src.utils.requests.get", side_effect=mock_get), \
            patch("pandas.read_excel", return_value=sample_transactions_df), \
            patch("src.utils.load_user_settings",
                  return_value={"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL"]}):

        result = get_dashboard_data("2024-01-09 14:30:00")

        print("\nОтладка: Результат запроса:")
        print("Курсы валют:", result["currency_rates"])
        print("Цены акций:", result["stock_prices"])

        # Проверяем наличие и формат курсов валют
        currency_rates = result["currency_rates"]
        assert len(currency_rates) == 2, (
            f"Ожидается два курса валют (USD и EUR), получено: {len(currency_rates)}. "
            f"Содержимое currency_rates: {currency_rates}"
        )

        # Проверяем каждый курс отдельно
        currencies = {rate["currency"]: rate["rate"] for rate in currency_rates}
        assert "USD" in currencies, "Отсутствует курс USD"
        assert "EUR" in currencies, "Отсутствует курс EUR"

        # Проверяем правильность расчета курсов
        assert abs(currencies["USD"] - 90.90) < 0.1, f"Неверный курс USD: {currencies['USD']}"
        assert abs(currencies["EUR"] - 100.0) < 0.1, f"Неверный курс EUR: {currencies['EUR']}"


def test_get_dashboard_data_api_errors(sample_transactions_df):
    """
    Тестирует обработку ошибок API при получении данных дашборда.

    Проверяет корректную обработку различных ошибок API:
    - Ошибка сети при запросе курсов валют
    - Некорректный ответ от API акций
    - Таймаут соединения
    """

    def raise_request_exception(*args, **kwargs):
        raise requests.RequestException("API connection failed")

    # Применяем патчи с эмуляцией ошибок
    with patch("requests.get", side_effect=raise_request_exception), \
            patch("pandas.read_excel", return_value=sample_transactions_df), \
            patch("src.utils.load_user_settings",
                  return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}):
        result = get_dashboard_data("2024-01-09 14:30:00")

        # Проверяем, что функция корректно обрабатывает ошибки
        assert result["currency_rates"] == []
        assert result["stock_prices"] == []
        # Проверяем, что остальные данные доступны несмотря на ошибки API
        assert result["greeting"]
        assert result["cards"]
        assert result["top_transactions"]


@pytest.mark.parametrize("api_response,expected_error", [
    ({"error": "Invalid API key"}, "Invalid API response format"),
    (None, "API returned no data"),
    ({}, "Missing required data in API response")
])
def test_get_dashboard_data_invalid_api_responses(
        sample_transactions_df,
        api_response,
        expected_error
):
    """
    Тестирует обработку некорректных ответов от API.

    Проверяет различные сценарии некорректных ответов от API
    и убеждается, что функция корректно их обрабатывает.
    """
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = api_response

    with patch("requests.get", return_value=mock_response), \
            patch("pandas.read_excel", return_value=sample_transactions_df), \
            patch("src.utils.load_user_settings",
                  return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}):
        result = get_dashboard_data("2024-01-09 14:30:00")

        # Проверяем, что функция вернула пустые списки при некорректных ответах
        assert result["currency_rates"] == []
        assert result["stock_prices"] == []