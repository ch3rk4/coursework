import json
import sys
from datetime import datetime, time
from pathlib import Path
from unittest.mock import mock_open, patch

import pandas as pd
import pytest
import requests

from src.views import (analyze_cards, get_currency_rates, get_dashboard_data, get_greeting, get_stock_prices,
                       get_top_transactions, load_user_settings)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_df():
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


def test_analyze_cards(sample_df):
    """Test card analysis functionality."""
    results = analyze_cards(sample_df)

    assert len(results) == 2
    assert results[0]["last_digits"] == "3456"
    assert results[0]["total_spent"] == 350.0  # |100 - 50 + 200|
    assert results[0]["cashback"] == 3.50

    assert results[1]["last_digits"] == "7654"
    assert results[1]["total_spent"] == 450.0  # |300 - 150|
    assert results[1]["cashback"] == 4.50


def test_get_top_transactions(sample_df):
    """Test top transactions retrieval."""
    results = get_top_transactions(sample_df, n=3)

    assert len(results) == 3
    assert isinstance(results[0]["date"], str)
    assert isinstance(results[0]["amount"], float)
    assert "category" in results[0]
    assert "description" in results[0]


@patch("requests.get")
def test_get_currency_rates(mock_get):
    """Test currency rates retrieval."""
    mock_response = {"rates": {"USD": 0.012, "EUR": 0.011}}
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    results = get_currency_rates(["USD", "EUR"])

    assert len(results) == 2
    assert results[0]["currency"] == "USD"
    assert isinstance(results[0]["rate"], float)


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


def test_load_user_settings():
    """Test user settings loading."""
    mock_settings = {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "GOOGL"]}

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_settings))):
        settings = load_user_settings()

        assert settings == mock_settings
        assert "user_currencies" in settings
        assert "user_stocks" in settings


@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_get_dashboard_data(mock_stocks, mock_currency, sample_df):
    """Test main dashboard data generation."""
    mock_currency.return_value = [{"currency": "USD", "rate": 75.0}]
    mock_stocks.return_value = [{"stock": "AAPL", "price": 150.0}]

    with patch("pandas.read_excel", return_value=sample_df), patch(
        "src.views.load_user_settings", return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    ):
        result = get_dashboard_data("2023-01-15 14:30:00")

        assert isinstance(result, dict)
        assert "greeting" in result
        assert "cards" in result
        assert "top_transactions" in result
        assert "currency_rates" in result
        assert "stock_prices" in result


def test_get_dashboard_data_invalid_input():
    """Test error handling for invalid input."""
    with pytest.raises(ValueError):
        get_dashboard_data("invalid-date-format")


@pytest.mark.parametrize("api_error", [requests.RequestException, requests.ConnectionError, requests.Timeout])
@patch("requests.get")
def test_api_error_handling(mock_get, api_error):
    """Test handling of various API errors."""
    mock_get.side_effect = api_error

    # Should return empty list instead of raising exception
    assert get_currency_rates(["USD"]) == []
    assert get_stock_prices(["AAPL"]) == []


def test_empty_dataframe():
    """Test handling of empty DataFrame."""
    empty_df = pd.DataFrame(columns=["date", "card", "amount", "category", "description"])

    assert analyze_cards(empty_df) == []
    assert get_top_transactions(empty_df) == []
