import pandas as pd
import pytest

from src.services import calculate_investment, investment_bank, round_amount


def test_round_amount():
    """Тестирование функции округления суммы"""
    assert round_amount(1712.0, 50) == 1750.0
    assert round_amount(1999.99, 100) == 2000.0
    assert round_amount(45.5, 10) == 50.0
    assert round_amount(100.0, 50) == 100.0


def test_calculate_investment():
    """Тестирование расчета суммы для инвестирования"""
    assert calculate_investment(1712.0, 50) == 38.0
    assert calculate_investment(1999.99, 100) == 0.01
    assert calculate_investment(45.5, 10) == 4.5
    assert calculate_investment(100.0, 50) == 0.0


def test_investment_bank_basic():
    """Базовое тестирование расчета инвестиций"""
    transactions = [
        {"Дата операции": "2024-01-15", "Сумма операции": 1712.0},
        {"Дата операции": "2024-01-16", "Сумма операции": 45.5},
    ]
    result = investment_bank("2024-01", transactions, 50)
    # 1712 -> 1750 (38) + 45.5 -> 50 (4.5) = 42.5
    assert result == 42.5


def test_investment_bank_empty():
    """Тестирование случая с пустым списком транзакций"""
    assert investment_bank("2024-01", [], 50) == 0.0


def test_investment_bank_different_month():
    """Тестирование фильтрации транзакций по месяцу"""
    transactions = [
        {"Дата операции": "2024-01-15", "Сумма операции": 1712.0},
        {"Дата операции": "2024-02-16", "Сумма операции": 45.5},
    ]
    result = investment_bank("2024-01", transactions, 50)
    # Только первая транзакция должна учитываться
    assert result == 38.0


def test_investment_bank_negative_amounts():
    """Тестирование обработки отрицательных сумм"""
    transactions = [
        {"Дата операции": "2024-01-15", "Сумма операции": 1712.0},
        {"Дата операции": "2024-01-16", "Сумма операции": -45.5},
    ]
    result = investment_bank("2024-01", transactions, 50)
    # Только положительная транзакция должна учитываться
    assert result == 38.0


@pytest.mark.parametrize("invalid_month", ["2024", "2024-13", "24-01", "invalid"])
def test_investment_bank_invalid_month(invalid_month):
    """Тестирование обработки некорректного формата месяца"""
    transactions = [{"Дата операции": "2024-01-15", "Сумма операции": 1712.0}]
    with pytest.raises(ValueError):
        investment_bank(invalid_month, transactions, 50)


def test_investment_bank_invalid_limit():
    """Тестирование обработки некорректного предела округления"""
    transactions = [{"Дата операции": "2024-01-15", "Сумма операции": 1712.0}]
    with pytest.raises(ValueError):
        investment_bank("2024-01", transactions, 0)
    with pytest.raises(ValueError):
        investment_bank("2024-01", transactions, -50)


def test_investment_bank_file():
    """Тестирование работы с реальными данными из файла"""
    # Читаем данные из файла
    df = pd.read_excel("data/operations.xlsx")

    # Преобразуем DataFrame в список словарей
    transactions = df.to_dict("records")

    # Проверяем работу с реальными данными
    result = investment_bank("2024-01", transactions, 50)
    assert isinstance(result, float)
    assert result >= 0


@pytest.mark.parametrize("limit", [10, 50, 100])
def test_investment_bank_different_limits(limit):
    """Тестирование разных пределов округления"""
    transactions = [{"Дата операции": "2024-01-15", "Сумма операции": 1712.0}]
    result = investment_bank("2024-01", transactions, limit)
    assert isinstance(result, float)
    assert result >= 0
