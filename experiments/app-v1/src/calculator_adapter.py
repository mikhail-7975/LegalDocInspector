"""
Функция переделывает структуру словаря из той, которая возвращается калькулятором, в ту, которую принимает генератор word документов

В Функцию нужно подавать список и словарей-результатов калькуляторов, для каждого договора и соответствующей справки к нему, такой формат
обусловлен тем, что договоров может быть несколько ( обычно 2 )
"""
from uuid import uuid4
import datetime

from StrictFormattedMoney import StrictFormattedMoney
from convert_month import convert_month

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
                    if str_item['type'] == 'debt_accrual':
                        current_accruals_months.append(date)
                    if str_item['type'] == 'correcting':
                        current_correcting_months.append(date)
        
        debt_penalty = debt + penalty
        all_debt+=debt
        all_penalty+=penalty
        cost_of_lawsuit += debt_penalty
        contract_dict['contract_periods'] = f"{current_accruals_months[0]}-{current_accruals_months[-1]}"
        contract_dict['debt'] = str(debt)
        contract_dict['penalty'] = str(penalty)
        contract_dict['debt_penalty'] = str(debt_penalty)

        list_unit.append(contract_dict)
        converted_data['contracts_info'].append(list_unit)

        converted_data['table_info'][contract_info['contract_number']] = {
            "contract_periods": contract_dict['contract_periods'],  
            "debt": contract_dict['debt'], 
            "debt_penalty": contract_dict['debt_penalty'], 
            "penalty": contract_dict['penalty'], 
            "penalty_period": contract_dict['penalty_period'], 
            "last_day": contract_dict['last_day'], 
            "contract_point": contract_dict['contract_point']
        }
    
    converted_data['table_info']['all_debt'] = str(all_debt)
    converted_data['table_info']['all_penalty'] = str(all_penalty)
    converted_data['table_info']['cost_of_lawsuit'] = str(cost_of_lawsuit)
        
    
    
    
    return converted_data


# EXAMPLE OF USAGE

# if __name__ == "__main__":
    
#     # Список результатов penalty calculator calculated_data_list
    
#     calculated_data_list = [ТУТ ДОЛЖНЫ БЫТЬ СПИСКИ ПОСЧИТАННЫХ КАЛЬКУЛЯТОРОМ СПРАВОК]
#     last_days =  [18, 20] # порядок должен соответствовать посчитанным результатам
#     contract_points = ['1.1', '5.5'] # аналогично
#     current_date  = '28.08.2025'
    
#     convert_data(
#         calculated_data_list=calculated_data_list,
#         last_days_of_penalty=last_days,
#         contract_points=contract_points,
#         company_type="ТСЖ",
#         current_date=current_date
#     ) 
    