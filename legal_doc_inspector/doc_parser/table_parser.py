# TODO
# add functions for exel table parsing
# input - path to table created using pathlib
# to avoid problems with path in windows
# (for example Path('path', 'to', 'table'))
import logging
import pandas as pd
import re
import json
from pathlib import Path

def parse_excel_table(path_to_table:Path):
    df = pd.read_excel(str(path_to_table))
    column_name = 'ККС' # переделать
    target_value = "ИТОГО ПО ДОГОВОРУ"
    currency_pattern = r"^(?:\d+\.\d{2}|0)$"
    list_vystavleny_schet = []
    list_oplata = []
    month_year_pattern = r'^(0[1-9]|1[0-2])\.(19|20)\d{2}$'

    matches = df[df.iloc[:,0].str.contains(month_year_pattern, regex=True, na=False)]
    row_indexes_to_search = matches.index.to_list()

    try:
        found_index = df[df[column_name] == target_value].index[0]
        print(f"Значение '{target_value}' найдено в строке с индексом: {found_index}")
    except IndexError:
        print(f"Значение '{target_value}' не найдено.")

    for i,start_index in enumerate(row_indexes_to_search):

        if i == len(row_indexes_to_search)-1:
            end_index = found_index
        
        else:
            end_index = row_indexes_to_search[i+1]
        
        for row_index in range(start_index+1,end_index):
            vystavleny_schet = df.iloc[row_index,1]
            oplata = df.iloc[row_index,3]
            
            if re.match(currency_pattern, str(vystavleny_schet)) and re.match(currency_pattern,str(oplata)):
                # print(f"Найдены валютные значения '{vystavleny_schet}, {oplata}' на строке {row_index}")
                list_vystavleny_schet.append(vystavleny_schet)
                list_oplata.append(oplata)

        result_dict = {
        key: {"Выставленный счёт": val1, "оплата": val2}
        for key, val1, val2 in zip(matches.iloc[:,0].tolist(), list_vystavleny_schet, list_oplata)
        }

    file_path = "output.json"  # Укажите путь к файлу

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(result_dict, json_file, indent=4, ensure_ascii=False)
    logging.debug('json с данными справки успешно сохранён')
    