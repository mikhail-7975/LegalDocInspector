# TODO
# add functions for exel table parsing
# input - path to table created using pathlib
# to avoid problems with path in windows
# (for example Path('path', 'to', 'table'))
import logging
import pandas as pd
import re
import json
import datetime
from pathlib import Path

class TableParser:

    def __init__(self):
        self.currency_pattern = r"^-?(?:\d+(\.\d{1,2})?|0)$"
        self.month_year_pattern = r'^(0[1-9]|1[0-2])\.(19|20)\d{2}$'
        self.date_pattern = r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d{2}$"
        self.inn_pattern = r"\b[иИiI][нНnN]{2}\b"
        self.text_month_pattern = r"^(январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]?|июл[ья]?|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])[ ]{1}(?:19|20|21)\d{2}$"
        self.number_pattern = r"№ :"
    def add_entry(self, data, month_year, invoice_amount, oplata, text_month, payments=None):
        """
        Добавляет запись в словарь.

        :param month_year: Ключ в формате "mm.yy".
        :param invoice_amount: Сумма выставленного счёта (float).
        :param payments: Словарь оплат в формате {"dd.mm.yy": float} или None.
        """

        if payments is None:
            payments = 0  # Если оплат нет, устанавливаем значение 0
            data[month_year] = {
            "месяц оплаты": text_month,
            "выставленный счёт": invoice_amount,
            "оплата": oplata,
        }
        else:

            data[month_year] = {
                "месяц оплаты": text_month,
                "выставленный счёт": invoice_amount,
                "оплата": oplata,
                "платежи": payments
            }

    def _find_inn(self, df: pd.DataFrame):
        matches = df[df.iloc[:,3].str.contains(self.inn_pattern, regex=True, na=False)].index.to_list()[0]

        return df.iloc[matches,4]
    
    def _parse_contract_number(self, df: pd.DataFrame):

        matches = df[df.iloc[:,0].str.contains(self.number_pattern, regex=True, na=False)].index.to_list()[0]

        contract_number = df.iloc[matches,1]

        matches = df[df.iloc[:,0].str.contains(r'Дата :', regex=True, na=False)].index.to_list()[0]

        contract_date = df.iloc[matches,1]
        if isinstance(contract_date,datetime.datetime):
            contract_date = contract_date.strftime("%d.%m.%Y")
            
        return contract_number + " от " + contract_date

    
    def parse_excel_table(self, path_to_table:Path):
        """
        input: 
            path_to_table: Путь к справке в формате XLS 
        ...
        output:
            result_dict: Словарь - результат парсинга таблицы
        ...
        """
        df = pd.read_excel(str(path_to_table))
        column_name = 'ККС' # переделать
        target_value = "ИТОГО ПО ДОГОВОРУ"
        result_dict = {}
        inn = self._find_inn(df)
        contract_number = self._parse_contract_number(df)
        result_dict['ИНН'] = inn
        result_dict['номер договора'] = contract_number

        matches = df[df.iloc[:,0].str.contains(self.month_year_pattern, regex=True, na=False)]
        matches = matches.drop_duplicates(subset=matches.columns[0], keep='first')

        row_indexes_to_search = matches.index.to_list()

        
        found_index = df[df[column_name] == target_value].index[0]
        # принты нужно убрать
        # можно кинуть эксепшн
        # можно logging.info и заполнить то что не найдено дефолтными значениями
        # done
        

        for i,start_index in enumerate(row_indexes_to_search):

            if i == len(row_indexes_to_search)-1:
                end_index = found_index

            else:
                end_index = row_indexes_to_search[i+1]

            for row_index in range(start_index+1, end_index):
                month_date = df.iloc[start_index, 0]
                text_month_match_id = df.iloc[:start_index,0].str.contains(self.text_month_pattern, regex=True, na=False).index.to_list()[-1]
                text_month = df.iloc[text_month_match_id,0]
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
                        text_month=text_month,
                        payments=payments_list
                    )
        return result_dict
