import json
import logging
import os
from datetime import time
from typing import Dict, List, Union
from xml.etree import ElementTree

import pandas as pd
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


def get_greeting(current_time: time) -> str:
    """Возвращение соответствующего приветствие в зависимости от времени суток"""
    if time(4, 0) <= current_time < time(12, 0):
        return "Доброе утро"
    elif time(12, 0) <= current_time < time(16, 0):
        return "Добрый день"
    elif time(16, 0) <= current_time < time(23, 0):
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def analyze_cards(df: pd.DataFrame) -> List[Dict[str, Union[str, float]]]:
    """Анализ транзакций по картам и расчёт кэшбэка"""
    cards_info = []

    for card_num in df["card"].unique():
        card_df = df[df["card"] == card_num]
        total_spent = sum(abs(amount) for amount in card_df["amount"])

        cashback = round(total_spent / 100, 2)

        cards_info.append(
            {"last_digits": str(card_num)[-4:], "total_spent": round(total_spent, 2), "cashback": cashback}
        )

    return cards_info


def get_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Union[str, float]]]:
    """Получение N наибольших транзакций"""
    if df.empty:
        return []

    df_copy = df.copy()
    df_copy["amount"] = df_copy["amount"].astype(float)

    df_copy["abs_amount"] = df_copy["amount"].abs().astype(float)

    top_df = df_copy.nlargest(n, "abs_amount")

    return [
        {
            "date": row["date"].strftime("%d.%m.%Y"),
            "amount": float(round(row["amount"], 2)),
            "category": row["category"],
            "description": row["description"],
        }
        for _, row in top_df.iterrows()
    ]


def get_currency_rates(currencies: List[str]) -> List[Dict[str, Union[str, float]]]:
    """Получает текущие курсы валют от API Центрального Банка РФ"""
    try:
        # API ЦБ РФ возвращает XML с курсами валют
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        response = requests.get(url)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        rates = []

        for valute in root.findall("Valute"):
            char_code = valute.find("CharCode").text
            if char_code in currencies:
                nominal = float(valute.find("Nominal").text)
                value = float(valute.find("Value").text.replace(",", "."))
                rate = round(value / nominal, 2)
                rates.append({"currency": char_code, "rate": rate})

        return rates

    except requests.RequestException as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        raise
    except (ElementTree.ParseError, AttributeError) as e:
        logger.error(f"Ошибка при разборе ответа от API: {e}")
        raise
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении курсов валют: {e}")
        raise
    except (ElementTree.ParseError, AttributeError) as e:
        logger.error(f"Ошибка при разборе ответа от API: {e}")
        raise


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Union[str, float]]]:
    """Получение текущ цен акций по API"""
    try:
        prices = []
        for stock in stocks:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={stock}&apikey={API_KEY}"
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            if "Global Quote" in data:
                price = float(data["Global Quote"]["05. price"])
                prices.append({"stock": stock, "price": round(price, 2)})

        return prices
    except requests.RequestException as e:
        logger.error(f"Error fetching stock prices: {e}")
        return []


def load_user_settings() -> Dict[str, List[str]]:
    """Загрузка пользовательских настроек из JSON-file"""
    try:
        with open("user_settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("user_settings.json not found")
        return {"user_currencies": [], "user_stocks": []}
