from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser
import datetime
import requests
from decimal import Decimal, ROUND_HALF_UP
# from calculator_adapter import convert_data

class StrictFormattedMoney:
    def __init__(self, amount, currency='RUB'):
        # Всегда преобразуем к Decimal с 2 знаками после запятой
        if not isinstance(amount, (Decimal, StrictFormattedMoney, str)):
            amount = Decimal(str(amount))
        if isinstance(amount, str):
            amount = amount.replace(' ', '')
            amount = amount.replace(',','.')
            if 'руб.' in amount:
                amount = amount.replace('руб.', '')
            # print(amount)
            self.amount = Decimal(str(amount))
            self.currency = currency
        if isinstance(amount, StrictFormattedMoney):
            self.amount = amount.amount
            self.currency = amount.currency
        if isinstance(amount, Decimal):
            self.amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.currency = currency

    def __str__(self):
        return self.format()

    def format(self, decimal_separator=',', thousands_separator=' '):
        """Форматирование суммы с правильной обработкой отрицательных чисел"""
        amount_str = str(self.amount)

        # Проверяем, отрицательное ли число
        is_negative = amount_str.startswith('-')
        if is_negative:
            amount_str = amount_str[1:]  # Убираем минус для обработки

        # Разделяем целую и дробную части
        if '.' in amount_str:
            integer_part, decimal_part = amount_str.split('.')
        else:
            integer_part, decimal_part = amount_str, '00'

        # Добиваем дробную часть до 2 знаков
        decimal_part = decimal_part.ljust(2, '0')[:2]

        # Добавляем разделители тысяч
        formatted_integer = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = thousands_separator + formatted_integer
            formatted_integer = digit + formatted_integer

        # Добавляем минус обратно без пробела
        if is_negative:
            formatted_integer = '-' + formatted_integer

        return f"{formatted_integer}{decimal_separator}{decimal_part}"

    def __add__(self, other):
        if not isinstance(other, StrictFormattedMoney):
            raise TypeError("Можно складывать только с StrictFormattedMoney")
        if self.currency != other.currency:
            raise ValueError("Валюты должны совпадать")

        return StrictFormattedMoney(self.amount + other.amount, self.currency)

    def __sub__(self, other):
        if not isinstance(other, StrictFormattedMoney):
            raise TypeError("Можно вычитать только StrictFormattedMoney")
        if self.currency != other.currency:
            raise ValueError("Валюты должны совпадать")

        return StrictFormattedMoney(self.amount - other.amount, self.currency)

    def __mul__(self, multiplier):
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Можно умножать только на число")

        return StrictFormattedMoney(self.amount * Decimal(str(multiplier)), self.currency)

    def __truediv__(self, divisor):
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Можно делить только на число")

        return StrictFormattedMoney(self.amount / Decimal(str(divisor)), self.currency)

def sort_dict_by_months(data_dict):
    """
    Сортирует словарь по месяцам в хронологическом порядке
    """
    # Словарь для преобразования русских названий месяцев
    month_order = {
        'Январь': 1, 'Февраль': 2, 'Март': 3, 'Апрель': 4, 'Май': 5, 'Июнь': 6,
        'Июль': 7, 'Август': 8, 'Сентябрь': 9, 'Октябрь': 10, 'Ноябрь': 11, 'Декабрь': 12
    }
    
    def get_sort_key(month_year):
        """
        Извлекает ключ для сортировки из строки "Месяц Год"
        """
        try:
            month_name, year = month_year.split()
            month_num = month_order.get(month_name, 0)
            return (int(year), month_num)
        except (ValueError, AttributeError):
            return (0, 0)
    
    # Сортируем ключи словаря
    sorted_keys = sorted(data_dict.keys(), key=get_sort_key)
    
    # Создаем новый упорядоченный словарь
    sorted_dict = {key: data_dict[key] for key in sorted_keys}
    
    return sorted_dict

def _add_last_day_of_month(date_str):
    """
    Альтернативная версия без использования calendar
    """
    try:
        month, year = map(int, date_str.split('.'))

        # Вычисляем первый день следующего месяца и вычитаем 1 день
        if month == 12:
            next_month = datetime.date(year + 1, 1, 1)
        else:
            next_month = datetime.date(year, month + 1, 1)

        last_day = next_month - datetime.timedelta(days=1)

        return last_day.strftime('%d.%m.%Y')

    except (ValueError, IndexError):
        return "Неверный формат даты"


def _get_start_date(day: datetime.date):

        if not _is_holiday(day):
            return day + datetime.timedelta(days=1)

        if _is_holiday(day):
            while _is_holiday(day):
                day = day + datetime.timedelta(days=1)

            return day + datetime.timedelta(days=1)

def _is_holiday(day: datetime.date):

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

def _get_dec_float(simple_float:str):
    if simple_float=='0':
        return 0.0, 1.0
    denominator, separator = map(float, simple_float.split('/'))
    return denominator, separator

def _get_penalty_periods(start_date:datetime.datetime, end_date:datetime.datetime, debt:StrictFormattedMoney, type_of_split:str):
    result = []
    match type_of_split:

            case "УК":
                # 60/30/+inf
                stage1_start = start_date
                stage1_end = min(start_date + datetime.timedelta(days=59), end_date)
                stage1_days = (stage1_end - stage1_start).days + 1

                if stage1_days > 0:

                    result.append({
                        "debt": str(debt),
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y"), stage1_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "1/300"),
                        'text': None,
                        })

                current_start = stage1_end + datetime.timedelta(days=1)

                stage2_end = min(current_start + datetime.timedelta(days=29), end_date)
                if current_start <= end_date:
                    stage2_days = (stage2_end - current_start).days + 1

                    result.append({
                        "debt": str(debt),
                        'period': (current_start.strftime("%d.%m.%Y"), stage2_end.strftime("%d.%m.%Y"), stage2_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "1/170"),
                        'text': None,
                        })
                    current_start = stage2_end + datetime.timedelta(days=1)
                else:
                    return result

                if current_start <= end_date:
                    stage3_days = (end_date - current_start).days + 1

                    result.append({
                        "debt": str(debt),
                        'period': (current_start.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y"), stage3_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "1/130"),
                        'text': None,
                    })

            case "ТСЖ":
                # 30/60/+inf
                stage1_start = start_date
                stage1_end = min(start_date + datetime.timedelta(days=29), end_date)
                stage1_days = (stage1_end - stage1_start).days + 1

                if stage1_days > 0:
                    result.append({
                        "debt": str(debt),
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y"), stage1_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "0"),
                        'text': None,
                        })

                current_start = stage1_end + datetime.timedelta(days=1)


                stage2_end = min(current_start + datetime.timedelta(days=59), end_date)
                if current_start <= end_date:
                    stage2_days = (stage2_end - current_start).days + 1

                    result.append({
                        "debt": str(debt),
                        'period': (current_start.strftime("%d.%m.%Y"), stage2_end.strftime("%d.%m.%Y"), stage2_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "1/300"),
                        'text': None,
                        })
                    current_start = stage2_end + datetime.timedelta(days=1)
                else:
                    return result


                if current_start <= end_date:
                    stage3_days = (end_date - current_start).days + 1

                    result.append({
                        "debt": str(debt),
                        'period': (current_start.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y"), stage3_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9,5 %", "1/130"),
                        'text': None,
                    })

            case "Прочие":
                # +inf
                stage1_start = start_date
                stage1_end = end_date
                stage1_days = (stage1_end - stage1_start).days + 1

                result.append({
                        "debt": str(debt),
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y"), stage1_days),
                        'type': 'penalty_period',
                        'penalty_period_info': ("9.5 %", "1/130"),
                        'text': None,
                    })

    return result

def _calculate_penalty_for_each_period(periods:list[dict]) -> tuple[list[dict], StrictFormattedMoney, StrictFormattedMoney]:
    result_penalty = StrictFormattedMoney(0)
    result_debt = StrictFormattedMoney(0)
    for period in periods:
        if period['type'] == 'penalty_period':
            debt = StrictFormattedMoney(period['debt'])
            _, _, days_count = period['period']
            rate, share = period['penalty_period_info']

            denominator, separator = _get_dec_float(share)

            penalty = debt * Decimal(days_count) * (Decimal(str(denominator)) / Decimal(str(separator))) * Decimal("0.095")
            period['penalty'] = str(penalty)
            period['formulae'] = f"{str(debt)} × {str(days_count)} × {share} × 9,5%"
            result_penalty += penalty
    result_debt += debt
    return periods, result_penalty, result_debt

def _split_stage_by_date(stage:dict, split_date: datetime.datetime, split_payments:list[dict]):
        """
        Делит один этап на два подэтапа по заданной дате.

        :param stage: исходный этап с ключами 'start', 'end', 'days', 'rate'
        :param split_date: дата, по которую делится этап (включительно в первый подэтап)
        :return: список из одного или двух подэтапов
        """
        stage_start, stage_end, _ = stage['period']
        stage_start, stage_end = datetime.datetime.strptime(stage_start, '%d.%m.%Y'), datetime.datetime.strptime(stage_end, '%d.%m.%Y')

        _ , original_rate = stage['penalty_period_info']
        original_debt = stage.get('debt', StrictFormattedMoney(0))
        if split_date < stage_start or split_date > stage_end:
            raise ValueError("Split date is outside the stage period.")

        # Первый подэтап: от начала до split_date включительно
        substage1_start = stage_start
        substage1_end = split_date
        substage1_days = (substage1_end - substage1_start).days + 1


        substage1 = {
            'debt': str(original_debt),
            'period': (substage1_start.strftime("%d.%m.%Y"), substage1_end.strftime("%d.%m.%Y"), substage1_days),
            'type': 'penalty_period',
            'penalty_period_info': ("9,5 %", original_rate),
            'text':None,
        }

        # Второй подэтап: от следующего дня после split_date до конца этапа
        substage2_start = split_date + datetime.timedelta(days=1)
        substage2_end = stage_end

        substage2_days = (substage2_end - substage2_start).days + 1
        result = [substage1]
        all_split_payment = StrictFormattedMoney(0)
        for payment in split_payments:
            split_payment  = StrictFormattedMoney(payment['payment'])
            all_split_payment += split_payment
            payment_stage = {
                'debt': str(split_payment * -1),
                'period': (split_date.strftime("%d.%m.%Y"), None, None),
                'penalty_period_info': None,
                'type': 'payment_after_penalty',
                'text': 'Погашение части долга',
            }

            result.append(payment_stage)

        if substage2_days > 0:
            result.append({
                'debt': str(StrictFormattedMoney(original_debt) - all_split_payment),
                'period': (substage2_start.strftime("%d.%m.%Y"), substage2_end.strftime("%d.%m.%Y"), substage2_days),
                'penalty_period_info': ("9,5 %", original_rate),
                'type': 'penalty_period',
                'text':None,
            })

        return result, str(StrictFormattedMoney(original_debt) - all_split_payment), all_split_payment

def _check_month_for_four_party(month_parsed_info:dict):
    for payment in month_parsed_info['accrual']['payments']:
        if payment['contract_type'] in [1960, 1961]:
            return True
    return False


def _split_stage_by_date_correcting(stage:dict, split_date: datetime.datetime, split_payment:StrictFormattedMoney):
        """
        Делит один этап на два подэтапа по заданной дате.

        :param stage: исходный этап с ключами 'start', 'end', 'days', 'rate'
        :param split_date: дата, по которую делится этап (включительно в первый подэтап)
        :return: список из одного или двух подэтапов
        """
        stage_start, stage_end, _ = stage['period']
        stage_start, stage_end = datetime.datetime.strptime(stage_start, '%d.%m.%Y'), datetime.datetime.strptime(stage_end, '%d.%m.%Y')

        _ , original_rate = stage['penalty_period_info']
        original_debt = stage.get('debt', StrictFormattedMoney(0))
        if split_date < stage_start or split_date > stage_end:
            raise ValueError("Split date is outside the stage period.")

        # Первый подэтап: от начала до split_date включительно
        substage1_start = stage_start
        substage1_end = split_date
        substage1_days = (substage1_end - substage1_start).days + 1

        # print(original_debt)
        # print(split_payment)

        substage1 = {
            'debt': str(original_debt),
            'period': (substage1_start.strftime("%d.%m.%Y"), substage1_end.strftime("%d.%m.%Y"), substage1_days),
            'type': 'penalty_period',
            'penalty_period_info': ("9,5 %", original_rate),
            'text':None,
        }

        # Второй подэтап: от следующего дня после split_date до конца этапа
        substage2_start = split_date + datetime.timedelta(days=1)
        substage2_end = stage_end

        substage2_days = (substage2_end - substage2_start).days + 1
        result = [substage1]


        payment_stage = {
            'debt': str(split_payment),
            'period': (split_date.strftime("%d.%m.%Y"), None, None),
            'penalty_period_info': None,
            'type': 'correcting',
            'text': 'Годовая корректировка обязательств',
        }

        result.append(payment_stage)
        new_debt = StrictFormattedMoney(original_debt) + StrictFormattedMoney(split_payment)
        if substage2_days > 0:
            result.append({
                'debt': str(original_debt),
                'period': (substage2_start.strftime("%d.%m.%Y"), substage2_end.strftime("%d.%m.%Y"), substage2_days),
                'penalty_period_info': ("9,5 %", original_rate),
                'type': 'penalty_period',
                'text':None,
            })


        return result, str(new_debt)


def calculate_penalty(parsed_data:dict, day_of_penalty:int, company_type:str, end_date:str) -> dict:
    all_penalty = StrictFormattedMoney(0)
    all_debt = StrictFormattedMoney(0)
    all_accrual_debt = StrictFormattedMoney(0)
    all_correcting_debt = StrictFormattedMoney(0)
    end_date = datetime.datetime.strptime(end_date, "%d.%m.%Y")
    
    parsed_data = sort_dict_by_months(parsed_data)
    
    res = {
        'start_of_table' : {}
    }

    start_date_flag = False
    for month_name, month_parsed_info in parsed_data.items():
        is_four_party = _check_month_for_four_party(month_parsed_info)
        print(is_four_party)
        res[month_name] = list()
        month_debt = StrictFormattedMoney(0)
        month_accrual = StrictFormattedMoney(0)
        month_correcting = StrictFormattedMoney(0)
        #расчёты даты начала просрочки
        month = month_parsed_info['accrual']['accruals'][0]['period']
        parsed = datetime.datetime.strptime(month, "%m.%Y")
        next_month = parsed.month+1 if parsed.month != 12 else 1
        next_year = parsed.year if parsed.month != 12 else parsed.year+1
        start_date = datetime.datetime(next_year, next_month, int(day_of_penalty))  # дефолтная дата окончания договора без учёта нерабочих дней
        start_date = _get_start_date(start_date) # дата начала периода просрочки
        if not start_date_flag:
            res['start_of_table'] = {
                'text1': 'Начало просрочки',
                'text2': 'Конец просрочки',
                'start': start_date.strftime('%d.%m.%Y'),
                'end': end_date.strftime('%d.%m.%Y')
            }
            start_date_flag = True
        # добавление полей, не являющихся периодами пени
        for accrual_or_adjustment, parsed_info in month_parsed_info.items():

            if accrual_or_adjustment == 'accrual':
                text = f"Начислено за период {parsed_info['accruals'][0]['period']}"
            if accrual_or_adjustment == 'adjustment':
                text = f"Годовая корректировка обязательств"
            # обработка выставленных счетов
            if len(parsed_info['accruals'])>0:
                for accrual in parsed_info['accruals']:
                    month_debt+= StrictFormattedMoney(accrual['accrual'])
                    if accrual_or_adjustment == 'accrual':
                        month_accrual += StrictFormattedMoney(accrual['accrual'])
                    else:
                        month_correcting += StrictFormattedMoney(accrual['accrual'])
                res[month_name].append({
                    'debt': str(month_accrual),
                    'period': (_add_last_day_of_month(accrual['period']), None, None),
                    'type': 'debt_accrual',
                    'penalty_period_info': None,
                    'text': text
                })
            # обработка доли годовой корректировки
            if accrual_or_adjustment == 'adjustment':
                if len(parsed_info['additionals'])>0:
                    all_additional = StrictFormattedMoney(0)
                    period = _add_last_day_of_month(month_parsed_info['accrual']['accruals'][0]['period'])
                    text = f"Доля от годовой корректировки {parsed_info['additionals'][0]['period'].split('.')[-1]} за период {month}"
                    for additional in parsed_info['additionals']:
                        all_additional+=StrictFormattedMoney(additional['accrual'])
                    month_debt+=all_additional
                    month_correcting+=all_additional
                    res[month_name].append({
                        'debt':str(all_additional),
                        'period':(period, None, None),
                        'type': 'correcting',
                        'penalty_period_info': None,
                        'text': text
                    })


            #предварительный расчёт периодов пени без учёта погашений
        
        
        periods = _get_penalty_periods(start_date, end_date, month_debt, company_type)

        print(month_parsed_info)
        print(month_name)
        if not is_four_party:
            for i ,payment_info in enumerate([month_parsed_info['accrual']['payments'], month_parsed_info['adjustment']['payments']]):
                
                if len(payment_info)>0:
                    for payment in payment_info:
                        # обработка погашений долга до периодов пени
                        if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') < start_date :
                            print(payment)
                            
                            month_debt-=StrictFormattedMoney(payment['payment'])
                            if i == 0:
                                month_accrual-=StrictFormattedMoney(payment['payment'])
                            else:
                                month_correcting-=StrictFormattedMoney(payment['payment'])
                            
                            res[month_name].append({
                                'debt': str(StrictFormattedMoney(payment['payment'])*-1),
                                'period':(payment['date'], None, None),
                                'type': "payment_before_penalty" if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') < start_date else "payment_after_penalty",
                                'penalty_period_info': None,
                                'text': "Погашение части долга"
                            })
                            # обновляем периуды пени с учётом погашений
                            for period in periods:
                                period['debt'] = str(month_debt)

                        new_periods = periods.copy()
                        seen_dates = []
                        # обработка погашений долга во время периода пени (дробление подпериодов)
                        

                    for payment in payment_info:
                        if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') >= start_date and payment['date'] not in seen_dates :
                            print(payment)
                            split_date = datetime.datetime.strptime(payment['date'], '%d.%m.%Y')
                            # split_payment = payment['payment']
                            split_payments = []
                            # split_payments.append(payment)
                            seen_dates.append(payment['date'])
                            # находим оплаты которые были в тот же день если они есть
                            for another_payment in payment_info:
                                if datetime.datetime.strptime(another_payment['date'], '%d.%m.%Y') == split_date:
                                    split_payments.append(another_payment)
                            # находим нужный подпериод по дате
                            for j, period in enumerate(periods):
                                if period['type'] == 'penalty_period':
                                    lb, ub, _  = period['period']
                                    lb, ub = datetime.datetime.strptime(lb, '%d.%m.%Y'), datetime.datetime.strptime(ub, '%d.%m.%Y')
                                    if split_date >= lb and split_date <= ub:
                                        splitted_periods, new_month_debt, all_split_payment = _split_stage_by_date(period, split_date, split_payments)
                                        if i ==0:
                                            month_accrual -= all_split_payment
                                        else :
                                            month_correcting -= all_split_payment
                                        new_periods = periods[:j] + splitted_periods + periods[j+1:]
                                        # обновляем месячные долги у слудующих периодов
                                        for next_period in new_periods[j+1:]:
                                            if next_period['type'] == 'penalty_period':
                                                next_period['debt'] = new_month_debt

                                        periods = new_periods
        
        else:
            all_payments = StrictFormattedMoney(0)
            for i ,payment_info in enumerate([month_parsed_info['accrual']['payments'], month_parsed_info['adjustment']['payments']]):
                for payment in payment_info:
                    if i == 0: 
                        month_accrual -= StrictFormattedMoney(payment['payment'])
                    else:
                        month_correcting -= StrictFormattedMoney(payment['payment'])
                    all_payments += StrictFormattedMoney(payment['payment'])
                    # print(payment)
            periods = _get_penalty_periods(start_date, end_date, month_accrual+month_correcting, company_type)
            payment_1 = {
                'debt': str(all_payments * -1),
                'period': (start_date.strftime("%d.%m.%Y"), None, None),
                'penalty_period_info': None,
                'type': 'payment_after_penalty',
                'text': 'Погашение части долга',
            }
            periods = [payment_1] + periods[0:]
        # обработка годовых корректировок
        for accrual_or_adjustment, parsed_info in month_parsed_info.items():
            if accrual_or_adjustment == 'accrual':
                if len(parsed_info['additionals'])>0:
                    text = f"Годовая корректировка обязательств"
                    new_periods = periods.copy()
                    for additional in parsed_info['additionals']:
                        debt = StrictFormattedMoney(additional['accrual'])
                        period = _add_last_day_of_month(additional['period'])
                        periods_elem = dict()
                        periods_elem['type'] = 'correcting'
                        periods_elem['text'] = text
                        periods_elem['period'] = (period, None, None)
                        periods_elem['penalty_periods_info'] = None
                        periods_elem['debt'] = str(debt)

                        correcting_date = datetime.datetime.strptime(period, '%d.%m.%Y')
                        flag = False
                        for i, penalty_period in enumerate(periods):
                            lb, ub, _  = penalty_period['period']
                            if ub is not None:
                                lb, ub = datetime.datetime.strptime(lb, '%d.%m.%Y'), datetime.datetime.strptime(ub, '%d.%m.%Y')
                                
                                if correcting_date >= lb and correcting_date <= ub:
                                    splitted_periods, new_month_debt = _split_stage_by_date_correcting(penalty_period, correcting_date, debt)
                                    
                                    new_periods = periods[:i] + splitted_periods  + periods[i+1:]
                                    flag = True
                                    for next_period in new_periods[i+1:]:
                                        if next_period['type'] == 'penalty_period':
                                            print(next_period)
                                            next_period['debt'] = str(StrictFormattedMoney(next_period['debt']) + debt)
                        if not flag:
                            payment_stage = {
                                'debt': str(debt),
                                'period': (correcting_date.strftime("%d.%m.%Y"), None , None),
                                'penalty_period_info': None,
                                'type': 'correcting',
                                'text': 'Годовая корректировка обязательств',
                            }
                            new_periods = [payment_stage] + periods
                            for next_period in new_periods[1:]:
                                    if next_period['type'] == 'penalty_period':
                                        next_period['debt'] = str(StrictFormattedMoney(next_period['debt']) + debt)
                        periods = new_periods
                        month_accrual += debt

        if str(month_accrual+month_correcting) == "0,00" :

            del res[month_name]
            continue
        
        
        
        periods, result_penalty, result_debt = _calculate_penalty_for_each_period(periods)
        res[month_name]+= periods
        res[month_name].append({
            'text': "Итого:",
            'type': 'field',
            'penalty': str(result_penalty)
        })

        all_penalty+=result_penalty
        all_debt+= month_correcting + month_accrual

        res[month_name].append({
            'text': None,
            'type': 'debt_info',
            'accrual_debt': str(month_accrual),
            'correcting_debt': str(month_correcting)
        })

        all_accrual_debt+=month_accrual
        all_correcting_debt+=month_correcting

    res['end_of_table1'] = {
        'text': "Сумма Основного долга",
        'money': str(all_debt),
        'type': 'field'
    }

    res['end_of_table2'] = {
        'text': "Сумма пеней по всем задолженностям",
        'money': str(all_penalty),
        'type': 'field'
    }

    res['debt_info'] = {
        'text': None,
        'type': 'debt_info',
        'accrual_debt': str(all_accrual_debt),
        'correcting_debt': str(all_correcting_debt)
    }


    return res
