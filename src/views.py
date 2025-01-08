from typing import Dict, List, Union, Optional
import json
import pandas as pd
from datetime import datetime, time
import requests
import logging
from pathlib import Path
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY')


def get_greeting(current_time: time) -> str:
    """
    Return appropriate greeting based on time of day.

    Args:
        current_time: Current time object

    Returns:
        str: Appropriate greeting message
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

    Args:
        df: DataFrame with transaction data

    Returns:
        List of dictionaries containing card analysis
    """
    cards_info = []

    # Group by card number
    for card_num in df['card'].unique():
        card_df = df[df['card'] == card_num]
        # Считаем сумму абсолютных значений всех транзакций
        total_spent = sum(abs(amount) for amount in card_df['amount'])

        # Calculate cashback (1 рубль на 100 рублей)
        cashback = round(total_spent / 100, 2)

        cards_info.append({
            "last_digits": str(card_num)[-4:],
            "total_spent": round(total_spent, 2),
            "cashback": cashback
        })

    return cards_info


def get_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Union[str, float]]]:
    """
    Get top N transactions by amount.

    Args:
        df: DataFrame with transaction data
        n: Number of top transactions to return

    Returns:
        List of dictionaries containing top transactions
    """
    # Проверяем, не пустой ли DataFrame
    if df.empty:
        return []

    # Создаем копию DataFrame и преобразуем столбец amount в float
    df_copy = df.copy()
    df_copy['amount'] = df_copy['amount'].astype(float)

    # Создаем столбец с абсолютными значениями, явно указывая тип float
    df_copy['abs_amount'] = df_copy['amount'].abs().astype(float)

    # Сортируем по абсолютным значениям и берем top N
    top_df = df_copy.nlargest(n, 'abs_amount')

    # Формируем результат
    return [{
        "date": row['date'].strftime('%d.%m.%Y'),
        "amount": float(round(row['amount'], 2)),
        "category": row['category'],
        "description": row['description']
    } for _, row in top_df.iterrows()]


def get_currency_rates(currencies: List[str]) -> List[Dict[str, Union[str, float]]]:
    """
    Fetch current currency rates from API.

    Args:
        currencies: List of currency codes to fetch

    Returns:
        List of dictionaries containing currency rates
    """
    try:
        # Using Exchange Rates API as an example
        base_url = "https://api.exchangerate-api.com/v4/latest/RUB"
        response = requests.get(base_url)
        response.raise_for_status()

        data = response.json()
        rates = []

        for currency in currencies:
            if currency in data['rates']:
                rate = round(1 / data['rates'][currency], 2)  # Convert to RUB
                rates.append({
                    "currency": currency,
                    "rate": rate
                })

        return rates
    except requests.RequestException as e:
        logger.error(f"Error fetching currency rates: {e}")
        return []


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Union[str, float]]]:
    """
    Fetch current stock prices from API.

    Args:
        stocks: List of stock symbols to fetch

    Returns:
        List of dictionaries containing stock prices
    """
    try:
        # Using Alpha Vantage API as an example
        prices = []
        for stock in stocks:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={stock}&apikey={API_KEY}"
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            if "Global Quote" in data:
                price = float(data["Global Quote"]["05. price"])
                prices.append({
                    "stock": stock,
                    "price": round(price, 2)
                })

        return prices
    except requests.RequestException as e:
        logger.error(f"Error fetching stock prices: {e}")
        return []


def load_user_settings() -> Dict[str, List[str]]:
    """
    Load user settings from JSON file.

    Returns:
        Dictionary containing user settings
    """
    try:
        with open('user_settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("user_settings.json not found")
        return {"user_currencies": [], "user_stocks": []}


def get_dashboard_data(datetime_str: str) -> Dict[str, Union[str, List[Dict[str, Union[str, float]]]]]:
    """
    Main function to generate dashboard data.

    Args:
        datetime_str: Input datetime string in format 'YYYY-MM-DD HH:MM:SS'

    Returns:
        Dictionary containing all dashboard data
    """
    try:
        # Parse input datetime
        current_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

        # Load user settings
        settings = load_user_settings()

        # Read and process operations data
        operations_df = pd.read_excel(
            Path('data/operations.xlsx'),
            parse_dates=['date']
        )

        # Filter data for current month
        month_start = current_datetime.replace(day=1, hour=0, minute=0, second=0)
        month_data = operations_df[
            (operations_df['date'] >= month_start) &
            (operations_df['date'] <= current_datetime)
            ]

        # Generate response
        response = {
            "greeting": get_greeting(current_datetime.time()),
            "cards": analyze_cards(month_data),
            "top_transactions": get_top_transactions(month_data),
            "currency_rates": get_currency_rates(settings["user_currencies"]),
            "stock_prices": get_stock_prices(settings["user_stocks"])
        }

        return response

    except Exception as e:
        logger.error(f"Error generating dashboard data: {e}")
        raise