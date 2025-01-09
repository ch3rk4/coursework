import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def save_report(filename: Optional[str] = None) -> Callable:
    """Декоратор для сохранения результатов отчета в файл"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            try:
                reports_dir = Path("reports")
                reports_dir.mkdir(exist_ok=True)

                if filename is None:
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_name = f"{func.__name__}_{current_time}.json"
                else:
                    report_name = filename if filename.endswith(".json") else f"{filename}.json"

                file_path = reports_dir / report_name

                if isinstance(result, pd.DataFrame):
                    data_to_save = result.to_dict("records")
                else:
                    data_to_save = result

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

                logger.info(f"Отчет сохранен в файл: {file_path}")

            except Exception as e:
                logger.error(f"Ошибка при сохранении отчета: {str(e)}")
                raise

            return result

        return wrapper

    return decorator


@save_report()
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """Анализирует траты по заданной категории за последние три месяца"""
    try:
        if date is None:
            target_date = datetime.now()
        else:
            target_date = datetime.strptime(date, "%Y-%m-%d")

        three_months_ago = target_date - timedelta(days=90)

        if not pd.api.types.is_datetime64_any_dtype(transactions["date"]):
            transactions["date"] = pd.to_datetime(transactions["date"])

        filtered_df = transactions[
            (transactions["date"] >= three_months_ago)
            & (transactions["date"] <= target_date)
            & (transactions["category"] == category)
        ].copy()

        filtered_df = filtered_df.sort_values("date")

        filtered_df["amount"] = filtered_df["amount"].round(2)

        filtered_df["date"] = filtered_df["date"].dt.strftime("%Y-%m-%d")

        return filtered_df[["date", "category", "amount", "description"]]

    except Exception as e:
        logger.error(f"Ошибка при формировании отчета по категории: {str(e)}")
        raise
