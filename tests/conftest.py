from typing import Dict, List

import pandas as pd
import pytest


@pytest.fixture
def sample_transactions_df() -> pd.DataFrame:
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


@pytest.fixture
def cbr_xml_response() -> str:
    """
    Фикстура, предоставляющая тестовый XML-ответ от API ЦБ РФ.
    Содержит курсы USD и EUR с фиксированными значениями для тестирования.
    """
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


@pytest.fixture
def mock_user_settings() -> Dict[str, List[str]]:
    """
    Фикстура с тестовыми пользовательскими настройками.
    """
    return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL"]}
