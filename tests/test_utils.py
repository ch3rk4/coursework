import sys
from datetime import time
from pathlib import Path
from unittest.mock import mock_open, patch

import pandas as pd
import pytest
import requests
import json

from src.utils import (analyze_cards, get_currency_rates, get_greeting,
                       get_stock_prices, get_top_transactions, load_user_settings)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_transactions_df():
    """Create a sample DataFrame for testing."""
    data = {
        "date": pd.date_range("2023-01-01", periods=5),
        "card": ["1234567890123456"] * 3 + ["9876543210987654"] * 2,
        "amount": [100, -50, 200, 300, -150],
        "category": ["Shopping"] * 5,
        "description": ["Test transaction"] * 5,
    }
    return pd.DataFrame(data)


def test_get_greeting():
    """Test greeting generation for different times of day."""
    assert get_greeting(time(6, 0)) == "Доброе утро"
    assert get_greeting(time(13, 0)) == "Добрый день"
    assert get_greeting(time(17, 0)) == "Добрый вечер"
    assert get_greeting(time(1, 0)) == "Доброй ночи"


def test_analyze_cards(sample_transactions_df):
    """Test card analysis functionality."""
    results = analyze_cards(sample_transactions_df)

    assert len(results) == 2  # Should have two unique cards

    # Test first card
    assert results[0]["last_digits"] == "3456"
    assert results[0]["total_spent"] == 350.0  # |100| + |-50| + |200|
    assert results[0]["cashback"] == 3.50

    # Test second card
    assert results[1]["last_digits"] == "7654"
    assert results[1]["total_spent"] == 450.0  # |300| + |-150|
    assert results[1]["cashback"] == 4.50


def test_get_top_transactions(sample_transactions_df):
    """Test top transactions retrieval."""
    results = get_top_transactions(sample_transactions_df, n=3)

    assert len(results) == 3
    # Проверяем формат данных в ответе
    assert isinstance(results[0]["date"], str)
    assert isinstance(results[0]["amount"], float)
    assert "category" in results[0]
    assert "description" in results[0]

    # Проверяем сортировку по абсолютной величине
    amounts = [abs(r["amount"]) for r in results]
    assert amounts == sorted(amounts, reverse=True)


def test_get_top_transactions_empty_df():
    """Test handling of empty DataFrame."""
    empty_df = pd.DataFrame(columns=["date", "card", "amount", "category", "description"])
    assert get_top_transactions(empty_df) == []


@patch("requests.get")
def test_get_currency_rates(mock_get):
    """Test currency rates retrieval."""
    # Подготавливаем мок-ответ
    mock_response = {"rates": {"USD": 0.012, "EUR": 0.011}}
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    results = get_currency_rates(["USD", "EUR"])

    assert len(results) == 2
    assert results[0]["currency"] == "USD"
    assert isinstance(results[0]["rate"], float)


@patch("requests.get")
def test_get_currency_rates_api_error(mock_get):
    """Test error handling in currency rates retrieval."""
    mock_get.side_effect = requests.RequestException
    results = get_currency_rates(["USD"])
    assert results == []


@patch("requests.get")
def test_get_stock_prices(mock_get):
    """Test stock prices retrieval."""
    mock_response = {"Global Quote": {"05. price": "150.25"}}
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    results = get_stock_prices(["AAPL"])

    assert len(results) == 1
    assert results[0]["stock"] == "AAPL"
    assert isinstance(results[0]["price"], float)
    assert results[0]["price"] == 150.25


@patch("requests.get")
def test_get_stock_prices_api_error(mock_get):
    """Test error handling in stock prices retrieval."""
    mock_get.side_effect = requests.RequestException
    results = get_stock_prices(["AAPL"])
    assert results == []


def test_load_user_settings():
    """
    Test user settings loading.
    """
    mock_settings = {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "GOOGL"]
    }

    mock_json = json.dumps(mock_settings)

    with patch("builtins.open", mock_open(read_data=mock_json)):
        settings = load_user_settings()

        assert isinstance(settings, dict)
        assert "user_currencies" in settings
        assert "user_stocks" in settings

        assert settings["user_currencies"] == ["USD", "EUR"]
        assert settings["user_stocks"] == ["AAPL", "GOOGL"]


def test_load_user_settings_file_not_found():
    """Test handling of missing settings file."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        settings = load_user_settings()
        assert settings == {"user_currencies": [], "user_stocks": []}