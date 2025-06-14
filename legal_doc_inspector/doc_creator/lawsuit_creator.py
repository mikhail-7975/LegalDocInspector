from pathlib import Path

import docx
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.table import Table, _Cell, _Row, _Column
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, ns


class LawsuitCreator:

    def __init__(self, data_json:dict):
        self.doc = docx.Document()
        self.data_json = data_json

    def create_lawsuit(self, info_json, path_to_save:Path):
        self._create_title(info_json=info_json)
        self.create_first_part_of_lawsuit(info_json=info_json)
        self.create_second_part_of_lawsuit(info_json=info_json)
        self.create_third_part_of_lawsuit(info_json=info_json)
        self._save_doc(str(path_to_save))

    def _save_doc(self, name:str):
        self.doc.save(name)
    
    def _create_title(self, info_json): 
        
        table = self.doc.add_table(rows=7, cols=2)
        table.style = "Normal Table"
        table_rows = table.rows
        self.set_table_width(table, 17)
        for row in table.rows:
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST


        self._put_text_into_table_cell(text="В",
                                       cell=table_rows[0].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"{info_json['court_info']['name']}\n",
                                       cell=table_rows[0].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f"{info_json['court_info']['addres']}",
                                       cell=table_rows[0].cells[1],
                                       orient='left')
        
        self._set_cell_vertical_alignment(cell=table_rows[0].cells[1])

        self._put_text_into_table_cell(text="Истец:",
                                       cell=table_rows[1].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"{info_json['plaintiff_info']['full_name']}\n",
                                       cell=table_rows[1].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f"(ОГРН {info_json['plaintiff_info']['ogrn']}, ИНН {info_json['plaintiff_info']['inn']})",
                                       cell=table_rows[1].cells[1],
                                       orient='left',
                                       need_bold=False)
        
        self._put_text_into_table_cell(text="Адрес:",
                                       cell=table_rows[2].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"{info_json['plaintiff_info']['addres']}",
                                       cell=table_rows[2].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text="Адрес для направления корреспонденции:",
                                       cell=table_rows[3].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_underline=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"{info_json['plaintiff_info']['correspondency_addres']}",
                                       cell=table_rows[3].cells[1],
                                       orient='left',
                                       need_bold=True)

        self._put_text_into_table_cell(text="Ответчик:",
                                       cell=table_rows[4].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)

        self._put_text_into_table_cell(text=f"{info_json['defendant_info']['full_name']}\n",
                                       cell=table_rows[4].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text="Адрес:",
                                       cell=table_rows[5].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)

        self._put_text_into_table_cell(text=f"{info_json['defendant_info']['addres']}",
                                       cell=table_rows[5].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f"(ОГРН {info_json['defendant_info']['ogrn']}, ИНН {info_json['defendant_info']['inn']})",
                                       cell=table_rows[4].cells[1],
                                       orient='left',
                                       need_bold=False,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"Цена иска: {info_json['lawsuit_info']['cost']}\n",
                                       cell=table_rows[6].cells[1],
                                       orient='left',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text=f"Госпошлина: {info_json['lawsuit_info']['tax']}",
                                       cell=table_rows[6].cells[1],
                                       orient='left',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        

        par = self._add_paragraph_with_run(text="\nИСКОВОЕ ЗАЯВЛЕНИЕ\n",
                                           need_bold=True,
                                           orient='center')
        
        service_type = self._get_service_type1(info=info_json['lawsuit_info']['service_type'])
        
        self._add_run_to_paragraph(text=f'о взыскании задолженности {service_type}',
                                   paragraph=par,
                                   need_bold=True)
    
    def create_third_part_of_lawsuit(self, info_json):
        self._add_paragraph_with_run(text="\n3.  Неустойка.\n",
                                     need_bold=True)
        ##TODO
        # я думаю что этот параграф зависит от того что за тип компании
        self._add_paragraph_with_run(text='В соответствии с частью 9.2 статьи 15 Федерального закона от 27.07.2010 № 190-ФЗ «О теплоснабжении» товарищества собственников жилья, жилищные, жилищно-строительные и иные специализированные потребительские кооперативы, созданные в целях удовлетворения потребностей граждан в жилье, приобретающие тепловую энергию (мощность) и (или) теплоноситель для целей предоставления коммунальных услуг, в случае несвоевременной и (или) неполной оплаты тепловой энергии (мощности) и (или) теплоносителя уплачивают единой теплоснабжающей организации (теплоснабжающей организации) пени в размере одной трехсотой ставки рефинансирования Центрального банка Российской Федерации, действующей на день фактической оплаты, от не выплаченной в срок суммы за каждый день просрочки начиная с тридцать первого дня, следующего за днем наступления установленного срока оплаты, по день фактической оплаты, произведенной в течение девяноста календарных дней со дня наступления установленного срока оплаты, либо до истечения девяноста календарных дней после дня наступления установленного срока оплаты, если в девяностодневный срок оплата не произведена. Начиная с девяносто первого дня, следующего за днем наступления установленного срока оплаты, по день фактической оплаты пени уплачиваются в размере одной стотридцатой ставки рефинансирования Центрального банка Российской Федерации, действующей на день фактической оплаты, от не выплаченной в срок суммы за каждый день просрочки.')
        
        self._add_paragraph_with_run(text='Согласно части 6.3 статьи 13 Федерального закона от 07.12.2011 № 416-ФЗ «О водоснабжении и водоотведении» товарищества собственников жилья, жилищные, жилищно-строительные и иные специализированные потребительские кооперативы, созданные в целях удовлетворения потребностей граждан в жилье, приобретающие горячую, питьевую и (или) техническую воду для целей предоставления коммунальных услуг, в случае несвоевременной и (или) неполной оплаты воды уплачивают организации, осуществляющей горячее водоснабжение, холодное водоснабжение, пени в размере одной трехсотой ставки рефинансирования Центрального банка Российской Федерации, действующей на день фактической оплаты, от не выплаченной в срок суммы за каждый день просрочки начиная с тридцать первого дня, следующего за днем наступления установленного срока оплаты, по день фактической оплаты, произведенной в течение девяноста календарных дней со дня наступления установленного срока оплаты, либо до истечения девяноста календарных дней после дня наступления установленного срока оплаты, если в девяностодневный срок оплата не произведена. Начиная с девяносто первого дня, следующего за днем наступления установленного срока оплаты, по день фактической оплаты пени уплачиваются в размере одной стотридцатой ставки рефинансирования Центрального банка Российской Федерации, действующей на день фактической оплаты, от не выплаченной в срок суммы за каждый день просрочки.')

        par = self._add_paragraph_with_run(text='Исходя из размера Основного долга и Периода задолженности ')
        self._add_run_to_paragraph(text='неустойка ',
                                   paragraph=par,
                                   need_bold=True)
        
        self._add_run_to_paragraph('по Договорам составляет:',
                                   paragraph=par)

        self._create_penalty_table(info_json)

        par = self._add_paragraph_with_run(text='Расчет суммы неустойки прилагается к настоящему исковому заявлению.',
                                           need_bold=True)
        
        par = self._add_paragraph_with_run(text='Таким образом, общая ')

        self._add_run_to_paragraph(text="цена иска ",
                                   paragraph=par,
                                   need_underline=True)
        
        self._add_run_to_paragraph(text='составляет ',
                                   paragraph=par)

        self._add_run_to_paragraph(text=f'{info_json['lawsuit_info']['cost']} ',
                                   paragraph=par,
                                   need_bold=True)
        
        # self._add_run_to_paragraph(text='руб.',
        #                            paragraph=par)
        
        par = self._add_paragraph_with_run(text='размер ')

        self._add_run_to_paragraph(text='государственной пошлины ',
                                   need_underline=True,
                                   paragraph=par)
        
        self._add_run_to_paragraph(text='составляет ',
                                   paragraph=par)

        self._add_run_to_paragraph(text=f'{info_json['lawsuit_info']['tax']}\n',
                                   paragraph=par,
                                   need_bold=True)
        
        par = self._add_paragraph_with_run(text='На основании вышеизложенного, в соответствии со статьями 309, 310, 395, 539, 541, 544 Гражданского кодекса РФ, ст. 15 Федерального закона от 27.07.2010 № 190-ФЗ «О теплоснабжении», ст. 13 Федерального закона от 07.12.2011 № 416-ФЗ «О водоснабжении и водоотведении», статьями 4, 125 Арбитражного процессуального кодекса Российской Федерации,')
        # self._add_run_to_paragraph(text='руб.',
        #                            paragraph=par)
        
        

    def _create_penalty_table(self, info_json):

        table = self.doc.add_table(rows=1, cols=5)

        title_row_cells = table.rows[0].cells
        table.style = "Table Grid"
        self._put_text_into_table_cell(text='Реквизиты\n(номер) договора',
                                       cell=title_row_cells[0],
                                       font_size=10.5,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Период',
                                       cell=title_row_cells[1],
                                        font_size=10.5,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Задолженность\n(основной долг),\nруб.',
                                       cell=title_row_cells[2],
                                       font_size=10.5,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Неустойка руб.',
                                        cell=title_row_cells[3],
                                        font_size=10.5,
                                        need_bold=True)
        
        self._put_text_into_table_cell(text='Итого по договору (неустойка + основной долг), сумма, руб.',
                                       cell=title_row_cells[4],
                                       font_size=10.5,
                                       need_bold=True)
        contracts = []
        for key, value in info_json['table_info'].items():
            if '№' in key:
                contracts.append((key, info_json['table_info'][key]))

        for contract_name, contract in contracts:
            row = table.add_row()
            row_cells = row.cells
            self._put_text_into_table_cell(text=f'{contract_name}',
                                       cell=row_cells[0],
                                       font_size=10.5,
                                       need_bold=True)
            
            self._put_text_into_table_cell(text=f'{contract['contract_periods']}',
                                       cell=row_cells[1],
                                        font_size=10.5,)
            
            self._put_text_into_table_cell(text=f'{contract['debt']}',
                                       cell=row_cells[2],
                                       font_size=10.5,)
            
            self._put_text_into_table_cell(text=f'{contract['penalty']}',
                                        cell=row_cells[3],
                                        font_size=10.5,)
            
            self._put_text_into_table_cell(text=f'{contract['debt_penalty']}',
                                       cell=row_cells[4],
                                       font_size=10.5,)

        result_row = table.add_row()
        result_row_cells = result_row.cells

        result_row_cells[0].merge(result_row_cells[1])


        self._put_text_into_table_cell(text='ИТОГО:',
                                       cell=result_row_cells[0],
                                       font_size=10.5,
                                       orient='right',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f'{info_json['table_info']['all_debt']}',
                                       cell=result_row_cells[2],
                                       font_size=10.5,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f'{info_json['table_info']['all_penalty']}',
                                       cell=result_row_cells[3],
                                       font_size=10.5,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f'{info_json['table_info']['cost_of_lawsuit']}',
                                       cell=result_row_cells[4],
                                       font_size=10.5,
                                       need_bold=True)

        for row in table.rows:
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

        return table

        
    def create_second_part_of_lawsuit(self, info_json):
        self._add_paragraph_with_run(text="\n2.  Соблюдение претензионного порядка.\n",
                                     need_bold=True)
        
        service_type = self._get_service_type4(info=info_json['lawsuit_info']['service_type'])

        par = self._add_paragraph_with_run(text=f'Поскольку Ответчик свои обязательства по оплате поставленной {service_type} исполнил ненадлежащим образом, Истцом направлены в его адрес ',)
        
        self._add_run_to_paragraph(text='претензии:',
                                   paragraph=par,
                                   need_bold=True)
        items = info_json['lawsuit_info']['claims']
        self._add_unnumeric_list(items=items)
        
        par = self._add_paragraph_with_run(text=f'с предложением погасить образовавшуюся задолженность за {service_type}, которые оставлены Ответчиком без ответа. Задолженность в полном объеме не погашена. Копии претензий, а также документация в отношении направления/получения их Ответчиком, соблюдения претензионного порядка прилагаются к настоящему иску.',
                                           first_line_indent=0)

    def create_first_part_of_lawsuit(self, info_json):
        self._add_paragraph_with_run(text="\n2.  Соблюдение претензионного порядка.\n",
                                     need_bold=True)
        
        par = self._add_paragraph_with_run(text='Между организацией ')

        self._add_run_to_paragraph(text=f'{info_json['plaintiff_info']['full_name']} ',
                                   need_bold=True,
                                   paragraph=par)
        
        self._add_run_to_paragraph(text=f"(далее - {info_json['plaintiff_info']['short_name']}, Истец) и ",
                                   paragraph=par)

        self._add_run_to_paragraph(text=f'{info_json['defendant_info']['short_name']} ',
                                   paragraph=par,
                                   need_bold=True)
        
        contract_type = self._get_contract_type(info_json=info_json)

        self._add_run_to_paragraph(text=f'(далее - Ответчик) были заключены следующие договоры (далее - {contract_type}), предметом которых является подача (поставка) Истцом Ответчику ',
                                   paragraph=par)
        
        service_type = self._get_service_type2(info_json=info_json)
        
        self._add_run_to_paragraph(text=f'{service_type} на условиях, определённых {"Договором" if contract_type=='Договор' else "Договорами"}:',
                                   paragraph=par)
        

        table = self._create_table_of_contracts_info(info_json)
        
        self.set_table_width(table, 17)

        par = self._add_paragraph_with_run(text="Поставка (подача) ресурсов производилась на условиях, определенных Договорами, за плату согласно действующим тарифам.")

        par = self._add_paragraph_with_run(text=f'{info_json['plaintiff_info']['short_name']} свои обязательства по Договорам исполнило в полном объеме, поставив ресурсы ')

        service_type = self._get_service_type3(info_json=info_json)

        self._add_run_to_paragraph(text=f'{service_type} в соответствии с принятыми на себя обязательствами. Точки поставки (адреса) указаны в названных Договорах.',
                                   paragraph=par)

        par = self._add_paragraph_with_run(text='В соответствии с условиями Договоров в период, указанный в соответствующей графе вышеизложенной таблицы (далее – Период), Истец поставил Ответчику через присоединенную сеть в соответствии с Договорами тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС), а Ответчик, соответственно, обязан оплатить полученные ресурсы на основании указанных Договоров и установленных тарифов для соответствующих групп потребителей.')

        par = self._add_paragraph_with_run(text='За Ответчиком по названным Договорам образовалась задолженность за потребленные ресурсы (тепловую энергию и/или теплоноситель и горячую воду) в сумме ')

        self._add_run_to_paragraph(text=f'{info_json['table_info']['all_debt']} ',
                                   paragraph=par,
                                   need_bold=True)
        
        self._add_run_to_paragraph(text='руб. за указанный выше Период.',
                                   paragraph=par,)
        
        par = self._add_paragraph_with_run(text='Договорами (в том числе раздел 5, пункт 5.5 каждого Договора), определены порядок и сроки взаиморасчетов за потребленные ресурсы, которые существенно нарушены Ответчиком. ')

        par = self._add_paragraph_with_run(text='Факт поставки тепловой энергии/теплоносителя, горячей воды в указанном в настоящем Иске количестве подтверждается соответствующими документами, прилагаемыми к настоящему иску, в том числе: актами приема-передачи энергоресурсов, счетами на оплату, счетами-фактурами.')

        par = self._add_paragraph_with_run(text=f'Таким образом, Истец свои обязательства по Договорам исполнил надлежащим образом и в полном объеме, поставив Ответчику {service_type[1:-1]} в соответствии с принятыми на себя обязательствами в отношении количества, качества и сроков ее поставки. Ответчик оплату в полном размере не произвел.')

        par = self._add_paragraph_with_run(text='В соответствии с п. 1 ст. 539 Гражданского кодекса Российской Федерации (далее – «ГК РФ») по договору энергоснабжения энергоснабжающая организация обязуется подавать абоненту (потребителю) через присоединенную сеть энергию, а абонент обязуется оплачивать принятую энергию, а также соблюдать предусмотренный договором режим ее потребления, обеспечивать безопасность эксплуатации находящихся в его ведении энергетических сетей и исправность используемых им приборов и оборудования, связанных с потреблением энергии.')

        par = self._add_paragraph_with_run(text='Согласно п. 1 ст. 544 ГК РФ оплата энергии производится за фактически принятое абонентом количество энергии в соответствии с данными учета энергии, если иное не предусмотрено законом, иными правовыми актами или соглашением сторон договора энергоснабжения (купли-продажи (поставки) энергии).')

        par = self._add_paragraph_with_run(text="В силу ст. ст. 309, 310 ГК РФ обязательства должны исполняться надлежащим образом в соответствии с условиями обязательства и требованиями закона, иных правовых актов. Односторонний отказ от исполнения обязательства и одностороннее изменение его условий не допускаются за исключением случаев, предусмотренных действующим законодательством.")

    def _add_unnumeric_list(self, items:list, font_size = 12, need_bold = True):


        for elem in items :
            par = self.doc.add_paragraph(style="List Bullet")
            run = par.add_run(f"{elem}")
            run.font.name = 'Times New Roman'
            element = run._element
            rPr = element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn('w:ascii'), 'Times New Roman')
            rFonts.set(qn('w:hAnsi'), 'Times New Roman')
            rFonts.set(qn('w:eastAsia'), 'Times New Roman')  
            rFonts.set(qn('w:cs'), 'Times New Roman')
            run.font.size = Pt(font_size)
            run.bold = True



    def _get_service_type3(self, info_json):
        contracts = []
        result = ''
        was1, was2, was3 = 0, 0, 0
        for key, value in info_json['table_info'].items():
            if '№' in key:
                contracts.append(key)

        for contract_name in contracts:
            if "ТЭ" in contract_name and not was2:
                was2 = 1
                if was3:
                    result = result + ' и тепловую энергию/теплоноситель (ТЭ)'
                else:
                    result = result + 'тепловую энергию/теплоноситель (ТЭ)'
            if "ГВС" in contract_name and not was3:
                was3 = 1
                if was2:
                    result = result = ' и горячую воду(ГВС)'
                else:
                    result = result + 'горячую воду (ГВС)'

        return f'({result})' 
    def _get_service_type2(self, info_json):
        contracts = []
        result = ''
        was1, was2, was3 = 0, 0, 0
        for key, value in info_json['table_info'].items():
            if '№' in key:
                contracts.append(key)

        for contract_name in contracts:
            if "СОИ" in contract_name and not was1:
                was1 = 1
                result = result + 'горячей воды для целей содержания общего имущества в многоквартирных домах (далее - СОИ), '
            if "ТЭ" in contract_name and not was2:
                was2 = 1
                result = result + 'тепловой энергии и/или теплоносителя (далее – ТЭ), '
            if "ГВС" in contract_name and not was3:
                was3 = 1
                result = result + 'горячей воды через присоединенные сети горячего водоснабжения (далее – ГВС), '

        return result

    def _get_contract_type(self, info_json, is_dog=True):
        contracts = []
        for key, value in info_json['table_info'].items():
            if '№' in key:
                contracts.append(key)
        if len(contracts) > 1 and is_dog : 
            return 'Договоры'
        else :
            return 'Договор'
        
        
    def _create_table_of_contracts_info(self, info_json):
        table = self.doc.add_table(rows=1, cols=5)
        title_row_cells = table.rows[0].cells
        table.style = "Table Grid"
        self._put_text_into_table_cell(text='Реквизиты\n(номер) договора',
                                       cell=title_row_cells[0],
                                       font_size=11,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Период',
                                       cell=title_row_cells[1],
                                        font_size=11,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Задолженность\n(основной долг),\nруб.',
                                       cell=title_row_cells[2],
                                       font_size=11,
                                       need_bold=True)
        
        self._put_text_into_table_cell(text='Срок оплаты',
                                        cell=title_row_cells[3],
                                        font_size=11,
                                        need_bold=True)
        
        self._put_text_into_table_cell(text='Пункт договора',
                                       cell=title_row_cells[4],
                                       font_size=11,
                                       need_bold=True)
        
        last_day = info_json['lawsuit_info']['last_day']
        x = '5.5'
        contracts = []
        for key, value in info_json['table_info'].items():
            if '№' in key:
                contracts.append((key, info_json['table_info'][key]))

        for contract_name, contract in contracts:
            row = table.add_row()
            row_cells = row.cells
            self._put_text_into_table_cell(text=f'{contract_name}',
                                       cell=row_cells[0],
                                       font_size=11,
                                       need_bold=True)
            
            self._put_text_into_table_cell(text=f'{contract['contract_periods']}',
                                       cell=row_cells[1],
                                        font_size=11,)
            
            self._put_text_into_table_cell(text=f'{contract['debt']}',
                                       cell=row_cells[2],
                                       font_size=11,)
            
            self._put_text_into_table_cell(text=f'{last_day}',
                                        cell=row_cells[3],
                                        font_size=9,)
            
            self._put_text_into_table_cell(text=f'{x}',
                                       cell=row_cells[4],
                                       font_size=11,)

        result_row = table.add_row()
        result_row_cells = result_row.cells

        result_row_cells[0].merge(result_row_cells[1])
        result_row_cells[3].merge(result_row_cells[4])

        self._put_text_into_table_cell(text='Сумма:',
                                       cell=result_row_cells[0],
                                       font_size=11,
                                       orient='right',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text=f'{info_json['table_info']['all_debt']}',
                                       cell=result_row_cells[2],
                                       font_size=11,
                                       need_bold=True)

        for row in table.rows:
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

        return table

    def _get_service_type4(self, info):

        match info:
            case "ГВС + ТЭ":
                return "ТЭ и ГВС"
            
            case "ГВС":
                return "ГВС"

            case "ТЭ":
                return "ТЭ"
            
    def _get_service_type1(self, info):

        match info:
            case "ГВС + ТЭ":
                return "за тепловую энергию и поставку горячей воды"
            
            case "ГВС":
                return "за поставку горячей воды"

            case "ТЭ":
                return "за тепловую энергию и/или теплоноситель"
        
    def _add_paragraph_with_run(self, text:str,
                                left_indent = 0, 
                                right_indent = -1, 
                                first_line_indent =1.25, 
                                font_size=12, 
                                need_underline=False, 
                                need_bold=False, 
                                need_italic=False, 
                                orient="left" ):
       
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.first_line_indent = Cm(first_line_indent)
        paragraph.paragraph_format.left_indent = Cm(left_indent)
        paragraph.paragraph_format.right_indent = Cm(right_indent)
        run = paragraph.add_run(text)
        run.bold = need_bold
        run.italic = need_italic
        run.underline = need_underline
        run.font.name = 'Times New Roman'
        element = run._element
        rPr = element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        rFonts.set(qn('w:eastAsia'), 'Times New Roman')  
        rFonts.set(qn('w:cs'), 'Times New Roman')
        run.font.size = Pt(font_size)

        match orient:
            case "center":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            case "left":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            case "right":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        return paragraph
    
    def _add_run_to_paragraph(self,
                            text:str,
                            paragraph: Paragraph,
                            font_size=12, 
                            need_underline=False, 
                            need_bold=False, 
                            need_italic=False):
        
        run = paragraph.add_run(text)
        run.bold = need_bold
        run.italic = need_italic
        run.underline = need_underline
        run.font.name = 'Times New Roman'
        element = run._element
        rPr = element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        rFonts.set(qn('w:eastAsia'), 'Times New Roman')  
        rFonts.set(qn('w:cs'), 'Times New Roman')
        run.font.size = Pt(font_size)

        return paragraph
        
                             
        



    def _put_text_into_table_cell(self, 
                                  text:str, 
                                  cell:_Cell, 
                                  font_size=12, 
                                  need_underline=False, 
                                  need_bold=False, 
                                  need_italic=False, 
                                  orient="center", 
                                  need_vertical_orient=True, 
                                  need_gray_bgc=False):
        
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(text)
        run.bold = need_bold
        run.italic = need_italic
        run.underline = need_underline
        run.font.name = 'Times New Roman'

        element = run._element
        rPr = element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        rFonts.set(qn('w:eastAsia'), 'Times New Roman')  
        rFonts.set(qn('w:cs'), 'Times New Roman')
        # run._element.rPr.rFonts.set('w:eastAsia', 'Times New Roman')  # для корректного отображения в Word
        run.font.size = Pt(font_size)

        match orient:
            case "center":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            case "left":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            case "right":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        if need_vertical_orient:
            self._set_cell_vertical_alignment(cell=cell)

        if need_gray_bgc:
            self._set_cell_background(cell=cell)


        
    def _set_cell_vertical_alignment(self, cell:_Cell, align="center"):
        tc = cell._tc
        tc_pr = tc.get_or_add_tcPr()
        tag = tc_pr.xpath('w:vAlign')
        if tag:
            el = tag[0]
            el.set(qn('w:val'), align)
        else:
            valign = OxmlElement('w:vAlign')
            valign.set(qn('w:val'), align)
            tc_pr.append(valign)


    def _set_cell_background(self, cell:_Cell, color_hex = "#cccccc"):
        tc_pr = cell._tc.get_or_add_tcPr()
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), color_hex)
        tc_pr.append(shading_elm)

    
    def set_table_width(self, table, width_cm):
    
        tbl = table._tbl  # получаем внутренний XML-объект
        tbl_pr = tbl.tblPr  # свойства таблицы

        # Создаем элемент <w:tblW> для указания ширины
        tbl_w = OxmlElement("w:tblW")
        tbl_w.set(ns.qn("w:w"), str(int(width_cm * 567)))  # 1 см = 567 EMU
        tbl_w.set(ns.qn("w:type"), "dxa")  # тип ширины: dxa = измерение в твипах (1/20 pt)

        # Удаляем предыдущее значение ширины, если есть
        for el in tbl_pr.xpath(".//w:tblW"):
            tbl_pr.remove(el)

        # Добавляем новое
        tbl_pr.append(tbl_w)