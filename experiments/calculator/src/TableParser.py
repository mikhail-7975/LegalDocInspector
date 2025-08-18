"""
Класс TableParser реализует интерфейс взаимодействия с excel документом. TableParser работает только на чтение!
"""

import re
import pandas as pd
# import math


class ExcelReader:
    """
    self.doc - текущий документ, с которым работает класс
    """
    def __init__(self):
        self.doc = None


    def open(self, filename: str) -> None:
        """Метод открывает excel документ только для чтения

        Args:
            filename (str): имя excel документа
        """
        self.doc = pd.read_excel(filename, sheet_name=0, header=None)


    def close(self):
        """Метод закрывает excel документ, если он открыт
        """
        if not self._is_closed():
            self.doc = None


    def _is_closed(self):
        return self.doc is None


    def cell(self, row: int, column: int) -> str:
        """Метод считывает данные из ячейки

        Args:
            row (int): индекс строки
            column (int): индекс столбца

        Returns:
            str: содержимое ячейки
        """
        return self.doc.iloc[row, column]


    def last_valid_cell_index(self, column: int) -> int:
        """Метод возвращает индекс последней непустой ячейки в столбце

        Args:
            column (int): индекс столбца
        """
        return self.doc.iloc[:, column].last_valid_index()


class TableParser:
    def __init__(self):
        self.reader = ExcelReader()
        self.pattern_month = r"(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)\s+\d{4}"
        self.pattern_date = r"\d{4}"
        self.pattern_adjustment = "доля от размера годовой корректировки платы за тепловую энергию"
        self.pattern_end = "итого по договору"
        self.pattern_period = r"(0?[1-9]|1[1-9])\.\d{4}"


    def open(self, filename: str) -> None:
        self.reader.open(filename)


    def close(self):
        self.reader.close()


    def parse(self) -> dict:
        periods = dict()

        start = 12
        end = self.reader.last_valid_cell_index(0)
        print(f"start = {start}, end = {end}")

        current_month = None
        current_period = None

        # block = 1 означает что текущий блок - это основной долг,
        # block = 2 означает что текущий блог - это блок с корректировкой
        block = 0
        row = start
        while row <= end:
            row_type = self.row_type(row)

            if row_type == 1:
                block = 1
                current_month = self.find_month(row)
                periods[current_month] = {"main_debt": 0.0, "adjustment": 0.0}

            elif row_type == 2:
                block = 2

            elif row_type == 3:
                row = end

            elif row_type == 4:
                debt = self.read_main_debt(row)
                if block == 1:
                    periods[current_month]["main_debt"] += debt
                elif block == 2:
                    periods[current_month]["adjustment"] += debt

            elif row_type == 5:
                payment = self.read_payment(row)
                if block == 1:
                    periods[current_month]["main_debt"] -= payment
                elif block == 2:
                    periods[current_month]["adjustment"] -= payment

            elif row_type == 6:
                pass

            elif row_type == 7:
                pass

            row += 1

        for period in periods.keys():
            periods[period]["main_debt"] = round(periods[period]["main_debt"], 2)
            periods[period]["adjustment"] = round(periods[period]["adjustment"], 2)

        # print(f"Итоговый словарь: {periods}")
        return periods


    def find_pattern(self, pattern: str, text: str):
        return re.search(pattern, text, re.IGNORECASE)


    def row_type(self, row: int) -> int:
        """
        row - индекс строки, тип которой мы хотим узнать.

        Возвращаемые значения:
        1 - начало блока с основной задолженностью
        2 - начало блока с корректировкой
        3 - конечная строка
        4 - строка, содержащая задолженность
        5 - строка, содержащая платеж
        6 - пустая строка (обычно стоит предпоследней перед следующим блоком)
        7 - строка, содержащая сумму всех задолженностей и платежей (обычно стоит последней перед следующим блоком)
        """
        first = self.reader.cell(row, 0)
        second = self.reader.cell(row, 1)
        third = self.reader.cell(row, 2)
        fourth = self.reader.cell(row, 3)

        if not pd.isna(first):
            if self.find_pattern(self.pattern_month, first):
                return 1

            if self.pattern_adjustment.lower() in first.lower():
                return 2

            if self.pattern_end.lower() in first.lower():
                return 3

            if self.find_pattern(self.pattern_period, first) and (not pd.isna(second)):
                return 4
        else:
            if pd.isna(second) and (not pd.isna(third)) and (not pd.isna(fourth)):
                return 5

            if pd.isna(second) and pd.isna(third) and pd.isna(fourth):
                return 6

            if (not pd.isna(second)) and pd.isna(third) and (not pd.isna(fourth)):
                return 7

        print(f"Строка row={row} не соответствует ни одному формату, не ясно как её обрабатывать.")
        raise RuntimeError(f"Invalid row: {row}")


    def find_month(self, row: int):
        return self.find_pattern(self.pattern_month, self.reader.cell(row, 0)).group(0)


    def read_main_debt(self, row: int) -> float:
        result_debt = 0.0

        debt = self.parse_debt(row)
        payment_date = self.parse_payment_date(row)
        payment_amount = self.parse_payment_amount(row)

        if debt is not None:
            result_debt += debt
        if payment_amount is not None:
            result_debt -= payment_amount

        return result_debt


    def read_payment(self, row: int) -> float:
        result_payment = 0.0

        payment_date = self.parse_payment_date(row)
        payment_amount = self.parse_payment_amount(row)

        if payment_amount is not None:
            result_payment += payment_amount

        return result_payment


    def parse_debt(self, row):
        debt = self.reader.cell(row, 1)
        return None if pd.isna(debt) else debt


    def parse_payment_date(self, row):
        date = self.reader.cell(row, 2)
        return None if pd.isna(date) else date


    def parse_payment_amount(self, row):
        amount = self.reader.cell(row, 3)
        return None if pd.isna(amount) else amount


    def money_str_to_float(self, money):
        return float(money.replace(" ", "").replace(",", "."))
