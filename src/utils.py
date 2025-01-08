import json
import logging
import os
from datetime import time
from typing import Dict, List, Union

import pandas as pd
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


def get_greeting(current_time: time) -> str:
    """
    Return appropriate greeting based on time of day.
    """
    if time(4, 0) <= current_time < time(12, 0):
        return "Доброе утро"
    elif time(12, 0) <= current_time < time(16, 0):
        return "Добрый день"
    elif time(16, 0) <= current_time < time(23, 0):
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def analyze_cards(df: pd.DataFrame) -> List[Dict[str, Union[str, float]]]:
    """
    Analyze card transactions and calculate totals and cashback.
    """
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
    """
    Get top N transactions by amount.
    """
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
    """
    Fetch current currency rates from API.
    """
    try:
        base_url = "https://api.exchangerate-api.com/v4/latest/RUB"
        response = requests.get(base_url)
        response.raise_for_status()

        data = response.json()
        rates = []

        for currency in currencies:
            if currency in data["rates"]:
                rate = round(1 / data["rates"][currency], 2)
                rates.append({"currency": currency, "rate": rate})

        return rates
    except requests.RequestException as e:
        logger.error(f"Error fetching currency rates: {e}")
        return []


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Union[str, float]]]:
    """
    Fetch current stock prices from API.
    """
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
    """
    Load user settings from JSON file.
    """
    try:
        with open("user_settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("user_settings.json not found")
        return {"user_currencies": [], "user_stocks": []}
