import pandas as pd
import pytest
from datetime import datetime


@pytest.fixture
def sample_transactions_df():
    """
    Создает тестовый набор данных транзакций.
    """
    data = {
        "date": pd.date_range("2023-01-01", periods=5),
        "card": ["1234567890123456"] * 3 + ["9876543210987654"] * 2,
        "amount": [100, -50, 200, 300, -150],
        "category": ["Shopping"] * 5,
        "description": ["Test transaction"] * 5,
    }
    return pd.DataFrame(data)