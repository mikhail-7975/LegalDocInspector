from collections import defaultdict
from pathlib import Path
from datetime import date

from docx.table import Table
from docx import Document
from docx.shared import Pt
from docx.enum.section import WD_ORIENT

class PenaltyTableCreator:
    
    def __init__(self):
        self.doc = Document()
    
    def save_doc(self, path_to_save:Path):
        self.doc.save(str(path_to_save))
    
    def _create_table_title(self, contract_number:str, start_date, end_date ):
        doc = self.doc
        
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Pt(842)  # ширина
        section.page_height = Pt(595)  # высота

        # создание титульника таблицы

        table = doc.add_table(rows=1, cols=11)

        # Получаем первую строку
        row_cells = table.rows[0].cells
        # Устанавливаем альбомную ориентацию
        # Объединяем первые две ячейки
        row_cells[0].merge(row_cells[2])
        row_cells[0].text = 'Информация о расчёте'
        row_cells[3].merge(row_cells[10])
        row_cells[3].text = 'тут должен быть номер договора'

        secondrow = table.add_row()
        row_cells = secondrow.cells
        row_cells[0].merge(row_cells[1])
        row_cells[0].text = "Начало просрочки"
        row_cells[2].merge(row_cells[4])
        row_cells[2].text = "тут будет дата начала просрочки"
        row_cells[5].merge(row_cells[6])
        row_cells[5].text = "конец просрочки"
        row_cells[7].merge(row_cells[10])
        row_cells[7].text = "тут будет дата конца просрочки"

        third_row = table.add_row()
        fourth_row = table.add_row()
        up_row_cells = third_row.cells
        down_row_cells = fourth_row.cells

        up_row_cells[0].merge(up_row_cells[1])
        down_row_cells[0].merge(down_row_cells[1])
        up_row_cells[0].merge(down_row_cells[0])
        up_row_cells[0].text = 'месяц'

        up_row_cells[2].merge(up_row_cells[3])
        down_row_cells[2].merge(down_row_cells[3])
        up_row_cells[2].merge(down_row_cells[2])
        up_row_cells[2].text = 'долг'

        up_row_cells[4].merge(up_row_cells[6])
        up_row_cells[4].text = 'период просрочки'

        down_row_cells[4].text = 'с'
        down_row_cells[5].text = 'по'
        down_row_cells[6].text = 'дней'

        up_row_cells[7].merge(down_row_cells[7])
        up_row_cells[7].text = 'ставка'

        up_row_cells[8].merge(down_row_cells[8])
        up_row_cells[8].text = 'доля ставки'

        up_row_cells[9].merge(down_row_cells[9])
        up_row_cells[9].text = 'формула'

        up_row_cells[10].merge(down_row_cells[10])
        up_row_cells[10].text = 'пени'
        
        return table
    
    def group_by_month(self, data):
        """
        принимает результат калькулятора пени, 
        возвращает периоды оплат и просрочек для каждого месяца
        """

        grouped = defaultdict(lambda: {'payments': [], 'periods': []})

        # Группируем платежи и периоды по месяцу
        for entry in data:
            month_key = entry['month']
            if 'payments' in entry:
                grouped[month_key]['payments'].append(entry['payments'])
            # Убираем лишние поля перед добавлением периода
            period_data = {
                k: v for k, v in entry.items()
                if k not in ('payments', 'month')
            }
            grouped[month_key]['periods'].append(period_data)

        result = []
        for month, items in grouped.items():
            combined = []
            # Сначала добавляем все платежи
            payments_seen = set()
            
            for payment in items['payments']:
                if payment is None:
                    continue
                
                for key, value in payment.items():
                    if key not in payments_seen:
                        print(key)
                        payments_seen.add(key)
                        combined.append({'type': 'payment', 'data': {key:value}})
                
                
            # Затем добавляем все периоды
            for period in items['periods']:
                combined.append({'type': 'period', 'data': period})

            def get_sort_key(event):
                if event['type'] == 'payment':
                    # Берём единственную дату из ключей
                    return next(iter(event['data'].keys()))
                else:
                    return event['data']['start']
                
            combined.sort(key=get_sort_key)

            result.append({month: combined})


        return result

    
    def _create_penalty_table(self, table:Table, list_dict_of_months):
        """
        принимает таблицу в документе и  результат group by month,
        добавляет в таблицу строки периодов для каждого месяца
        """
        for month_dict in list_dict_of_months:
            month_key, periods_and_payments  = next(iter(month_dict.items()))
            new_rows_for_month = []
            itogo = 0
            for period_or_payment in periods_and_payments:
                if period_or_payment['type'] == 'period':
                    data = period_or_payment['data']
                    new_row = table.add_row()
                    new_row_cells = new_row.cells
                    debt = data['debt']
                    start_date = data['start']
                    end_date = data['end']
                    days_count = data['days']
                    rate = data['rate']
                    rate = self._rate_float_to_decimal(rate)
                    penalty = data['penalty']
                    itogo+=penalty

                    start_date = start_date.strftime("%d.%m.%Y")
                    end_date = end_date.strftime("%d.%m.%Y")

                    new_row_cells[0].merge(new_row_cells[1])
                    new_row_cells[2].merge(new_row_cells[3])

                    new_row_cells[2].text = f'{debt}'

                    new_row_cells[4].text = f'{start_date}'
                    new_row_cells[5].text = f'{end_date}'
                    new_row_cells[6].text = f'{days_count}'

                    new_row_cells[7].text = '9,50%'
                    new_row_cells[8].text = rate

                    new_row_cells[9].text = f'{debt} × {days_count} × {rate} × 9,5%'
                    new_row_cells[10].text = f'{penalty} р.'
                    new_rows_for_month.append(new_row)

                if period_or_payment['type'] == 'payment':
                    data = period_or_payment['data']
                    new_row = table.add_row()
                    new_row_cells = new_row.cells
                    date_of_payment, amount = next(iter(data.items()))
                    date_of_payment = date_of_payment.strftime("%d.%m.%Y")

                    new_row_cells[0].merge(new_row_cells[1])
                    new_row_cells[2].merge(new_row_cells[3])

                    new_row_cells[2].text = f'-{amount}'

                    new_row_cells[4].text = f'{date_of_payment}'
                    new_row_cells[5].merge(new_row_cells[10])
                    new_row_cells[5].text = "погашение части долга"
                    new_rows_for_month.append(new_row)
            
            itog_row = table.add_row()
            itog_row_cells = itog_row.cells
            itog_row_cells[0].merge(itog_row_cells[1])
            itog_row_cells[2].merge(itog_row_cells[3])
            itog_row_cells[9].text = 'Итого'
            itog_row_cells[10].text = f'{itogo} р.'
            new_rows_for_month.append(itog_row)
            new_rows_for_month[0].cells[0].merge(new_rows_for_month[-1].cells[0])
            new_rows_for_month[0].cells[0].text = f'{month_key}'
        
        return table
    
    def _rate_float_to_decimal(self,rate):
        """
        переводит число с плавающей точкой в обыкновенную дробь
        """
        first = 1/300
        second = 1/170
        third = 1/130
        fourth = 0
        
        if rate==first:    
            return "1/300"
        if rate==second:
            return "1/170"
        if rate==third:
            return "1/130"
        if rate==fourth:
            return "0"
        
    def create_penalty_table_from_json(self, name, data, contract_number, start_date, end_date):
        table = self._create_table_title(contract_number, start_date, end_date)
        list_of_periods = self.group_by_month(data)
        table = self._create_penalty_table(table, list_of_periods)
        self.save_doc(name)

        return self.convert_datetime_keys(list_of_periods)
    
    def convert_datetime_keys(self,obj):
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                # Преобразуем ключ, если он datetime/date
                new_key = k
                if isinstance(k, date):
                    new_key = k.strftime("%d.%m.%Y")
                
                new_value = self.convert_datetime_keys(v)
                new_dict[new_key] = new_value
            return new_dict
        elif isinstance(obj, list):
            return [self.convert_datetime_keys(item) for item in obj]
        elif isinstance(obj, date):
            return obj.strftime("%d.%m.%Y")
        else:
            return obj