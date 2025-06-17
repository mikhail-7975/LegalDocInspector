import re

def month_year_to_decimal(date_str):
    # Словарь соответствия месяцев их номерам
    months = {
        'Январь': '01', 'Февраль': '02', 'Март': '03',
        'Апрель': '04', 'Май': '05', 'Июнь': '06',
        'Июль': '07', 'Август': '08', 'Сентябрь': '09',
        'Октябрь': '10', 'Ноябрь': '11', 'Декабрь': '12'
    }

    # Проходим по всем месяцам и проверяем, есть ли он в строке
    for month_name, month_num in months.items():
        if month_name in date_str:
            # Ищем год (предполагается, что после месяца идет год)
            year_match = re.search(r'\b\d{4}\b', date_str)
            if year_match:
                year = year_match.group()  # Берём полный год
                return f"{month_num}.{year}"
    
    return None  # Если ничего не найдено