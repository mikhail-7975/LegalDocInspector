"""
Функция переделывает структуру словаря из той, которая возвращается калькулятором, в ту, которую принимает генератор word документов

В Функцию нужно подавать список и словарей-результатов калькуляторов, для каждого договора и соответствующей справки к нему, такой формат
обусловлен тем, что договоров может быть несколько ( обычно 2 )
"""
from uuid import uuid4
import re

import datetime
from dateutil.relativedelta import relativedelta

from LegalDocInspector.legal_doc_inspector.utils.strict_formatted_money import StrictFormattedMoney
from LegalDocInspector.legal_doc_inspector.utils.convert_month import convert_month


def group_consecutive_months(dates_list):
    # Преобразуем строки в объекты datetime и сортируем
    date_objects = []
    for date_str in dates_list:
        month, year = map(int, date_str.split('.'))
        date_objects.append(datetime.datetime(year, month, 1))
    
    date_objects.sort()
    
    # Группируем последовательные даты
    groups = []
    current_group = []
    
    for i, date in enumerate(date_objects):
        if not current_group:
            current_group.append(date)
        else:
            # Проверяем, является ли текущая дата следующей за предыдущей
            prev_date = date_objects[i-1]
            expected_next_date = prev_date + relativedelta(months=1)
            
            if date == expected_next_date:
                current_group.append(date)
            else:
                groups.append(current_group)
                current_group = [date]
    
    if current_group:
        groups.append(current_group)
    
    # Форматируем результат
    result_parts = []
    
    for group in groups:
        if len(group) == 1:
            # Одиночная дата
            result_parts.append(group[0].strftime('%m.%Y'))
        else:
            # Диапазон дат
            start_date = group[0]
            end_date = group[-1]
            result_parts.append(f"{start_date.strftime('%m.%Y')}-{end_date.strftime('%m.%Y')}")
    
    return ', '.join(result_parts)


def convert_data(calculated_data_list: list[dict], last_days_of_penalty: list[int | str], contract_points:list[str], company_type:str, current_date:str) -> dict:
    converted_data = {}
    all_debt = StrictFormattedMoney(0)
    all_penalty = StrictFormattedMoney(0)
    cost_of_lawsuit = StrictFormattedMoney(0)
    current_date = datetime.datetime.strptime(current_date, "%d.%m.%Y").strftime("%Y-%m-%d")
    converted_data["company_type"] = company_type
    converted_data["current_date"] = current_date
    converted_data["contracts_info"] = []
    converted_data['table_info'] = {}
    id = uuid4()
    for i, contract_info in enumerate(calculated_data_list):
        current_accruals_months = []
        current_correcting_months = []
        list_unit = []
        contract_dict = {}
        list_unit.append(str(id))
        list_unit.append(contract_info['contract_number'])
        contract_dict['correcting_year'] = None
        contract_dict['contract_point'] = contract_points[i]
        contract_dict['last_day'] = f"До {last_days_of_penalty[i]} числа месяца, следующего за расчётным"
        for month_or_type, str_info in contract_info.items():
            if month_or_type == 'start_of_table':
                start_date, end_date = str_info['start'], str_info['end']
                contract_dict['penalty_period'] = f"{start_date} по {end_date}"
            elif month_or_type == 'end_of_table1':
                debt = StrictFormattedMoney(str_info['money'])
            elif month_or_type == 'end_of_table2':
                penalty = StrictFormattedMoney(str_info['money'])
            elif month_or_type == "contract_number":
                continue
            elif month_or_type == 'debt_info':
                contract_dict['accrual_debt'] = str_info['accrual_debt']
                contract_dict['correcting_debt'] = str_info['correcting_debt']
            else:
                month, year = month_or_type.split(' ')
                month = convert_month(month)
                date = f"{month}.{year}"
                for str_item in str_info:
                    if str_item['type'] == 'debt_info':
                        if (str_item['accrual_debt']) != "0,00":
                            current_accruals_months.append(date)
                        if (str_item['correcting_debt']) != "0,00":
                            current_correcting_months.append(date)
                    if str_item['type'] == 'correcting':
                        matched = re.search(r'\b(19|20)\d{2}\b', str_item['text'])
                        if matched:
                            contract_dict['correcting_year'] = matched.group()

        debt_penalty = debt + penalty
        all_debt+=debt
        all_penalty+=penalty
        cost_of_lawsuit += debt_penalty
        contract_dict['contract_periods'] = group_consecutive_months(current_accruals_months)
        contract_dict['contract_periods_correcting'] = group_consecutive_months(current_correcting_months)
        contract_dict['debt'] = str(debt)
        contract_dict['penalty'] = str(penalty)
        contract_dict['debt_penalty'] = str(debt_penalty)

        list_unit.append(contract_dict)
        converted_data['contracts_info'].append(list_unit)

        converted_data['table_info'][contract_info['contract_number']] = {
            "contract_periods": contract_dict['contract_periods'],
            "contract_periods_correcting": contract_dict['contract_periods_correcting'],
            "debt": contract_dict['debt'],
            "debt_penalty": contract_dict['debt_penalty'],
            "penalty": contract_dict['penalty'],
            "penalty_period": contract_dict['penalty_period'],
            "last_day": contract_dict['last_day'],
            "contract_point": contract_dict['contract_point'],
            "accrual_debt": contract_dict['accrual_debt'],
            "correcting_debt": contract_dict['correcting_debt'],

        }
    converted_data['table_info']['all_debt'] = str(all_debt)
    converted_data['table_info']['all_penalty'] = str(all_penalty)
    converted_data['table_info']['cost_of_lawsuit'] = str(cost_of_lawsuit)

    # converted_data["contract_types_templates"] = get_templates_of_smt(converted_data["contracts_info"], converted_data["company_type"], )

    return converted_data



# def get_templates_of_smt(contracts, company_type: str, service_type: str):
#     """
#     Это вспомогательная функция. Она нужна чтобы определить, какой иск генерировать. 
#     Сейчас есть три вида: ТЭ, ГВС и ТЭ + ГВС. В зависимости от этого, используются 
#     разные шаблоны абзацев.
#     """
#     templates = dict()

#     contruct_types = []
#     if "ГВС" in service_type:
#         contruct_types.append("ГВС")
#     if "ТЭ" in service_type:
#         contruct_types.append("ТЭ")
#     # for contract in contracts:
#     #     contract_number = contract[1].split(" ")[1]

#     #     if contract_number.endswith("ГВС"):
#     #         if "ГВС" not in contruct_types:
#     #             contruct_types.append("ГВС")

#     #     elif contract_number.endswith("ТЭ"):
#     #         if "ТЭ" not in contruct_types:
#     #             contruct_types.append("ТЭ")

#     if len(contracts) == 1:
#         templates["supplied_resources4"] = "ТЭ"
#         templates["plural_template_1"] = "Договором"
#         templates["plural_template_2"] = "Договору"
#         templates["plural_template_3"] = "названном Договоре"
#         templates["plural_template_4"] = "Договора"
#         templates["plural_template_5"] = "указанного Договора"
#         templates["plural_template_6"] = "названному Договору"

#     elif len(contracts) > 1:
#         templates["plural_template_1"] = "Договорами"
#         templates["plural_template_2"] = "Договорам"
#         templates["plural_template_3"] = "названных Договорах"
#         templates["plural_template_4"] = "Договоров"
#         templates["plural_template_5"] = "указанных Договоров"
#         templates["plural_template_6"] = "названным Договорам"


#     templates["types_of_significant_paragraph"] = []
#     # Выбираем нужные шаблоны
#     if ("ГВС" in contruct_types) and ("ТЭ" in contruct_types):
#         templates["supplied_resources"] = "тепловой энергии и/или теплоносителя (далее – ТЭ), горячей воды через присоединенные сети горячего водоснабжения (далее – ГВС)"
#         templates["contract_type"] = "тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС)"
#         # templates["contract_type2"] = "тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС)"
#         templates["supplied_resources2"] = "тепловой энергии/теплоносителя, горячей воды"
#         templates["supplied_resources3"] = "тепловую энергию/теплоноситель, горячую воду"
#         templates["supplied_resources4"] = "ТЭ и ГВС"
#         templates["types_of_significant_paragraph"].append(company_type + "ТЭ")
#         templates["types_of_significant_paragraph"].append(company_type + "ГВС")
#         templates["service_article"] = "ст. 15 Федерального закона от 27.07.2010 № 190-ФЗ «О теплоснабжении», ст. 13 Федерального закона от 07.12.2011 № 416-ФЗ «О водоснабжении и водоотведении»"
        

#     elif "ТЭ" in contruct_types:
#         templates["supplied_resources"] = "тепловой энергии и/или теплоносителя (далее – ТЭ)"
#         templates["contract_type"] = "тепловую энергию/теплоноситель (ТЭ)"
#         # templates["contract_type2"] = "тепловую энергию/теплоноситель (ТЭ)"
#         templates["supplied_resources2"] = "тепловой энергии/теплоносителя"
#         templates["supplied_resources3"] = "тепловую энергию/теплоноситель"
#         templates["supplied_resources4"] = "ТЭ"
#         templates["types_of_significant_paragraph"].append(company_type + "ТЭ")
#         templates["service_article"] = "ст. 15 Федерального закона от 27.07.2010 № 190-ФЗ «О теплоснабжении»"

#     elif "ГВС" in contruct_types:
#         templates["supplied_resources"] = "горячей воды через присоединенные сети горячего водоснабжения (далее – ГВС)"
#         templates["contract_type"] = "горячую воду (ГВС)"
#         # templates["contract_type2"] = "горячую воду (ГВС)"
#         templates["supplied_resources2"] = "горячей воды"
#         templates["supplied_resources3"] = "горячую воду"
#         templates["supplied_resources4"] = "ГВС"
#         templates["types_of_significant_paragraph"].append(company_type + "ГВС")
#         templates["service_article"] = "ст. 13 Федерального закона от 07.12.2011 № 416-ФЗ «О водоснабжении и водоотведении»"

#     return templates


