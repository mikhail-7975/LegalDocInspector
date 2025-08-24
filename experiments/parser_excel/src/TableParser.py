"""
Класс TableParser реализует интерфейс взаимодействия с excel документом. TableParser работает только на чтение!
"""

import re
import pandas as pd

from convert_month import convert_month


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
        self.pattern_period = r"(0?[1-9]|1[0-9])\.\d{4}"


    def open(self, filename: str) -> None:
        self.reader.open(filename)


    def close(self):
        self.reader.close()


    def parse(self) -> dict:
        periods = dict()

        start = 12
        end = self.reader.last_valid_cell_index(0)
        # print(f"start = {start}, end = {end}")

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
                periods[current_month] = {
                    "accrual": {
                        "accruals": [],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": None,
                        "total_amount_of_payments": None,
                        "debt": None
                    },
                    "adjustment": {
                        "accruals": [],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": None,
                        "total_amount_of_payments": None,
                        "debt": None
                    }
                }

            elif row_type == 2:
                block = 2

            elif row_type == 3:
                row = end

            elif row_type == 4:
                period = self.parse_period(row)
                accrual = self.parse_accrual(row)

                # Распознаем тип операции
                type_operation = None

                # # Отрицательную задолженность парсим как оплату
                # if accrual < 0:
                #     type_operation = "payments"
                # Распознаем добор
                if self.is_additional(period, current_month):
                    type_operation = "additionals"
                # Во всех остальных случаях это просто задолженность
                else:
                    type_operation = "accruals"

                # if block == 1:
                #     periods[current_month]["accrual"][type_operation].append({"period": period, "accrual": accrual})
                # elif block == 2:
                #     periods[current_month]["adjustment"][type_operation].append({"period": period, "accrual": accrual})
                periods[current_month][self.block_type(block)][type_operation].append({"period": period, "accrual": accrual})

            elif row_type == 5:
                date = self.parse_payment_date(row)
                payment = self.parse_payment_amount(row)
                contract_type = self.parse_payment_contract_type(row)
                # if block == 1:
                #     periods[current_month]["accrual"]["payments"].append({"date": date, "payment": payment, "contract_type": contract_type})
                # elif block == 2:
                #     periods[current_month]["adjustment"]["payments"].append({"date": date, "payment": payment, "contract_type": contract_type})
                periods[current_month][self.block_type(block)]["payments"].append({"date": date, "payment": payment, "contract_type": contract_type})

            elif row_type == 6:
                periods[current_month][self.block_type(block)]["debt"] = self.parse_debt(row)

            elif row_type == 7:
                periods[current_month][self.block_type(block)]["total_amount_of_accruals"] = self.parse_total_amount_of_accruals(row)
                periods[current_month][self.block_type(block)]["total_amount_of_payments"] = self.parse_total_amount_of_paymnets(row)

            row += 1

        return periods


    def block_type(self, block):
        if block == 1:
            return "accrual"
        elif block == 2:
            return "adjustment"
        else:
            print(f"Блок block={block} не не может быть обработан, нарушение парсинга")
            raise RuntimeError(f"Invalid block: {block}")


    def find_pattern(self, pattern: str, text: str):
        return re.search(pattern, text, re.IGNORECASE)


    def row_type(self, row: int) -> int:
        """
        row - индекс строки, тип которой мы хотим узнать.

        Возвращаемые значения:
        1 - начало блока с начислениями
        2 - начало блока с корректировкой
        3 - конечная строка
        4 - строка, содержащая начисления
        5 - строка, содержащая платеж
        6 - строка, содержащая задолженность за весь текущий период (обычно стоит предпоследней перед следующим блоком)
        7 - строка, содержащая сумму всех задолженностей и платежей (обычно стоит последней перед следующим блоком)
        """
        first = self.reader.cell(row, 0)
        second = self.reader.cell(row, 1)
        third = self.reader.cell(row, 2)
        fourth = self.reader.cell(row, 3)
        sixth = self.reader.cell(row, 5)
        seventh = self.reader.cell(row, 6)

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

            if pd.isna(second) and pd.isna(third) and pd.isna(fourth) and (not pd.isna(seventh)):
                return 6

            if (not pd.isna(second)) and pd.isna(third) and (not pd.isna(fourth)):
                return 7

        print(f"Строка row={row} не соответствует ни одному формату, не ясно как её обрабатывать.")
        raise RuntimeError(f"Invalid row: {row}")


    def find_month(self, row: int):
        return self.find_pattern(self.pattern_month, self.reader.cell(row, 0)).group(0)


    # def read_accrual(self, row: int) -> float:
    #     result_accrual = 0.0

    #     accrual = self.parse_accrual(row)
    #     payment_date = self.parse_payment_date(row)
    #     payment_amount = self.parse_payment_amount(row)

    #     if accrual is not None:
    #         result_accrual += accrual
    #     if payment_amount is not None:
    #         result_accrual -= payment_amount

    #     return result_accrual


    # def read_payment(self, row: int) -> float:
    #     result_payment = 0.0

    #     payment_date = self.parse_payment_date(row)
    #     payment_amount = self.parse_payment_amount(row)

    #     if payment_amount is not None:
    #         result_payment += payment_amount

    #     return result_payment


    def parse_period(self, row):
        period = self.reader.cell(row, 0)
        return None if pd.isna(period) else period


    def parse_accrual(self, row):
        accrual = self.reader.cell(row, 1)
        return None if pd.isna(accrual) else accrual


    def parse_payment_date(self, row):
        date = self.reader.cell(row, 2)
        return None if pd.isna(date) else date


    def parse_payment_amount(self, row):
        amount = self.reader.cell(row, 3)
        return None if pd.isna(amount) else amount


    def parse_total_amount_of_accruals(self, row):
        total_amount = self.reader.cell(row, 1)
        return None if pd.isna(total_amount) else total_amount


    def parse_total_amount_of_paymnets(self, row):
        total_amount = self.reader.cell(row, 3)
        return None if pd.isna(total_amount) else total_amount


    def parse_debt(self, row):
        debt = self.reader.cell(row, 6)
        return None if pd.isna(debt) else debt


    def parse_payment_contract_type(self, row):
        contract_type = self.reader.cell(row, 5)
        return None if pd.isna(contract_type) else contract_type


    def is_additional(self, period: str, month: str):
        """Проверяем, является ли текущий период добором или нет.

        Args:
            period (str): Это период платежа, он приходит в виде ДД.ГГГГ
            month (str): Это месяц, в котором записан платеж, приходит в виде */Название_месяца ГГГГ/* 

        Если период платежа не совпадает с месяцем, в котором он записан, то это добор.
        """
        converted_month = convert_month(month.split()[0])
        converted_period = period.split(".")[0]
        if converted_month != converted_period:
            return True
        return False


    def money_str_to_float(self, money):
        return float(money.replace(" ", "").replace(",", "."))
