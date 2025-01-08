from typing import Optional, Callable, Any
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from functools import wraps

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_report(filename: Optional[str] = None) -> Callable:
    """
    Декоратор для сохранения результатов отчета в файл.

    Args:
        filename: Опциональное имя файла для сохранения отчета.
                 Если не указано, генерируется автоматически.

    Returns:
        Callable: Декорированная функция
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Получаем результат работы функции
            result = func(*args, **kwargs)

            try:
                # Создаем директорию для отчетов, если она не существует
                reports_dir = Path('reports')
                reports_dir.mkdir(exist_ok=True)

                # Формируем имя файла
                if filename is None:
                    # Если имя файла не указано, генерируем его автоматически
                    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                    report_name = f"{func.__name__}_{current_time}.json"
                else:
                    report_name = filename if filename.endswith('.json') else f"{filename}.json"

                file_path = reports_dir / report_name

                # Преобразуем DataFrame в список словарей для JSON
                if isinstance(result, pd.DataFrame):
                    data_to_save = result.to_dict('records')
                else:
                    data_to_save = result

                # Сохраняем результат в JSON файл
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)

                logger.info(f"Отчет сохранен в файл: {file_path}")

            except Exception as e:
                logger.error(f"Ошибка при сохранении отчета: {str(e)}")
                raise

            return result

        return wrapper

    return decorator


@save_report()
def spending_by_category(
        transactions: pd.DataFrame,
        category: str,
        date: Optional[str] = None
) -> pd.DataFrame:
    """
    Анализирует траты по заданной категории за последние три месяца.

    Args:
        transactions: DataFrame с транзакциями
        category: Название категории
        date: Опциональная дата в формате 'YYYY-MM-DD'

    Returns:
        DataFrame с тратами по категории
    """
    try:
        # Если дата не указана, используем текущую
        if date is None:
            target_date = datetime.now()
        else:
            target_date = datetime.strptime(date, '%Y-%m-%d')

        # Рассчитываем дату три месяца назад
        three_months_ago = target_date - timedelta(days=90)

        # Преобразуем столбец с датой в datetime, если это еще не сделано
        if not pd.api.types.is_datetime64_any_dtype(transactions['date']):
            transactions['date'] = pd.to_datetime(transactions['date'])

        # Фильтруем транзакции по дате и категории
        filtered_df = transactions[
            (transactions['date'] >= three_months_ago) &
            (transactions['date'] <= target_date) &
            (transactions['category'] == category)
            ].copy()

        # Если нет данных, возвращаем пустой DataFrame с нужной структурой
        if filtered_df.empty:
            return pd.DataFrame(columns=['date', 'category', 'amount', 'description'])

        # Сортируем по дате
        filtered_df = filtered_df.sort_values('date')

        # Округляем суммы до 2 знаков после запятой
        filtered_df['amount'] = filtered_df['amount'].round(2)

        # Преобразуем даты в строковый формат для JSON
        filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d')

        return filtered_df[['date', 'category', 'amount', 'description']]

    except Exception as e:
        logger.error(f"Ошибка при формировании отчета по категории: {str(e)}")
        raise