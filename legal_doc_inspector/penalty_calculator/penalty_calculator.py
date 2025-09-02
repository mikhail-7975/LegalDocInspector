import datetime
import requests
import re

from xml.etree import ElementTree as ET
from typing import Tuple,Dict


class Penalty_calculator:

    def __init__(self):
        self.path_to_data = None
        self.cb_key_rate = 9.5 / 100
        # self.cb_key_rate = self._get_cb_rate()
        pass

    def calculate_penalty_from_doc(self, data: dict, company_type, current_date: datetime.date, day_of_penalty:int):
        """
        Принимает результат парсера таблицы,
        для каждого месяца считает пени за каждый подпериод
        суммирует пени
        возвращает список периодов с расчётами
        """
        penalty = []  # сумма пеней по всем задолженностям
        # перебираем каждый месяц
        month_pattern = r'^(0[1-9]|1[0-2])\.(20\d{2}|2100)$'
        for month in data.keys():

            if re.match(month_pattern, month):

                periods = self._get_penalty_periods_for_month(data=data,
                                                              month=month,
                                                              company_type=company_type,
                                                              current_date=current_date,
                                                              day_of_penalty=day_of_penalty
                                                              )

                for period in periods:

                    period_with_calculated_penalty = self._calculate_penalty_for_period(period=period)
                    # print(period_with_calculated_penalty)
                    penalty.append(period_with_calculated_penalty)

            else:
                continue

        return penalty





    def calculate_penalty_and_create_table(self, data: dict):
        """
        Принимает результат парсера таблицы, возвращает итоговую сумму неустойки
        строит docx таблицу с расчётом
        """

    def _get_penalty_periods_for_month(self, data: dict, month:str, company_type, current_date: datetime.date, day_of_penalty:int):
        """
        Принимает данные за месяц, взятые из парсера таблиц
        возвращает список периодов неустойки в формате
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """

        periods = []
        parsed = datetime.datetime.strptime(month, "%m.%Y")
        next_month = parsed.month+1 if parsed.month != 12 else 1
        next_year = parsed.year if parsed.month != 12 else parsed.year+1
        start_date = datetime.date(next_year, next_month, int(day_of_penalty))  # дефолтная дата окончания договора без учёта нерабочих дней
        start_date = self._get_start_date(start_date) # дата начала просрочки с учётом того что договор может истечь в нерабочий день

        need_to_pay = data[month]['выставленный счёт']
        if company_type == "Прочие":

            periods = self._get_penalty_periods_for_type_1(data, month, current_date, need_to_pay, start_date)

        if company_type == "УК":

            periods = self._get_penalty_periods_for_type_2(data, month, current_date, need_to_pay, start_date)

        if company_type == 'ТСЖ':

            periods = self._get_penalty_periods_for_type_3(data, month, current_date, need_to_pay, start_date)

        return periods

    def _get_penalty_periods_for_type_1(self, data: dict, month, current_date: datetime.date, need_to_pay,start_date):
        """
        возвращает список периодов нейстойки для прочих потребителей в формате :
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """
        periods = None
        payments_dict = None

        payment_month = (data[month]['месяц оплаты'])
        if need_to_pay != 0:

            periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay , type_of_split= 'Прочие')

            if data[month]['оплата'] != 0:

                payments_dict = self._sum_payments_by_date(data[month])
                for date, payment in sorted(payments_dict.items()):

                    # т к сначала всё равно идут наиболее ранние даты которые могут быть ещё до долга, вычитаем из долга, обновляем периоды
                    if date < start_date:
                        need_to_pay -= payment
                        periods = self._split_period_by_stages(period=(start_date, current_date), debt=need_to_pay, type_of_split= 'Прочие')
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
        for period in periods:
            period['month'] = payment_month
            period['payments'] = payments_dict if payments_dict is not None else None
        return periods


    def _get_penalty_periods_for_type_2(self, data: dict, month, current_date: datetime.date, need_to_pay, start_date):
        """
        возвращает список периодов нейстойки для  управляющих компаний в формате :
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """
        periods = None
        payments_dict = None

        payment_month = (data[month]['месяц оплаты'])

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
        for period in periods:
            period['month'] = payment_month
            period['payments'] = payments_dict if payments_dict is not None else None

        return periods

    def _get_penalty_periods_for_type_3(self, data: dict, month, current_date: datetime.date, need_to_pay, start_date):
        """
        возвращает список периодов нейстойки для ТСЖ\ЖСК в формате :
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """
        periods = None
        payments_dict = None
        payment_month = (data[month]['месяц оплаты'])

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
        for period in periods:
            period['month'] = payment_month    
            period['payments'] = payments_dict if payments_dict is not None else None

        return periods

    def _split_period_by_stages(self, period: Tuple[datetime.date, datetime.date], debt: float, type_of_split):
        """
        возвращает список подпериодов нейстойки для потребителей в формате :
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}
        """

        start_date, end_date = period
        result = []

        match type_of_split:

            case "УК":
                # 60/30/+inf
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
                        "rate": 1/130
                    })

            case "ТСЖ":
                # 30/60/+inf
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
                        "rate": 1/130
                    })

            case "Прочие":
                # +inf
                stage1_start = start_date
                stage1_end = end_date
                stage1_days = (stage1_end - stage1_start).days + 1
                result.append({
                        "start": stage1_start,
                        "end": stage1_end,
                        "days": stage1_days,
                        "debt":debt,
                        "rate": 1/130
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

    def _calculate_penalty_for_period(self, period: dict):
        """
        Принимает период в формате:
        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки}

        Возвращает словарь в формате:

        {'start': datetime.date - дата начала периода,
        'end': datetime.date - дата конца периода,
        'days': int - количество дней,
        'debt': float - сумма долга,
        'rate': float - доля ставки,
        'penalty': float - подсчитанная неустойка}
        """
        debt = period['debt']
        rate = period['rate']
        count_days = period['days']

        period['penalty'] = round(debt * count_days * rate * self.cb_key_rate, 2)

        return period


    def _get_cb_rate(self):
        # URL сервиса
        url = "http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"

        # Заголовки запроса
        headers = {
            "Host": "www.cbr.ru",
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"http://web.cbr.ru/KeyRate"'
        }

        # Тело SOAP-запроса (вставьте нужные даты)
        today = datetime.datetime.now() - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        from_date = today.strftime("%Y-%m-%dT00:00:00")
        to_date = tomorrow.strftime("%Y-%m-%dT00:00:00")

        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                        xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
            <KeyRate xmlns="http://web.cbr.ru/">
                <fromDate>{from_date}</fromDate>
                <ToDate>{to_date}</ToDate>
            </KeyRate>
            </soap:Body>
        </soap:Envelope>
        """

        # Отправка POST-запроса
        response = requests.post(url, data=body, headers=headers)

        # Вывод ответа
        root = ET.fromstring(response.text)

        ns = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'cbr': 'http://web.cbr.ru/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
            'msdata': 'urn:schemas-microsoft-com:xml-msdata'
        }

        kr_records = root.findall('.//KR', ns)

        for record in kr_records:
            dt_elem = record.find('DT', ns)
            rate_elem = record.find('Rate', ns)

            if dt_elem is not None and rate_elem is not None:
                dt_str = dt_elem.text.split('+')[0]  # убираем часовой пояс
                rate = rate_elem.text

        if rate and dt_str:
            return datetime.datetime.fromisoformat(dt_str), (float(rate)/100)
        else:
            return None, None

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

    def _is_holiday(self, day: datetime.date):

        url = f"https://isdayoff.ru/{day.strftime('%Y%m%d')}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            day_type = int(response.text)

            # 0 - рабочий, 1 - выходной, 2 - праздник
            return day_type in (1, 2)
        except Exception as e:
            # print(e)
            return False

    def _get_start_date(self, day: datetime.date):

        if not self._is_holiday(day):
            return day + datetime.timedelta(days=1)

        if self._is_holiday(day):
            while self._is_holiday(day):
                day = day + datetime.timedelta(days=1)

            return day + datetime.timedelta(days=1)
