import json

from docx import Document

from DocxRedactor import DocxRedactor

class DocLawsuitReplacer:
    """
    Класс для редактирования документа с табличкой
    
    """
    def __init__(self) -> None:
        self.redactor: DocxRedactor = DocxRedactor()
        self.doc: Document = None


    def make_instance(self, template_filename: str, output_filename: str = None):
        """
        template_filename: str - имя файла-шаблона
        output_filename: str - имя файла, созданного по шаблону
        """

        self.redactor.clone_file(template_filename, output_filename)
        self.doc = self.redactor.open(output_filename)

        self.fill_file()

        self.redactor.save()
        self.redactor.close()


    def fill_file(self):
        self.fill_first_table()
        self.fill_second_table()


    def fill_first_table(self):
        text_1 = self.redactor.get_table(0).row_cells(4)[4].text
        text_2 = self.redactor.get_table(0).row_cells(6)[4].text

        # self.clone_row_in_first_table_2(0, 4, 5, text_1)
        self.clone_row_in_first_table_1(0, 5, 6)
        # self.clone_row_in_first_table_1(0, 9, 10)

        # self.clone_row_in_first_table_2(0, 6, 11, text_2)


    def clone_row_in_first_table_1(self, table_index, source_row_index, target_row_index):
        table = self.redactor.get_table(table_index)
        c1 = table.row_cells(source_row_index)[0]
        new_row = self.redactor.insert_row_in_table(table, target_row_index)
        self.redactor.clone_table_row(table.rows[source_row_index], new_row)
        c2 = new_row.cells[0]
        self.redactor.merge_table_cells(c1, c2)

        self.redactor.merge_table_cells(new_row.cells[1], new_row.cells[2])
        self.redactor.merge_table_cells(new_row.cells[6], new_row.cells[7])
        self.redactor.merge_table_cells(new_row.cells[9], new_row.cells[10])


    def clone_row_in_first_table_2(self, table_index, source_row_index, target_row_index, text):
        table = self.redactor.get_table(table_index)
        c1 = table.row_cells(source_row_index)[0]
        new_row = self.redactor.insert_row_in_table(table, target_row_index)
        self.redactor.clone_table_row(table.rows[source_row_index], new_row)
        c2 = new_row.cells[0]
        self.redactor.merge_table_cells(c1, c2)

        self.redactor.merge_table_cells(new_row.cells[1], new_row.cells[2])
        for i in range(5, 12):
            self.redactor.merge_table_cells(new_row.cells[4], new_row.cells[i])

        new_row.cells[4].paragraphs[0].runs[0].text = text.strip()


    def fill_second_table(self):
        table = self.redactor.get_table(1)
        new_row = self.redactor.insert_row_in_table(table, 2)
        self.redactor.clone_table_row(table.rows[1], new_row)
