"""
Функция переделывает структуру словаря из той, которая возвращается калькулятором, в ту, которую принимает генератор word документов
"""

def convert_data(calculated_data: dict, contract_number: str):
    converted_data = {}
    converted_data["contract_number"] = contract_number
    converted_data["start_date_of_delay"] = "XXX"
    converted_data["end_date_of_delay"] = "XXX"

    for period in calculated_data.keys():
        pass