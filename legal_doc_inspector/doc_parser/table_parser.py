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

class TableParser:
    
    def __init__(self):
        self.currency_pattern = r"^-?(?:\d+(\.\d{1,2})?|0)$"
        self.month_year_pattern = r'^(0[1-9]|1[0-2])\.(19|20)\d{2}$'
        self.date_pattern = r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d{2}$"
    
    
    def add_entry(self, data, month_year, invoice_amount, oplata,payments=None):
        """
        Добавляет запись в словарь.

        :param month_year: Ключ в формате "mm.yy".
        :param invoice_amount: Сумма выставленного счёта (float).
        :param payments: Словарь оплат в формате {"dd.mm.yy": float} или None.
        """
        
        if payments is None:
            payments = 0  # Если оплат нет, устанавливаем значение 0
            data[month_year] = {
            "выставленный счёт": invoice_amount,
            "оплата": oplata
        }
        else:
            
            data[month_year] = {
                "выставленный счёт": invoice_amount,
                "оплата": oplata,
                "платежи": payments
            }
    
    def parse_excel_table(self, path_to_table:Path,path_to_save:Path):
        df = pd.read_excel(str(path_to_table))
        column_name = 'ККС' # переделать
        target_value = "ИТОГО ПО ДОГОВОРУ"
        result_dict = {}
        
        
        
        
        matches = df[df.iloc[:,0].str.contains(self.month_year_pattern, regex=True, na=False)]
        matches = matches.drop_duplicates(subset=matches.columns[0], keep='first')

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
            
            for row_index in range(start_index+1, end_index):
                month_date = df.iloc[start_index, 0]
                vystavleny_schet = df.iloc[row_index, 1]
                oplata = df.iloc[row_index, 3]
                
                    
                if re.match(self.currency_pattern, str(vystavleny_schet)) and re.match(self.currency_pattern, str(oplata)):
                    # print(f"Найдены валютные значения '{vystavleny_schet}, {oplata}' на строке {row_index}")
                    payments_list = None
                    if int(oplata) > 0:
                        # ищем все платежи с датами
                        payments_list = []
                         
                        for row_index_2 in range(start_index+1,row_index):
                            if re.match(self.date_pattern, str(df.iloc[row_index_2, 2])) and re.match(self.currency_pattern, str(df.iloc[row_index_2, 3])):
                                
                                payments_list.append((str(df.iloc[row_index_2, 2]),df.iloc[row_index_2, 3])) 
                    
                    self.add_entry(
                        data=result_dict,
                        month_year=month_date,
                        invoice_amount=vystavleny_schet,
                        oplata=oplata,
                        payments=payments_list
                    )
                      
        file_path = path_to_save  

        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(result_dict, json_file, indent=4, ensure_ascii=False)
        logging.debug('json с данными справки успешно сохранён')
        
        return result_dict