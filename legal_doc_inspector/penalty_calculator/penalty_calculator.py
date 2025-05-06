import datetime

from typing import Tuple,Dict

from utils.HolidayChecker import HolidayChecker


class Penalty_calculator:

    def __init__(self):
        pass

    def calculate_penalty_from_doc(data: dict,):
        """
        Принимает результат парсера таблицы, возвращает итоговую сумму неустойи
        """
        pass

    def get_penalty_periods_from_month(self, data: dict, month, company_type, current_date: datetime.date):
        """
        Принимает данные за месяц, взятые из парсера таблиц
        возвращает список периодов неустойки в формате
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """
        # TODO:

        # нужно внести проверку на выходной день
        periods = []
        parsed = datetime.datetime.strptime(month, "%m.%Y")
        start_date = datetime.date(parsed.year, parsed.month+1, 19)  # дефолтная дата начала просрочки без учёта нерабочих дней

        need_to_pay = data[month]['выставленный счёт']
        if company_type == "прочие":

            periods = self._get_penalty_periods_for_type_1(data, month, current_date, need_to_pay, start_date)

        if company_type == "УК":

            periods = self._get_penalty_periods_for_type_2(data, month, current_date, need_to_pay, start_date)

        if company_type == 'ТСЖ':
            
            periods = self._get_penalty_periods_for_type_3(data, month, current_date, need_to_pay, start_date)
        
        return periods

    def _get_penalty_periods_for_type_1(self,data: dict, month, current_date: datetime.date, need_to_pay,start_date):

        periods = None

        if need_to_pay != 0:
            periods = []

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


    def _get_penalty_periods_for_type_2(self, data: dict, month, current_date: datetime.date, need_to_pay, start_date):

        periods = None

        if need_to_pay != 0:

            periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay , type_of_split= 'УК')

            if data[month]['оплата'] != 0:

                payments_dict = self._sum_payments_by_date(data[month])
                for date, payment in sorted(payments_dict.items()):

                    # т к сначала всё равно идут наиболее ранние даты которые могут быть ещё до долга, вычитаем из долга, обновляем периоды
                    if date < start_date:
                        need_to_pay -= payment
                        periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay, type_of_split= 'УК')
                        continue

                    # эта часть кода работает когда уже идут долговые погашения
                    new_periods = periods.copy()
                    for i, period in enumerate(periods):
                        lb = period['start']
                        ub = period['end']

                        if lb <= date <= ub:
                            splitted_periods, need_to_pay = self._split_stage_by_date(period, date, payment)

                            new_periods = new_periods[:i] + splitted_periods + new_periods[i+1:]
                            # обновляем долг для всех следующих периодов
                            for next_period in new_periods[i+1:]:
                                next_period['debt'] = need_to_pay

                            periods = new_periods

        return periods

    def _get_penalty_periods_for_type_3(self, data: dict, month, current_date: datetime.date, need_to_pay, start_date):

        periods = None

        if need_to_pay != 0:

            periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay , type_of_split='ТСЖ')

            if data[month]['оплата'] != 0:

                payments_dict = self._sum_payments_by_date(data[month])
                for date, payment in sorted(payments_dict.items()):

                    # т к сначала всё равно идут наиболее ранние даты которые могут быть ещё до долга, вычитаем из долга, обновляем периоды
                    if date < start_date:
                        need_to_pay -= payment
                        periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay, type_of_split='ТСЖ')
                        continue

                    # эта часть кода работает когда уже идут долговые погашения
                    new_periods = periods.copy()
                    for i, period in enumerate(periods):
                        lb = period['start']
                        ub = period['end']

                        if lb <= date <= ub:
                            splitted_periods, need_to_pay = self._split_stage_by_date(period, date, payment)

                            new_periods = new_periods[:i] + splitted_periods + new_periods[i+1:]
                            # обновляем долг для всех следующих периодов
                            for next_period in new_periods[i+1:]:
                                next_period['debt'] = need_to_pay

                            periods = new_periods

        return periods

    def _split_period_by_stages(self, period: Tuple[datetime.date, datetime.date], debt: float, type_of_split):
        start_date, end_date = period
        result = []
        if type_of_split == 'УК':  # 60/30/+inf
            stage1_start = start_date
            stage1_end = min(start_date + datetime.timedelta(days=59), end_date)
            stage1_days = (stage1_end - stage1_start).days + 1

            if stage1_days > 0:

                result.append({
                    "start": stage1_start,
                    "end": stage1_end,
                    "days": stage1_days,
                    "debt": debt,
                    "rate": 1/300
                    })

            current_start = stage1_end + datetime.timedelta(days=1)

            stage2_end = min(current_start + datetime.timedelta(days=29), end_date)
            if current_start <= end_date:
                stage2_days = (stage2_end - current_start).days + 1
                result.append({
                    "start": current_start,
                    "end": stage2_end,
                    "days": stage2_days,
                    "debt": debt,
                    "rate": 1/170
                    })
                current_start = stage2_end + datetime.timedelta(days=1)
            else:
                return result

            if current_start <= end_date:
                stage3_days = (end_date - current_start).days + 1
                result.append({
                    "start": current_start,
                    "end": end_date,
                    "days": stage3_days,
                    "debt": debt,
                    "stage": 1/130
                })

        if type_of_split == 'ТСЖ':  # 30/60/+inf
            stage1_start = start_date
            stage1_end = min(start_date + datetime.timedelta(days=29), end_date)
            stage1_days = (stage1_end - stage1_start).days + 1

            if stage1_days > 0:

                result.append({
                    "start": stage1_start,
                    "end": stage1_end,
                    "days": stage1_days,
                    "debt":debt,
                    "rate": 0
                    })

            current_start = stage1_end + datetime.timedelta(days=1)


            stage2_end = min(current_start + datetime.timedelta(days=59), end_date)
            if current_start <= end_date:
                stage2_days = (stage2_end - current_start).days + 1
                result.append({
                    "start": current_start,
                    "end": stage2_end,
                    "days": stage2_days,
                    "debt":debt,
                    "rate": 1/300
                    })
                current_start = stage2_end + datetime.timedelta(days=1)
            else:
                return result


            if current_start <= end_date:
                stage3_days = (end_date - current_start).days + 1
                result.append({
                    "start": current_start,
                    "end": end_date,
                    "days": stage3_days,
                    "debt":debt,
                    "stage": 1/130
                })




        return result

    def _split_stage_by_date(self, stage: Dict[str, datetime.date | int | float], split_date: datetime.date, split_payment):
        """
        Делит один этап на два подэтапа по заданной дате.

        :param stage: исходный этап с ключами 'start', 'end', 'days', 'rate'
        :param split_date: дата, по которую делится этап (включительно в первый подэтап)
        :return: список из одного или двух подэтапов
        """
        stage_start = stage["start"]
        stage_end = stage["end"]
        original_rate = stage.get("rate", None)
        original_debt = stage.get('debt', 0)
        if split_date < stage_start or split_date > stage_end:
            raise ValueError("Split date is outside the stage period.")

        # Первый подэтап: от начала до split_date включительно
        substage1_start = stage_start
        substage1_end = split_date
        substage1_days = (substage1_end - substage1_start).days + 1

        substage1 = {
            "start": substage1_start,
            "end": substage1_end,
            "days": substage1_days,
            "debt": original_debt,
            "rate": original_rate
        }

        # Второй подэтап: от следующего дня после split_date до конца этапа
        substage2_start = split_date + datetime.timedelta(days=1)
        substage2_end = stage_end

        substage2_days = (substage2_end - substage2_start).days + 1

        result = [substage1]

        if substage2_days > 0:
            result.append({
                "start": substage2_start,
                "end": substage2_end,
                "days": substage2_days,
                "debt": original_debt - split_payment,
                "rate": original_rate
            })

        return result, original_debt - split_payment

    def _calculate_penalty_to_manager_company(self, period: Tuple[datetime.date, datetime.date, float]):
        """
        Принимает период неустойки, расчитывает сумму пени согласно
        №190-ФЗ "о теплоснабжении" статья 15 пункт 9.3 (Управляющие компании)
        """

        pass

    def _calculate_penalty_to_tsj(self, period: Tuple[datetime.date, datetime.date, float]):
        """
        Принимает период неустойки, расчитывает сумму пени согласно
        №190-ФЗ "о теплоснабжении" статья 15 пункт 9.2 (ТСЖ ЖСК)
        """
        pass

    def _calculate_penalty_by_standart_method(self, period: Tuple[datetime.date, datetime.date, float]):
        """
        Принимает период неустойки, расчитывает сумма пени согласно
        №190-ФЗ "о теплоснабжении" статья 15 пункт 9.1 (Прочие потребители)
        """
        cb_keyrate = self._get_key_rate()
        start_date, end_date, amount = period
        days_count = (end_date - start_date + datetime.timedelta(days=1)).days
        base_rate = 1/130
        return days_count * amount * base_rate * cb_keyrate

    def _check_start_time_for_period(self, date: datetime.date):
        """
        принимает дату, проверяет, является ли день рабочим
        в случае если день не рабочий , то возвращает второй рабочий день после него
        """

    def _get_cb_key_rate(self):
        """
        возвращает текущую ставку рефинансирования цб рф
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
