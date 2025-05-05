import datetime

from typing import Tuple

from utils.HolidayChecker import HolidayChecker


class Penalty_calculator:
    
    def __init__(self):
        pass
    
    def calculate_penalty_from_doc(data: dict,):
        """
        Принимает результат парсера таблицы, возвращает итоговое пени
        """
        pass
    
    def get_penalty_periods_from_month(self, data: dict, month, current_date: datetime.date):
        """
        Принимает данные за месяц, взятые из парсера таблиц
        возвращает периоды неустойки в формате (дата начала,дата конца,сумма задолженности)
        """
        # TODO:
        # нужно внести проверку на выходной день
        periods = []
        parsed = datetime.datetime.strptime(month, "%m.%Y")
        start_date = datetime.date(parsed.year, parsed.month+1, 19)
        need_to_pay = data[month]['выставленный счёт']
        if data[month]['оплата'] != 0:
                        
            payments_dict = self._sum_payments_by_date(data[month])
            for date, payment in sorted(payments_dict.items()):
                if date < start_date:
                    need_to_pay -= payment
                    continue
                period = (start_date, date, need_to_pay)
                need_to_pay -= payment
                need_to_pay = round(need_to_pay, 2)
                start_date = date+datetime.timedelta(days=1)
                periods.append(period)
        if need_to_pay != 0:
            period = (start_date, current_date, need_to_pay)
            periods.append(period)
        return periods
    
    def _calculate_penalty_by_subperiods(self, period: Tuple[datetime.date, datetime.date, float]):
        """
        Принимает период неустойки, расчитывает сумму пени согласно
        №190-ФЗ "о теплоснабжении" статья 15 пункт 9.3
        """
        pass
    
    def _calculate_penalty_by_standart_method(self, period: Tuple[datetime.date, datetime.date, float]):
        """
        Принимает период неустойки, расчитывает сумма пени согласно
        №190-ФЗ "о теплоснабжении" статья 15 пункт 9.1
        """
        pass
        
    def _sum_payments_by_date(self, data: dict):
        temp_result = {}

        for date_str, amount in data['платежи']:
            # Преобразуем строку в объект date
            date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()

            if date_obj in temp_result:
                temp_result[date_obj] += amount
            else:
                temp_result[date_obj] = amount

        # Убираем записи с нулевой суммой
        final_result = {date_obj: total for date_obj, total in temp_result.items() if total != 0}
        sorted_result = dict(sorted(final_result.items()))
        return sorted_result