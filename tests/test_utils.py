import sys
from datetime import time
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

from src.utils import analyze_cards, get_currency_rates, get_greeting, get_stock_prices, get_top_transactions

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_transactions_df():
    """Создание образца DataFrame для тестирования"""
    data = {
        "Дата платежа": pd.date_range("2023-01-01", periods=5),
        "Номер карты": ["1234567890123456"] * 3 + ["9876543210987654"] * 2,
        "Сумма платежа": [100, -50, 200, 300, -150],
        "Категория": ["Shopping"] * 5,
        "Описание": ["Test transaction"] * 5,
    }
    return pd.DataFrame(data)


def test_get_greeting():
    """Тестирование приветствия для разного времени"""
    assert get_greeting(time(6, 0)) == "Доброе утро"
    assert get_greeting(time(13, 0)) == "Добрый день"
    assert get_greeting(time(17, 0)) == "Добрый вечер"
    assert get_greeting(time(1, 0)) == "Доброй ночи"


def test_analyze_cards(sample_transactions_df):
    """Tест функционала анализа карты"""
    results = analyze_cards(sample_transactions_df)

    assert len(results) == 2  # Should have two unique cards

    assert results[0]["last_digits"] == "3456"
    assert results[0]["total_spent"] == 350.0  # |100| + |-50| + |200|
    assert results[0]["cashback"] == 3.50

    assert results[1]["last_digits"] == "7654"
    assert results[1]["total_spent"] == 450.0  # |300| + |-150|
    assert results[1]["cashback"] == 4.50


def test_get_top_transactions(sample_transactions_df):
    """Тестирование извлечения основных транзакций"""
    results = get_top_transactions(sample_transactions_df, n=3)

    assert len(results) == 3
    assert isinstance(results[0]["Дата платежа"], str)
    assert isinstance(results[0]["Сумма платежа"], float)
    assert "Категория" in results[0]
    assert "Описание" in results[0]

    amounts = [abs(r["Сумма платежа"]) for r in results]
    assert amounts == sorted(amounts, reverse=True)


def test_get_top_transactions_empty_df():
    """Тестовая обработка пустого DataFrame"""
    empty_df = pd.DataFrame(columns=["Дата платежа", "Номер карты", "Сумма платежа", "Категория", "Описание"])
    assert get_top_transactions(empty_df) == []


@pytest.fixture
def mock_cbr_response():
    """Фикстура, обеспечивающая фиктивный ответ CBR API XML"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<ValCurs Date="09.01.2024" name="Foreign Currency Market">
    <Valute ID="R01235">
        <NumCode>840</NumCode>
        <CharCode>USD</CharCode>
        <Nominal>1</Nominal>
        <Name>Доллар США</Name>
        <Value>90,90</Value>
    </Valute>
    <Valute ID="R01239">
        <NumCode>978</NumCode>
        <CharCode>EUR</CharCode>
        <Nominal>1</Nominal>
        <Name>Евро</Name>
        <Value>100,00</Value>
    </Valute>
</ValCurs>"""


def test_get_currency_rates_success(mock_cbr_response):
    """Тест успешного получения курсов валют"""
    currencies = ["USD", "EUR"]

    mock_response = Mock()
    mock_response.content = mock_cbr_response.encode("utf-8")
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = get_currency_rates(currencies)

        assert len(result) == 2
        assert result[0]["currency"] == "USD"
        assert result[0]["rate"] == 90.90
        assert result[1]["currency"] == "EUR"
        assert result[1]["rate"] == 100.00


def test_get_currency_rates_http_error():
    """Тестовая обработка ошибок HTTP при получении курсов валют"""
    currencies = ["USD", "EUR"]

    with patch("requests.get", side_effect=requests.RequestException("Connection error")):
        with pytest.raises(requests.RequestException) as exc_info:
            get_currency_rates(currencies)
        assert "Connection error" in str(exc_info.value)


def test_get_currency_rates_invalid_xml():
    """Тестовая обработка недопустимого ответа XML"""
    currencies = ["USD", "EUR"]

    mock_response = Mock()
    mock_response.content = "Invalid XML".encode("utf-8")
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(Exception) as exc_info:
            get_currency_rates(currencies)
        assert "ParseError" in str(exc_info.type)


def test_get_currency_rates_empty_list():
    """Тестовая обработка пустого списка валют"""
    result = get_currency_rates([])
    assert result == []


@pytest.fixture
def mock_stock_response():
    """Фикстура, обеспечивающая ответ API фиктивного запаса"""
    return {"Global Quote": {"01. symbol": "AAPL", "05. price": "185.92"}}


def test_get_stock_prices_success(mock_stock_response):
    """Тест успешного извлечения цен акций"""
    stocks = ["AAPL"]

    mock_response = Mock()
    mock_response.json.return_value = mock_stock_response
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = get_stock_prices(stocks)

        assert len(result) == 1
        assert result[0]["stock"] == "AAPL"
        assert result[0]["price"] == 185.92


def test_get_stock_prices_http_error():
    """Тестовая обработка ошибок HTTP при извлечении цен на акции"""
    stocks = ["AAPL"]

    with patch("requests.get", side_effect=requests.RequestException("API error")):
        result = get_stock_prices(stocks)
        assert result == []


def test_get_stock_prices_invalid_response():
    """Тестовая обработка недопустимого ответа API"""
    stocks = ["AAPL"]

    mock_response = Mock()
    mock_response.json.return_value = {"error": "Invalid API response"}
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = get_stock_prices(stocks)
        assert result == []


def test_get_stock_prices_empty_list():
    """Тестовая обработка пустого списка запасов"""
    result = get_stock_prices([])
    assert result == []


def test_get_stock_prices_multiple_stocks(mock_stock_response):
    """Тестовое извлечение нескольких цен акций"""
    stocks = ["AAPL", "GOOGL"]

    responses = [
        {"Global Quote": {"01. symbol": "AAPL", "05. price": "185.92"}},
        {"Global Quote": {"01. symbol": "GOOGL", "05. price": "142.56"}},
    ]

    mock_responses = []
    for response in responses:
        mock = Mock()
        mock.json.return_value = response
        mock.raise_for_status = Mock()
        mock_responses.append(mock)

    with patch("requests.get", side_effect=mock_responses):
        result = get_stock_prices(stocks)

        assert len(result) == 2
        assert result[0]["stock"] == "AAPL"
        assert result[0]["price"] == 185.92
        assert result[1]["stock"] == "GOOGL"
        assert result[1]["price"] == 142.56
