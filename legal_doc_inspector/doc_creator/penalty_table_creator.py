from docx import Document
from docx.shared import Pt
from docx.enum.section import WD_ORIENT

class Penalty_table_creator:
    
    def __init__(self):
        self.doc = Document()
    
    def _save_doc(self, name:str):
        self.doc.save(name)
    
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
    
    def _create_month_periods_for_table(self, list_of_dicts):
        
        # для каждого периода список строк
        month_period = dict()
        
        for period_dict in 
    
    def _create_penalty_table(self, table, json):
        
        pass
    
    
    def _create_month_subtable(self,table):
        pass
    
    