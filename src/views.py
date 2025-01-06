
import logging
from datetime import datetime
from typing import List, Literal, TypedDict

import pandas as pd

from main import FILE_PATH

GreetingType = Literal["Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи"]


class CardInfo(TypedDict):
    last_digits: str
    total_spent: float
    cashback: float


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def get_greeting(time: datetime) -> GreetingType:
    hour = time.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 17:
        return "Добрый день"
    elif 17 <= hour < 21:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_card_info() -> List[CardInfo]:
    try:
        if not FILE_PATH.exists():
            logger.error("Файл не найден")
            raise FileNotFoundError("Файл transactions.xlsx отсутствует в директории data")

        if FILE_PATH.suffix.lower() not in [".xlsx", ".xls"]:
            logging.error("Неверный формат файла")
            raise

        df = pd.read_excel(FILE_PATH)
        unique_cards = df["Номер карты"].unique()
        cards_info = []

        for card_number in unique_cards:
            last_digits = str(card_number)[-4:]

            card_transaction = df[(df["Номер карты"] == last_digits) & (df["Сумма платежа"] < 0)]
            total_spent = float(abs(card_transaction["Сумма платежа"].sum()))

            cashback = float(total_spent * 0.01)

        card_info: CardInfo = {
            "last_digits": str(last_digits),
            "total_spent": float(total_spent),
            "cashback": float(cashback),
        }

        cards_info.append(card_info)
        return cards_info
    except Exception as e:
        logger.error(f"Ошибка при чтении файла транзакций: {str(e)}")
        raise


#  FileNotFoundError: если файл не найден
#  pd.errors.EmptyDataError: если файл пуст
#  ValueError: если данные в файле некорректны
