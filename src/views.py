import logging
from datetime import datetime
from typing import List, Literal, TypedDict
from xml.etree import ElementTree

import pandas as pd
import requests

from main import FILE_PATH

GreetingType = Literal["Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи"]


class CardInfo(TypedDict):
    last_digits: str
    total_spent: float
    cashback: float


class Transaction(TypedDict):
    date: str
    amount: float
    category: str
    description: str


class CurrencyRate(TypedDict):
    currency: str
    rate: float


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def generate_report(datetime_str: str) -> datetime:
    input_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    return input_datetime


def get_greeting(input_datetime: datetime) -> GreetingType:
    hour = input_datetime.hour
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


def get_top_transaction(input_datetime: datetime) -> List[Transaction]:
    try:
        df = pd.read_excel(FILE_PATH)
        required_columns = {"Дата платежа", "Сумма платежа", "Категория", "Описание"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise ValueError(f"В файле отсутствуют необходимые столбцы: {missing}")
        df["Дата платежа"] = pd.to_datetime(df["Дата платежа"])
        df = df[df["Дата платежа"] <= input_datetime]
        df = df.sort_values("Сумма платежа", key=lambda x: abs(x), ascending=False).head(5)
        top_transactions = []
        for _, row in df.iterrows():
            transaction: Transaction = {
                "date": str(row["Дата платежа"].strftime("%d.%m.%h")),
                "amount": float(row["Сумма платежа"]),
                "category": str(row["Категория"]),
                "description": str(row["Описание"]),
            }
            top_transactions.append(transaction)

        return top_transactions
    except Exception as e:
        logger.error(f"ошибка при получении транзакции: {str(e)}")
        raise


def get_currency_rate(input_datetime: datetime) -> List[CurrencyRate]:
    try:
        date_str = input_datetime.strftime("%d/%m/%Y")
        url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={date_str}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        tree = ElementTree.fromstring(response.content)
        currencies_is_interest = {"USD", "EUR"}
        result = []
        for valute in tree.findall("Valute"):
            char_code = valute.find("CharCode")
            if char_code is None or char_code.text is None:
                logger.warning("Найден элемент Valute без кода валюты")
                continue

            if char_code in currencies_is_interest:
                value_element = valute.find("Value")
                if value_element is None or value_element.text is None:
                    logger.warning(f"Для валюты {char_code} не найдено значение курса")
                    continue
                try:
                    rate_str = value_element.text.replace(",", ".")
                    rate = float(rate_str)
                    currency_rate: CurrencyRate = {"currency": str(char_code), "rate": rate}
                    result.append(currency_rate)

                except ValueError as e:
                    logger.warning(f"Не удалось преобразовать курс валюты {char_code}: {str(e)}")
                    continue

        if len(result) != len(currencies_is_interest):
            missing = currencies_is_interest - {r["currency"] for r in result}
            logger.warning(f"Не удалось получить курсы для валют: {missing}")
        return result
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API ЦБ РФ: {e}")
        raise
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML ответа: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении курсов валют: {str(e)}")
        raise


#  FileNotFoundError: если файл не найден
#  pd.errors.EmptyDataError: если файл пуст
#  ValueError: если данные в файле некорректны
