from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
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

    def create_lawsuit(self, path_to_save:Path):
        self._create_title()
        self._save_doc(str(path_to_save))

    def _save_doc(self, name:str):
        self.doc.save(name)
    
    def _create_title(self): 
        
        table = self.doc.add_table(rows=7, cols=2)
        table.style = "Normal Table"
        table_rows = table.rows
        self.set_table_width(table, 19)

        self._put_text_into_table_cell(text="В",
                                       cell=table_rows[0].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text="Арбитражный суд города Москвы\n",
                                       cell=table_rows[0].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text="115225, г. Москва, ул. Большая Тульская, д. 17\n",
                                       cell=table_rows[0].cells[1],
                                       orient='left')
        
        self._set_cell_vertical_alignment(cell=table_rows[0].cells[1])

        self._put_text_into_table_cell(text="Истец",
                                       cell=table_rows[1].cells[0],
                                       orient='right',
                                       need_bold=True,
                                       need_vertical_orient=False)
        
        self._put_text_into_table_cell(text="Публичное акционерное общество\n «Московская объединенная энергетическая компания» \n",
                                       cell=table_rows[1].cells[1],
                                       orient='left',
                                       need_bold=True)
        
        self._put_text_into_table_cell(text="(ОГРН 1047796974092, ИНН 7720518494)",
                                       cell=table_rows[1].cells[1],
                                       orient='left',
                                       need_bold=False)


    def _put_text_into_table_cell(self, text:str, cell:_Cell, font_size=12, need_bold=False, need_italic=False, orient="center", need_vertical_orient=True, need_gray_bgc=False):
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(text)
        run.bold = need_bold
        run.italic = need_italic
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