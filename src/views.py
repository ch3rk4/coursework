import logging
import os
import time
from datetime import datetime
from typing import List, Literal, TypedDict
from xml.etree import ElementTree

import pandas as pd
import requests
from dotenv import load_dotenv

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


class StockPrice(TypedDict):
    stock: str
    price: float


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


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


load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("API ключ Alpha Vantage не найден в переменных окружения")


def get_stock_prices(input_datetime: datetime) -> List[StockPrice]:
    try:
        stock_of_interest = ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        result = []

        base_url = "https://www.alphavantage.co/query"
        logger.info(f"Начинаем получение цен акций на {input_datetime}")

        for symbol in stock_of_interest:
            try:
                params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHA_VANTAGE_API_KEY}
                logger.debug(f"Запрашиваем данные для {symbol}")

                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                if "Global Quote" not in data:
                    logger.warning(f"Неожиданный формат ответа для {symbol}: {data}")
                    continue

                quote_data = data["Global Quote"]

                if "05. price" not in quote_data:
                    logger.warning(f"Нет данных о цене для {symbol}")
                    continue

                try:
                    price = float(quote_data["05. price"])

                    stock_price: StockPrice = {"stock": str(symbol), "price": float(round(price, 2))}

                    result.append(stock_price)
                    logger.debug(f"Успешно получена цена для {symbol}: {price}")

                except (ValueError, TypeError) as e:
                    logger.error(f"Ошибка преобразования цены для {symbol}: {e}")
                    continue

                time.sleep(0.25)

            except requests.RequestException as e:
                logger.error(f"Ошибка запроса для {symbol}: {e}")
                continue

            if len(result) != len(stock_of_interest):
                missing = set(stock_of_interest) - {s["stock"] for s in result}
                logger.warning(f"Не удалось получить цены для следующих акций: {missing}")

        return result

    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении цен акций: {str(e)}")
        raise


def generate_report(datetime_str: str) -> dict:
    try:
        input_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        report = {
            "greeting": get_greeting(input_datetime),
            "cards": get_card_info(),
            "top_transactions": get_top_transaction(input_datetime),
            "currency_rates": get_currency_rate(input_datetime),
            "stocks_price": get_stock_prices(input_datetime),
        }

        logger.info(
            f"Отчет успешно сформирован для {datetime_str}. "
            f"Получено {len(report['cards'])} карт, "
            f"{len(report['top_transactions'])} транзакций, "
            f"{len(report['currency_rates'])} курсов валют, "
            f"{len(report['stock_prices'])} цен акций."
        )

        return report

    except ValueError as e:
        error_msg = f"Неверный формат даты/времени: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    except FileNotFoundError as e:
        error_msg = f"Не найден файл с данными: {str(e)}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    except Exception as e:
        error_msg = f"Ошибка при формировании отчета: {str(e)}"
        logger.error(error_msg)
        raise
