import logging
import math
from datetime import datetime
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def round_amount(amount: float, limit: int) -> float:
    """Округляет сумму до ближайшего верхнего значения, кратного пределу"""
    return math.ceil(amount / limit) * limit


def calculate_investment(amount: float, limit: int) -> float:
    """Вычисляет сумму для инвестирования на основе разницы между округленной и исходной суммой"""
    rounded = round_amount(amount, limit)
    return round(rounded - amount, 2)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """Рассчитывает общую сумму, которую можно отложить в инвесткопилку за месяц"""
    try:
        target_date = datetime.strptime(month, "%Y-%m")
        logger.info(f"Расчет инвестиций для месяца: {month}")

        if limit <= 0:
            raise ValueError("Предел округления должен быть положительным числом")

        total_investment = 0.0

        for transaction in transactions:
            trans_date = datetime.strptime(transaction["Дата операции"], "%Y-%m-%d")
            if trans_date.year == target_date.year and trans_date.month == target_date.month:
                amount = float(transaction["Сумма операции"])

                if amount > 0:
                    investment = calculate_investment(amount, limit)
                    total_investment += investment
                    logger.debug(f"Транзакция {amount} -> инвестиция {investment}")

        return round(total_investment, 2)

    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при расчете инвестиций: {str(e)}")
        raise
