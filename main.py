import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.reports import spending_by_category
from src.services import investment_bank
from src.utils import load_user_settings
from src.views import get_dashboard_data


# Настраиваем логирование
def setup_logging(log_level: int = logging.INFO) -> None:
    """
    Настраивает систему логирования с выводом в файл и консоль.
    """
    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Формируем имя файла лога на основе текущей даты
    current_date = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"financial_app_{current_date}.log"

    # Настраиваем форматирование
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Создаем базовую конфигурацию
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )


def load_operations(filepath: Union[str, Path]) -> Any:
    """
    Загружает операции из Excel файла с правильной обработкой колонок.

    Args:
        filepath: Путь к файлу операций

    Returns:
        DataFrame с операциями, где колонки приведены к стандартному виду

    Raises:
        FileNotFoundError: Если файл не найден
    """
    import pandas as pd

    logger = logging.getLogger(__name__)

    try:
        # Читаем файл с явным указанием типов и названий колонок
        operations = pd.read_excel(
            filepath, dtype={"Сумма платежа": float, "Номер карты": str, "Категория": str, "Описание": str}
        )

        # Переименовываем колонки в стандартный вид
        column_mapping = {
            "Дата платежа": "date",
            "Сумма платежа": "amount",
            "Номер карты": "card",
            "Категория": "category",
            "Описание": "description",
        }

        # Проверяем наличие всех необходимых колонок
        missing_columns = [col for col in column_mapping.keys() if col not in operations.columns]
        if missing_columns:
            raise ValueError(f"В файле отсутствуют обязательные колонки: {', '.join(missing_columns)}")

        # Переименовываем колонки
        operations = operations.rename(columns=column_mapping)

        # Преобразуем дату в правильный формат
        operations["Дата платежа"] = pd.to_datetime(operations["date"])

        logger.info(f"Успешно загружено {len(operations)} операций из {filepath}")
        logger.info(f"Колонки в файле: {', '.join(operations.columns)}")
        return operations

    except FileNotFoundError:
        logger.error(f"Файл операций не найден: {filepath}")
        raise
    except ValueError as ve:
        logger.error(f"Ошибка в структуре файла операций: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке операций: {str(e)}")
        raise


def run_financial_analysis(
    operations_file: Union[str, Path],
    category: Optional[str] = None,
    investment_month: Optional[str] = None,
    rounding_limit: int = 100,
) -> Dict[str, Any]:
    """
    Запускает полный финансовый анализ
    """
    logger = logging.getLogger(__name__)
    results: Dict[str, Any] = {}

    try:
        # Загружаем операции
        operations = load_operations(operations_file)

        # Получаем текущую дату и время для дашборда
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формируем дашборд
        logger.info("Формирование дашборда...")
        results["dashboard"] = get_dashboard_data(current_datetime)

        # Если указана категория, анализируем траты по ней
        if category:
            logger.info(f"Анализ трат по категории: {category}")
            results["category_analysis"] = spending_by_category(operations, category)

        # Если указан месяц, рассчитываем инвестиции
        if investment_month:
            logger.info(f"Расчет инвестиций за месяц: {investment_month}")
            # Преобразуем DataFrame в список словарей для investment_bank
            operations_list = operations.to_dict("records")
            results["investment_amount"] = investment_bank(investment_month, operations_list, rounding_limit)

        return results

    except Exception as e:
        logger.error(f"Ошибка при выполнении анализа: {str(e)}")
        raise


def main() -> None:
    """
    Основная функция приложения.
    """
    try:
        # Настраиваем логирование
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Запуск финансового приложения...")

        # Загружаем пользовательские настройки
        settings = load_user_settings()

        # Путь к файлу операций
        operations_file = Path("data") / "operations.xlsx"

        # Текущий месяц для расчета инвестиций
        current_month = datetime.now().strftime("%Y-%m")

        # Запускаем анализ
        results = run_financial_analysis(
            operations_file=operations_file,
            category="Продукты",  # Пример категории
            investment_month=current_month,
            rounding_limit=100,
        )

        # Выводим результаты
        logger.info("Анализ успешно завершен")
        if "dashboard" in results:
            logger.info(f"Данные дашборда получены: {len(results['dashboard'])} показателей")
        if "category_analysis" in results:
            logger.info(f"Проанализировано {len(results['category_analysis'])} транзакций по категории")
        if "investment_amount" in results:
            logger.info(f"Рассчитана сумма для инвестирования: {results['investment_amount']:.2f}")

    except Exception as e:
        logger.error(f"Критическая ошибка при выполнении программы: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
