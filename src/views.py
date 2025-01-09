import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd

from src.utils import (analyze_cards, get_currency_rates, get_greeting, get_stock_prices, get_top_transactions,
                       load_user_settings)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_dashboard_data(datetime_str: str) -> Dict[str, Union[str, List[Dict[str, Union[str, float]]]]]:
    """Генерация данных панели мониторинга"""
    try:
        current_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        settings = load_user_settings()
        operations_df = pd.read_excel(Path("data/operations.xlsx"), parse_dates=["Дата платежа"])

        month_start = current_datetime.replace(day=1, hour=0, minute=0, second=0)
        month_data = operations_df[
            (operations_df["Дата платежа"] >= month_start) & (operations_df["Дата платежа"] <= current_datetime)
        ]

        response = {
            "greeting": get_greeting(current_datetime.time()),
            "cards": analyze_cards(month_data),
            "top_transactions": get_top_transactions(month_data),
            "currency_rates": get_currency_rates(settings["user_currencies"]),
            "stock_prices": get_stock_prices(settings["user_stocks"]),
        }

        return response

    except Exception as e:
        logger.error(f"Error generating dashboard data: {e}")
        raise
