import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.views import get_dashboard_data

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_settings():
    """Фикстура, имитирующая пользовательские настройки"""
    return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}


@pytest.fixture
def mock_operations_df():
    """Фикстура, представляющая примеры операций DataFrame"""
    data = {
        "Дата платежа": pd.date_range("2024-01-01", periods=5),
        "Номер карты": ["1234"] * 3 + ["5678"] * 2,
        "Сумма платежа": [100, -50, 200, 300, -150],
        "Категория": ["Shopping"] * 5,
        "Описание": ["Test transaction"] * 5,
    }
    return pd.DataFrame(data)


def test_get_dashboard_data_success(mock_settings, mock_operations_df):
    """Тестирование успешного создания данных панели мониторинга со всеми компонентами"""
    test_datetime = "2024-01-15 12:00:00"

    # Mock all external function calls
    with patch("src.views.load_user_settings", return_value=mock_settings), patch(
        "pandas.read_excel", return_value=mock_operations_df
    ), patch("src.views.get_greeting", return_value="Добрый день"), patch(
        "src.views.analyze_cards",
        return_value=[
            {"last_digits": "1234", "total_spent": 350.0, "cashback": 3.50},
            {"last_digits": "5678", "total_spent": 450.0, "cashback": 4.50},
        ],
    ), patch(
        "src.views.get_top_transactions",
        return_value=[
            {
                "Дата платежа": "15.01.2024",
                "Сумма платежа": 300.0,
                "Категория": "Shopping",
                "Описание": "Test transaction",
            }
        ],
    ), patch(
        "src.views.get_currency_rates",
        return_value=[{"currency": "USD", "rate": 90.5}, {"currency": "EUR", "rate": 98.7}],
    ), patch(
        "src.views.get_stock_prices",
        return_value=[{"stock": "AAPL", "price": 185.92}, {"stock": "GOOGL", "price": 142.56}],
    ):
        result = get_dashboard_data(test_datetime)

        assert isinstance(result, dict)
        assert "greeting" in result
        assert "cards" in result
        assert "top_transactions" in result
        assert "currency_rates" in result
        assert "stock_prices" in result

        assert result["greeting"] == "Добрый день"
        assert len(result["cards"]) == 2
        assert len(result["top_transactions"]) == 1
        assert len(result["currency_rates"]) == 2
        assert len(result["stock_prices"]) == 2


def test_get_dashboard_data_file_not_found():
    """Тестовая обработка отсутствующего файла операций"""
    test_datetime = "2024-01-15 12:00:00"

    with patch("src.views.load_user_settings", return_value={"user_currencies": [], "user_stocks": []}), patch(
        "pandas.read_excel", side_effect=FileNotFoundError
    ):
        with pytest.raises(FileNotFoundError):
            get_dashboard_data(test_datetime)


def test_get_dashboard_data_invalid_date():
    """Тестовая обработка недопустимого формата даты и времени"""
    test_datetime = "invalid_date"

    with pytest.raises(ValueError):
        get_dashboard_data(test_datetime)


def test_get_dashboard_data_api_error(mock_settings, mock_operations_df):
    """Тестовая обработка сбоев API"""
    test_datetime = "2024-01-15 12:00:00"

    with patch("src.views.load_user_settings", return_value=mock_settings), patch(
        "pandas.read_excel", return_value=mock_operations_df
    ), patch("src.views.get_greeting", return_value="Добрый день"), patch(
        "src.views.analyze_cards", return_value=[]
    ), patch(
        "src.views.get_top_transactions", return_value=[]
    ), patch(
        "src.views.get_currency_rates", side_effect=Exception("API Error")
    ), patch(
        "src.views.get_stock_prices", return_value=[]
    ):
        with pytest.raises(Exception) as exc_info:
            get_dashboard_data(test_datetime)

        assert "API Error" in str(exc_info.value)


def test_get_dashboard_data_empty_dataframe(mock_settings):
    """Тестовая обработка пустых операций DataFrame"""
    test_datetime = "2024-01-15 12:00:00"
    empty_df = pd.DataFrame(columns=["Дата платежа", "Номер карты", "Сумма платежа", "Категория", "Описание"])

    with patch("src.views.load_user_settings", return_value=mock_settings), patch(
        "pandas.read_excel", return_value=empty_df
    ), patch("src.views.get_greeting", return_value="Добрый день"), patch(
        "src.views.analyze_cards", return_value=[]
    ), patch(
        "src.views.get_top_transactions", return_value=[]
    ), patch(
        "src.views.get_currency_rates", return_value=[]
    ), patch(
        "src.views.get_stock_prices", return_value=[]
    ):
        result = get_dashboard_data(test_datetime)

        assert isinstance(result, dict)
        assert result["cards"] == []
        assert result["top_transactions"] == []
