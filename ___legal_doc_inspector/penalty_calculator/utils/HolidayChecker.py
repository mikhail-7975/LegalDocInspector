# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 18:28:25 2025

@author: marin
"""

import json
from datetime import date, timedelta
from pathlib import Path
from workalendar.europe import Russia
import requests

class HolidayChecker:
    def __init__(self, cache_file='holiday_cache.json', offline=False):
        self.calendar = Russia()
        self.cache_file = Path(cache_file)
        self.offline = offline
        self.holidays_cache = self._load_cache()
        
    def _load_cache(self):
        """Загружает кэш праздников из файла или создаёт новый"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """Сохраняет кэш праздников в файл"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.holidays_cache, f, ensure_ascii=False, indent=2)

    def _fetch_online_holidays(self, year):
        """Получает праздники через API (альтернатива workalendar)"""
        try:
            url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/RU"
            response = requests.get(url, timeout=3)
            return [holiday['date'] for holiday in response.json()]
        except requests.RequestException:
            return None

    def _update_holidays(self, year):
        """Обновляет кэш праздников для указанного года"""
        if str(year) in self.holidays_cache:
            return
            
        # Используем workalendar как основной источник
        holidays = []
        for month in range(1, 13):
            month_holidays = self.calendar.holidays(year)[month-1::12]
            holidays.extend([d.strftime('%Y-%m-%d') for d, _ in month_holidays])

        # Пробуем получить дополнительные данные онлайн
        if not self.offline:
            online_holidays = self._fetch_online_holidays(year)
            if online_holidays:
                holidays.extend(online_holidays)

        self.holidays_cache[str(year)] = list(set(holidays))  # Убираем дубли
        self._save_cache()

    def is_holiday_or_weekend(self, check_date):
        """Проверяет, является ли дата праздником или выходным"""
        if not isinstance(check_date, date):
            check_date = date.fromisoformat(check_date) if isinstance(check_date, str) else None
            if not check_date:
                raise ValueError("Некорректный формат даты")

        year = check_date.year
        if str(year) not in self.holidays_cache:
            self._update_holidays(year)

        # Проверяем выходные (суббота/воскресенье)
        if check_date.weekday() >= 5:
            return True

        # Проверяем праздники
        return check_date.isoformat() in self.holidays_cache[str(year)]

    def get_next_workday(self, check_date):
        """Возвращает следующий рабочий день с учётом переносов"""
        delta = timedelta(days=2)
        next_day = check_date + delta
        
        while self.is_holiday_or_weekend(next_day):
            next_day += delta
            
        return next_day

def get_user_date():
    """Функция для ввода даты пользователем"""
    while True:
        date_str = input("Введите дату в формате ДД.ММ.ГГГГ (например, 01.01.2024): ").strip()
        try:
            day, month, year = map(int, date_str.split('.'))
            return date(year, month, day)
        except (ValueError, AttributeError):
            print("Ошибка: введите дату в правильном формате (ДД.ММ.ГГГГ)")

# Пример использования
if __name__ == "__main__":
    # Инициализация (offline=True для работы без интернета)
    checker = HolidayChecker(offline=False)
    
    # Запрос даты у пользователя
    user_date = get_user_date()
    
    # Проверка введенной даты
    status = "выходной/праздник" if checker.is_holiday_or_weekend(user_date) else "рабочий день"
    print(f"\n{user_date.strftime('%d.%m.%Y')}: {status}")
    
    # Если дата выходная, показываем следующий рабочий день
    if checker.is_holiday_or_weekend(user_date):
        next_workday = checker.get_next_workday(user_date)
        print(f"Следующий рабочий день: {next_workday.strftime('%d.%m.%Y')}")