from TableParser import TableParser
import datetime
import requests

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

def _get_penalty_periods(start_date:datetime.datetime, end_date:datetime.datetime, debt:float, type_of_split:str):
    result = []
    match type_of_split:

            case "УК":
                # 60/30/+inf
                stage1_start = start_date
                stage1_end = min(start_date + datetime.timedelta(days=59), end_date)
                stage1_days = (stage1_end - stage1_start).days + 1

                if stage1_days > 0:

                    result.append({
                        "debt": debt,
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage1_days, 9.5 / 100, 1/300),
                        'text': None
                        })

                current_start = stage1_end + datetime.timedelta(days=1)

                stage2_end = min(current_start + datetime.timedelta(days=29), end_date)
                if current_start <= end_date:
                    stage2_days = (stage2_end - current_start).days + 1
                    result.append({
                        "debt": debt,
                        'period': (current_start.strftime("%d.%m.%Y"), stage2_end.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage2_days, 9.5 / 100, 1/170),
                        'text': None
                        })
                    current_start = stage2_end + datetime.timedelta(days=1)
                else:
                    return result

                if current_start <= end_date:
                    stage3_days = (end_date - current_start).days + 1
                    result.append({
                        "debt": debt,
                        'period': (current_start.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage3_days, 9.5 / 100, 1/130),
                        'text': None
                    })

            case "ТСЖ":
                # 30/60/+inf
                stage1_start = start_date
                stage1_end = min(start_date + datetime.timedelta(days=29), end_date)
                stage1_days = (stage1_end - stage1_start).days + 1

                if stage1_days > 0:

                    result.append({
                        "debt": debt,
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage1_days, 9.5 / 100, 0),
                        'text': None
                        })

                current_start = stage1_end + datetime.timedelta(days=1)


                stage2_end = min(current_start + datetime.timedelta(days=59), end_date)
                if current_start <= end_date:
                    stage2_days = (stage2_end - current_start).days + 1
                    result.append({
                        "debt": debt,
                        'period': (current_start.strftime("%d.%m.%Y"), stage2_end.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage2_days, 9.5 / 100, 1/300),
                        'text': None
                        })
                    current_start = stage2_end + datetime.timedelta(days=1)
                else:
                    return result


                if current_start <= end_date:
                    stage3_days = (end_date - current_start).days + 1
                    result.append({
                        "debt": debt,
                        'period': (current_start.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage3_days, 9.5 / 100, 1/130),
                        'text': None
                    })

            case "Прочие":
                # +inf
                stage1_start = start_date
                stage1_end = end_date
                stage1_days = (stage1_end - stage1_start).days + 1
                result.append({
                        "debt": debt,
                        'period': (stage1_start.strftime("%d.%m.%Y"), stage1_end.strftime("%d.%m.%Y")),
                        'type': 'penalty_period',
                        'penalty_period_info': (stage1_days, 9.5 / 100, 1/130),
                        'text': None
                    })

    return result

def _split_stage_by_date(stage:dict, split_date: datetime.datetime, split_payments:list[dict]):
        """
        Делит один этап на два подэтапа по заданной дате.

        :param stage: исходный этап с ключами 'start', 'end', 'days', 'rate'
        :param split_date: дата, по которую делится этап (включительно в первый подэтап)
        :return: список из одного или двух подэтапов
        """
        stage_start, stage_end = stage['period']
        stage_start, stage_end = datetime.datetime.strptime(stage_start, '%d.%m.%Y'), datetime.datetime.strptime(stage_end, '%d.%m.%Y')
        
        _, _ , original_rate = stage['penalty_period_info']
        original_debt = stage.get('debt', 0)
        if split_date < stage_start or split_date > stage_end:
            raise ValueError("Split date is outside the stage period.")

        # Первый подэтап: от начала до split_date включительно
        substage1_start = stage_start
        substage1_end = split_date
        substage1_days = (substage1_end - substage1_start).days + 1

        substage1 = {
            'debt': original_debt,
            'period': (substage1_start.strftime("%d.%m.%Y"), substage1_end.strftime("%d.%m.%Y")),
            'type': 'penalty_period',
            'penalty_period_info': (substage1_days, 0.095, original_rate),
            'text':None
        }

        # Второй подэтап: от следующего дня после split_date до конца этапа
        substage2_start = split_date + datetime.timedelta(days=1)
        substage2_end = stage_end

        substage2_days = (substage2_end - substage2_start).days + 1
        result = [substage1]
        all_split_payment = 0
        for payment in split_payments:
            split_payment  = payment['payment']
            all_split_payment += split_payment
            payment_stage = {
                'debt': -1*split_payment,
                'period': (split_date.strftime("%d.%m.%Y"), None),
                'penalty_period_info': None,
                'type': 'payment_after_penalty',
                'text': 'Погашение части долга'
            }
            
            result.append(payment_stage)

        if substage2_days > 0:
            result.append({
                'debt': original_debt - all_split_payment,
                'period': (substage2_start.strftime("%d.%m.%Y"), substage2_end.strftime("%d.%m.%Y")),
                'penalty_period_info': (substage2_days, 0.095, original_rate),
                'type': 'penalty_period',
                'text':None
            })

        return result, original_debt - all_split_payment
    

def calculate_penalty(parsed_data:dict, day_of_penalty:int, company_type:str, end_date:str) -> dict:
    end_date = datetime.datetime.strptime(end_date, "%d.%m.%Y")    
    res = dict()
    for month_name, month_parsed_info in parsed_data.items():
        res[month_name] = list()
        month_debt = 0 
        
        #расчёты даты начала просрочки
        month = month_parsed_info['accrual']['accruals'][0]['period']
        parsed = datetime.datetime.strptime(month, "%m.%Y")
        next_month = parsed.month+1 if parsed.month != 12 else 1
        next_year = parsed.year if parsed.month != 12 else parsed.year+1
        start_date = datetime.datetime(next_year, next_month, int(day_of_penalty))  # дефолтная дата окончания договора без учёта нерабочих дней
        start_date = _get_start_date(start_date) # дата начала периода просрочки
        
        # добавление полей, не являющихся периодами пени
        for accrual_or_adjustment, parsed_info in month_parsed_info.items():
            
            if accrual_or_adjustment == 'accrual':
                text = f"Начисленно за период {parsed_info['accruals'][0]['period']}"
            if accrual_or_adjustment == 'adjustment':
                text = f"Годовая корректировка обязательств"
            # обработка выставленных счетов
            if len(parsed_info['accruals'])>0:
                for accrual in parsed_info['accruals']:
                    month_debt+=accrual['accrual']
                    res[month_name].append({
                        'debt': accrual['accrual'],
                        'period': (_add_last_day_of_month(accrual['period']), None),
                        'type': 'debt_accrual',
                        'penalty_period_info': None,
                        'text': text
                    })
            # обработка корректировок
            if len(parsed_info['additionals'])>0:
                all_additional = 0
                period = _add_last_day_of_month(month_parsed_info['accrual']['accruals'][0]['period'])
                text = f"Доля от годовой корректировки {parsed_info['additionals'][0]['period'].split('.')[-1]} за период {month}"
                for additional in parsed_info['additionals']:
                    all_additional+=additional['accrual']
                month_debt+=all_additional
                res[month_name].append({
                    'debt':all_additional,
                    'period':(period, None),
                    'type': 'correcting',
                    'penalty_period_info': None,
                    'text': text
                })
            #предварительный расчёт периодов пени без учёта погашений
            
        periods = _get_penalty_periods(start_date, end_date, month_debt, company_type)
                
        for payment_info in [month_parsed_info['accrual']['payments'], month_parsed_info['adjustment']['payments']]:
            
            if len(payment_info)>0:
                for payment in payment_info:
                    # обработка погашений долга до периодов пени
                    if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') < start_date :
                        month_debt-=payment['payment']
                        res[month_name].append({
                            'debt': -1*payment['payment'],
                            'period':(payment['date'], None),
                            'type': "payment_before_penalty" if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') < start_date else "payment_after_penalty",
                            'penalty_period_info': None,
                            'text': "Погашение части долга"
                        })
                        # обновляем периуды пени с учётом погашений
                        for period in periods:
                            period['debt'] = month_debt
                            
                new_periods = periods.copy()
                seen_dates = []
                # обработка погашений долга во время периода пени (дробление подпериодов)
                for payment in payment_info:
                    if datetime.datetime.strptime(payment['date'], '%d.%m.%Y') >= start_date and payment['date'] not in seen_dates :
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
                        for i, period in enumerate(periods):
                            if period['type'] == 'penalty_period':
                                lb, ub  = period['period']
                                lb, ub = datetime.datetime.strptime(lb, '%d.%m.%Y'), datetime.datetime.strptime(ub, '%d.%m.%Y')
                                if split_date >= lb and split_date <= ub:
                                    splitted_periods, new_month_debt = _split_stage_by_date(period, split_date, split_payments)
                                    new_periods = periods[:i] + splitted_periods + periods[i+1:]
                                    # обновляем месячные долги у слудующих периодов
                                    for next_period in new_periods[i+1:]:
                                        if next_period['type'] == 'penalty_period':
                                            next_period['debt'] = new_month_debt

                                    periods = new_periods
            
        
        # учёт выплат во время периода пени
        
        
        res[month_name]+= periods
    return res

# USAGE EXAMPLE

if __name__ == "__main__":
    parser = TableParser()
    parser.open('/home/kirill/neurolumber/docscanner/new_legal_doc_inspector/docinspecor/legal_doc_data/test_data/1/комплект 1/Документы для иска/04.303360-ТЭ/04.303360-ТЭ_справка.XLSM')
    data = parser.parse()
    parser.close()
    day_of_penalty = 20
    company_type = 'ТСЖ'
    end_date = '27.08.2025'
    res = calculate_penalty(
        parsed_data= data,
        day_of_penalty=day_of_penalty,
        company_type=company_type,
        end_date=end_date
    )
    print(res)
