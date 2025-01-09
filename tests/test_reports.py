import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.reports import save_report, spending_by_category


@pytest.fixture
def sample_transactions():
    """
    Создает тестовый набор транзакций за определенный период.
    Даты генерируются таким образом, чтобы:
    - 5 транзакций попадали в трехмесячный период
    - 1 транзакция выходила за его пределы
    - 1 транзакция была в другой категории
    """
    current_date = datetime.now()

    # Создаем даты с четким распределением:
    # - Текущий месяц
    # - Предыдущий месяц (две записи)
    # - Два месяца назад
    # - Почти три месяца назад
    # - За пределами трех месяцев
    dates = [
        current_date,  # сегодня
        current_date - timedelta(days=20),  # текущий месяц
        current_date - timedelta(days=40),  # предыдущий месяц
        current_date - timedelta(days=50),  # предыдущий месяц
        current_date - timedelta(days=70),  # два месяца назад
        current_date - timedelta(days=95),  # чуть более трех месяцев (не должна учитываться)
        current_date - timedelta(days=30),  # предыдущий месяц (другая категория)
    ]

    data = {
        "date": dates,
        "category": ["Продукты", "Продукты", "Продукты", "Продукты", "Продукты", "Продукты", "Транспорт"],
        "amount": [100.50, 200.75, 150.00, 300.25, 175.50, 250.00, 125.00],
        "description": [f"Магазин {i + 1}" for i in range(7)],
    }
    return pd.DataFrame(data)


def test_spending_by_category_basic(sample_transactions, clean_reports_dir):
    """
    Тестирование базового функционала отчета по категории.
    Проверяем, что функция правильно выбирает все транзакции
    по категории 'Продукты' за последние 3 месяца.
    """
    result = spending_by_category(sample_transactions, "Продукты")

    assert len(result) == 5, f"Ожидалось 5 транзакций, получено {len(result)}"

    assert all(
        row["category"] == "Продукты" for _, row in result.iterrows()
    ), "Все транзакции должны быть категории 'Продукты'"

    dates = pd.to_datetime(result["date"])
    assert (
        dates.max() - dates.min()
    ).days <= 90, "Период между первой и последней транзакцией не должен превышать 90 дней"

    assert list(dates) == list(sorted(dates)), "Результаты должны быть отсортированы по дате"


@pytest.fixture
def clean_reports_dir():
    """Создает и очищает директорию для отчетов перед каждым тестом"""
    reports_dir = Path("reports")
    if reports_dir.exists():
        shutil.rmtree(reports_dir)
    reports_dir.mkdir()
    yield reports_dir
    shutil.rmtree(reports_dir)


def test_spending_by_category_no_data(sample_transactions, clean_reports_dir):
    """Тестирование случая с отсутствующей категорией"""
    result = spending_by_category(sample_transactions, "Несуществующая категория")

    assert len(result) == 0
    assert all(col in result.columns for col in ["date", "category", "amount", "description"])


def test_spending_by_category_specific_date(sample_transactions, clean_reports_dir):
    """Тестирование отчета с указанной датой"""
    specific_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    result = spending_by_category(sample_transactions, "Продукты", specific_date)

    assert len(result) > 0
    assert all(
        datetime.strptime(row["date"], "%Y-%m-%d") <= datetime.strptime(specific_date, "%Y-%m-%d")
        for _, row in result.iterrows()
    )


def test_save_report_default_filename(clean_reports_dir):
    """Тестирование сохранения отчета с именем по умолчанию"""

    @save_report()
    def dummy_report():
        return {"test": "data"}

    dummy_report()

    files = list(clean_reports_dir.glob("dummy_report_*.json"))
    assert len(files) == 1

    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == {"test": "data"}


def test_save_report_custom_filename(clean_reports_dir):
    """Тестирование сохранения отчета с пользовательским именем файла"""

    @save_report("custom_report")
    def dummy_report():
        return {"test": "custom data"}

    dummy_report()

    report_file = clean_reports_dir / "custom_report.json"
    assert report_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == {"test": "custom data"}


def test_save_report_with_dataframe(clean_reports_dir):
    """Тестирование сохранения DataFrame в JSON"""

    @save_report("df_report")
    def dummy_df_report():
        return pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

    dummy_df_report()

    report_file = clean_reports_dir / "df_report.json"
    assert report_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 3
        assert all("col1" in row and "col2" in row for row in data)


def test_invalid_date_format(sample_transactions, clean_reports_dir):
    """Тестирование обработки некорректного формата даты"""
    with pytest.raises(ValueError):
        spending_by_category(sample_transactions, "Продукты", "invalid-date")


def test_report_directory_creation(clean_reports_dir):
    """Тестирование создания директории для отчетов"""
    shutil.rmtree(clean_reports_dir)

    @save_report("test_report")
    def dummy_report():
        return {"test": "data"}

    dummy_report()

    assert clean_reports_dir.exists()
    assert (clean_reports_dir / "test_report.json").exists()
