import json
from datetime import datetime, timedelta

from docx import Document
from docx.table import Table

from LegalDocInspector.legal_doc_inspector.doc_creator.docx_editor import DocxRedactor



class ClaimGenerator:
    """
    Класс создания документа по шаблону. При создании экземпляра принимает три аргумента:
    
    """

    def __init__(self) -> None:
        self.redactor: DocxRedactor = DocxRedactor()
        self.config: dict = None
        self.doc: Document = None


    def make_instance(self, config: str, template_filename: str, output_filename: str = None):
        """
        config_filename: str - конфиги для шаблона
        template_filename: str - имя файла-шаблона
        output_filename: str - имя файла, созданного по шаблону
        """
        self.config = config

        self.redactor.clone_file(template_filename, output_filename)
        self.doc = self.redactor.open(output_filename)

        self.fill_file()

        self.redactor.save()
        self.redactor.close()


    def parse_config(self, filename: str) -> dict:
        with open(filename, 'r', encoding="utf-8") as file:
            data = json.load(file)
        return data


    def borders(self, string: str, start: str = "/*", end: str = "*/"):
        return start + string + end


    def fill_file(self):
        # self.redactor.print_table(self.redactor.get_table(0))
        self.fill_first_table()
        self.fill_second_table()
        self.fill_third_table()
        self.fill_first_list()
        self.fill_second_list()
        self.fill_third_list()
        self.fill_other_parts()


    def fill_first_table(self):
        # self.redactor.print_table(table)

        to_replace = (
            # строка 2
            (self.borders("истец полное имя"),      self.config["plaintiff_info"]["full_name"]),
            (self.borders("истец огрн"),            self.config["plaintiff_info"]["ogrn"]),
            (self.borders("истец инн"),             self.config["plaintiff_info"]["inn"]),

            # Строка 3
            (self.borders("истец адрес"),           self.config["plaintiff_info"]["addres"]),

            # Строка 6
            (self.borders("ответчик полное имя"),   self.config["defendant_info"]["full_name"]),
            (self.borders("ответчик огрн"),         self.config["defendant_info"]["ogrn"]),
            (self.borders("ответчик инн"),          self.config["defendant_info"]["inn"]),

            # Строка 7
            (self.borders("ответчик адрес"),        self.config["defendant_info"]["addres"]),
        )

        table = self.redactor.get_table(0)

        cell = table.row_cells(2)[1]
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[0][0], to_replace[0][1])
        self.redactor.replace_text_in_paragraph(cell.paragraphs[1], to_replace[1][0], to_replace[1][1])
        self.redactor.replace_text_in_paragraph(cell.paragraphs[1], to_replace[2][0], to_replace[2][1])

        cell = table.row_cells(3)[1]
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[3][0], to_replace[3][1])

        cell = table.row_cells(6)[1]
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[4][0], to_replace[4][1])
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[5][0], to_replace[5][1])
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[6][0], to_replace[6][1])

        cell = table.row_cells(7)[1]
        self.redactor.replace_text_in_paragraph(cell.paragraphs[0], to_replace[7][0], to_replace[7][1])

        self.redactor.save()


    def fill_second_table(self):

        table = self.redactor.get_table(1)
        self.second_table_fill_common_info(table)
        # self.redactor.print_table(table)
        
        # по сути число договоров
        n_contracts = len(self.config["contracts_info"])

        # По смыслу, это количство уже заполненных строк в таблице. Начинаем не с 0, а с 1 потому что
        # в таблице есть заголовочная строка, в которой ничего заполнять не нужна, но она есть сама 
        # по себе и её нужно учитывать. По сути, значение n_row равно индексу строки, которую мы будем 
        # заполнять на текущей итерации
        n_rows = 1
        for i, contract in enumerate(self.config["contracts_info"]):

            if i < n_contracts - 1:
                self.third_table_clone_row(table, n_rows)

            # contract_number = list(self.config["table_info"].keys())[i]
            contract_number = self.config["contracts_info"][i][1]

            if self.config["table_info"][contract_number]["correcting_debt"] == "0,00":
                self.second_table_fill_simple_row(table, n_rows, i)
                n_rows += 1

            else:
                self.third_table_clone_row(table, n_rows)
                self.second_table_fill_complex_row(table, n_rows, i)
                n_rows += 2


    def second_table_fill_common_info(self, table: Table):
        self.redactor.replace_text_in_paragraph(
            table.row_cells(2)[2].paragraphs[0],
            self.borders("сумма долга"),
            self.config["table_info"]["all_debt"]
        )


    def second_table_fill_simple_row(self, table: Table, row_index: int, contract_index: int):
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[0].paragraphs[0],
            self.borders("номер договора"),
            self.config["contracts_info"][contract_index][1]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[1].paragraphs[0],
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["debt"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[3].paragraphs[0],
            self.borders("срок оплаты"),
            self.config["contracts_info"][contract_index][2]["last_day"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[4].paragraphs[0],
            self.borders("пункт"),
            self.config["contracts_info"][contract_index][2]["contract_point"]
        )


    def second_table_fill_complex_row(self, table: Table, row_index: int, contract_index: int):
        self.third_table_merge_rows(table, row_index)

        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[0].paragraphs[0],
            self.borders("номер договора"),
            self.config["contracts_info"][contract_index][1]
        )

        # Ячейка Период
        source_paragraph = table.row_cells(row_index)[1].paragraphs[0]
        new_paragraph = table.row_cells(row_index)[1].add_paragraph("")
        self.redactor.clone_paragraph(source_paragraph, new_paragraph)
        self.redactor.replace_text_in_paragraph(
            source_paragraph,
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods"]
        )
        self.redactor.replace_text_in_paragraph(
            new_paragraph,
            self.borders("период"),
            "текущие начисления"
        )
        self.redactor.paragraph_text_set_bold(new_paragraph)

        source_paragraph = table.row_cells(row_index + 1)[1].paragraphs[0]
        new_paragraph = table.row_cells(row_index + 1)[1].add_paragraph("")
        self.redactor.clone_paragraph(source_paragraph, new_paragraph)
        self.redactor.replace_text_in_paragraph(
            source_paragraph,
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods_correcting"]
        )
        self.redactor.replace_text_in_paragraph(
            new_paragraph,
            self.borders("период"),
            "доля от ГК"
        )
        self.redactor.paragraph_text_set_bold(new_paragraph)

        # Ячейка Задолженность
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["debt"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index + 1)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["correcting_debt"]
        )

        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[3].paragraphs[0],
            self.borders("срок оплаты"),
            self.config["contracts_info"][contract_index][2]["last_day"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[4].paragraphs[0],
            self.borders("пункт"),
            self.config["contracts_info"][contract_index][2]["contract_point"]
        )


    def fill_third_table(self):

        table = self.redactor.get_table(2)
        self.third_table_fill_common_info(table)
        # self.redactor.print_table(table)
        
        # по сути число договоров
        n_contracts = len(self.config["contracts_info"])

        # По смыслу, это количство уже заполненных строк в таблице. Начинаем не с 0, а с 1 потому что
        # в таблице есть заголовочная строка, в которой ничего заполнять не нужна, но она есть сама 
        # по себе и её нужно учитывать. По сути, значение n_row равно индексу строки, которую мы будем 
        # заполнять на текущей итерации
        n_rows = 1
        for i, contract in enumerate(self.config["contracts_info"]):

            if i < n_contracts - 1:
                self.third_table_clone_row(table, n_rows)

            # contract_number = list(self.config["table_info"].keys())[i]
            contract_number = self.config["contracts_info"][i][1]

            if self.config["table_info"][contract_number]["correcting_debt"] == "0,00":
                self.third_table_fill_simple_row(table, n_rows, i)
                n_rows += 1

            else:
                self.third_table_clone_row(table, n_rows)
                self.third_table_fill_complex_row(table, n_rows, i)
                n_rows += 2


    def third_table_fill_common_info(self, table: Table):
        # table = self.redactor.get_table(1)
        self.redactor.replace_text_in_paragraph(
            table.row_cells(2)[2].paragraphs[0],
            self.borders("сумма долга"),
            self.config["table_info"]["all_debt"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(2)[3].paragraphs[0],
            self.borders("неустойка общая"),
            self.config["table_info"]["all_penalty"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(2)[4].paragraphs[0],
            self.borders("цена иска"),
            self.config["table_info"]["cost_of_lawsuit"]
        )


    def third_table_clone_row(self, table: Table, cloning_row_index: int):
        new_row = self.redactor.insert_row_in_table(table, cloning_row_index + 1)
        self.redactor.clone_table_row(table.rows[cloning_row_index], new_row)


    def third_table_fill_simple_row(self, table: Table, row_index: int, contract_index: int):
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[0].paragraphs[0],
            self.borders("номер договора"),
            self.config["contracts_info"][contract_index][1]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[1].paragraphs[0],
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["debt"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[3].paragraphs[0],
            self.borders("неустойка"),
            self.config["contracts_info"][contract_index][2]["penalty"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[4].paragraphs[0],
            self.borders("неустойка+задолженность"),
            self.config["contracts_info"][contract_index][2]["debt_penalty"]
        )


    def third_table_fill_complex_row(self, table: Table, row_index: int, contract_index: int):
        self.third_table_merge_rows(table, row_index)

        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[0].paragraphs[0],
            self.borders("номер договора"),
            self.config["contracts_info"][contract_index][1]
        )

        # Ячейка Период
        source_paragraph = table.row_cells(row_index)[1].paragraphs[0]
        new_paragraph = table.row_cells(row_index)[1].add_paragraph("")
        self.redactor.clone_paragraph(source_paragraph, new_paragraph)
        self.redactor.replace_text_in_paragraph(
            source_paragraph,
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods"]
        )
        self.redactor.replace_text_in_paragraph(
            new_paragraph,
            self.borders("период"),
            "текущие начисления"
        )
        self.redactor.paragraph_text_set_bold(new_paragraph)

        source_paragraph = table.row_cells(row_index + 1)[1].paragraphs[0]
        new_paragraph = table.row_cells(row_index + 1)[1].add_paragraph("")
        self.redactor.clone_paragraph(source_paragraph, new_paragraph)
        self.redactor.replace_text_in_paragraph(
            source_paragraph,
            self.borders("период"),
            self.config["contracts_info"][contract_index][2]["contract_periods_correcting"]
        )
        self.redactor.replace_text_in_paragraph(
            new_paragraph,
            self.borders("период"),
            "доля от ГК"
        )
        self.redactor.paragraph_text_set_bold(new_paragraph)

        # Ячейка Задолженность
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["debt"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index + 1)[2].paragraphs[0],
            self.borders("задолженность"),
            self.config["contracts_info"][contract_index][2]["correcting_debt"]
        )

        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[3].paragraphs[0],
            self.borders("неустойка"),
            # "#неустойка#".upper()
            self.config["contracts_info"][contract_index][2]["penalty"]
        )
        self.redactor.replace_text_in_paragraph(
            table.row_cells(row_index)[4].paragraphs[0],
            self.borders("неустойка+задолженность"),
            # "#неустойка+задолженность#".upper()
            self.config["contracts_info"][contract_index][2]["debt_penalty"]
        )


    def third_table_merge_rows(self, table: Table, row_index: int):
        row_1 = table.rows[row_index]
        row_2 = table.rows[row_index + 1]
        for i in [0, 3, 4]:
            self.redactor.merge_table_cells(row_1.cells[i], row_2.cells[i])


    def fill_first_list(self):
        rows_n = len(self.config["contracts_info"]) # Кол-во элементов в списке договоров
        template_text = f"раздел {self.borders('номер раздела')}, в том числе пункт {self.borders('пункт')} договора {self.borders('номер договора')}"
        start = self.redactor.find_paragraph_consists_of_text(template_text)   # Индекс первого абзаца списка

        for i in range(rows_n):
            if i < rows_n - 1:
                src_p = self.redactor.get_paragraph(start + i)
                new_p = self.redactor.insert_paragraph(start + i + 1)
                self.redactor.clone_paragraph(src_p, new_p)

            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i),
                self.borders("номер раздела"),
                # "#номер раздела#".upper()
                self.config["contracts_info"][i][2]["contract_point"].split(".")[0]
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i),
                self.borders("пункт"),
                self.config["contracts_info"][i][2]["contract_point"]
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i),
                self.borders("номер договора"),
                self.config["contracts_info"][i][1]
            )


    def fill_second_list(self):
        rows_n = len(self.config["lawsuit_info"]["claims"]) # Кол-во элементов в списке претензий
        template_text = f"list{self.borders('номер претензии')};"
        start = self.redactor.find_paragraph_consists_of_text(template_text)   # Индекс первого абзаца списка

        for i in range(rows_n):
            if i < rows_n - 1:
                src_p = self.redactor.get_paragraph(start + i)
                new_p = self.redactor.insert_paragraph(start + i + 1)
                self.redactor.clone_paragraph(src_p, new_p)

            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i),
                template_text[:len(template_text) - 1],
                self.config["lawsuit_info"]["claims"][i]
            )


    def fill_third_list(self):
        rows_n = len(self.config["contracts_info"]) # Кол-во элементов в списке договоров
        template_text = "по Договору 05.403297-ТЭ от 01.08.2017:"
        start = self.redactor.find_paragraph_consists_of_text(template_text)   # Индекс первого абзаца списка

        # Список индексов тех параграфов, которые нужно удалить после цикла. Почему их нужно удалять?
        # Эти параграфы - это корректировка обязательств, которая есть не у всех договоров. Поэтому 
        # там где ее нет, параграфы удаляются
        delete_par_indices = []

        # Эта переменная нужна для подсчета числа заполненных строк в списке. Нельзя просто сделать
        # rows_n * stride, поскольку у некоторых договоров отсутствует годовая корректировка, и 
        # соответствующие параграфы удаляются из списка, т.е. строк становится меньше
        filled_rows = 0

        stride = 5
        for i in range(rows_n):
            if i < rows_n - 1:
                for j in range(stride):
                    src_p = self.redactor.get_paragraph(start + i * stride + j)
                    new_p = self.redactor.insert_paragraph(start + (i + 1) * stride + j)
                    self.redactor.clone_paragraph(src_p, new_p)

            # contract_number = list(self.config["table_info"].keys())[i]
            contract_number = self.config["contracts_info"][i][1]

            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride),
                "05.403297-ТЭ от 01.08.2017",
                # self.config["contracts_info"][i][1]
                contract_number
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 1),
                self.borders("задолженность"),
                # self.config["contracts_info"][i][2]["debt"]
                self.config["table_info"][contract_number]["debt"]
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 1),
                self.borders("период"),
                # self.config["contracts_info"][i][2]["contract_periods"]
                self.config["table_info"][contract_number]["contract_periods"]
            )

            if self.config["table_info"][contract_number]["contract_periods_correcting"] is not None:
                if self.config["table_info"][contract_number]["correcting_debt"] != "0,00":
                    self.redactor.replace_text_in_paragraph(
                        self.redactor.get_paragraph(start + i * stride + 2),
                        self.borders("доля годовой корректировки"),
                        # self.config["contracts_info"][i][2]["debt_penalty"]
                        self.config["table_info"][contract_number]["correcting_debt"]
                    )
                    self.redactor.replace_text_in_paragraph(
                        self.redactor.get_paragraph(start + i * stride + 2),
                        self.borders("период корректировки"),
                        # self.config["contracts_info"][i][2]["debt_penalty"]
                        self.config["table_info"][contract_number]["contract_periods_correcting"]
                    )
                else:
                    if start + i * stride + 2 not in delete_par_indices:
                        delete_par_indices.append(start + i * stride + 2)
            else:
                if start + i * stride + 2 not in delete_par_indices:
                    delete_par_indices.append(start + i * stride + 2)

            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 3),
                self.borders("неустойка"),
                # self.config["contracts_info"][i][2]["debt_penalty"]
                self.config["table_info"][contract_number]["penalty"]
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 3),
                self.borders("период неустойки 1"),
                # self.config["contracts_info"][i][2]["debt_penalty"]
                self.config["table_info"][contract_number]["penalty_period"].split(" по ")[0]
            )
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 3),
                self.borders("период неустойки 2"),
                # self.config["contracts_info"][i][2]["debt_penalty"]
                self.config["table_info"][contract_number]["penalty_period"].split(" по ")[1]
            )

            date_string = self.config["table_info"][contract_number]["penalty_period"].split(" по ")[1]
            format_string = "%d.%m.%Y"
            parsed_date = datetime.strptime(date_string, format_string)
            parsed_date_plus_1 = parsed_date + timedelta(days=1)
            self.redactor.replace_text_in_paragraph(
                self.redactor.get_paragraph(start + i * stride + 4),
                self.borders("начальная дата неустойки"),
                # self.config["contracts_info"][i][2]["debt_penalty"]
                parsed_date_plus_1.strftime(format_string)
            )

        delete_paragraps = 0
        for index in delete_par_indices:
            self.redactor.delete_paragraph(index - delete_paragraps)
            delete_paragraps += 1


    def fill_other_parts(self):
        to_replace = {
            "/*цена иска*/": self.config["lawsuit_info"]["cost"],
            "/*госпошлина*/": self.config["lawsuit_info"]["tax"],
            "/*истец полное имя*/": self.config["plaintiff_info"]["full_name"],
            "/*истец сокращенное имя*/": self.config["plaintiff_info"]["short_name"],
            "/*ответчик полное имя*/": self.config["defendant_info"]["full_name"],
            "/*ответчик сокращенное имя*/": self.config["defendant_info"]["short_name"],
            "/*тип договора*/": self.config["contract_types_templates"]["contract_type"],
            "/*тип договора2*/": self.config["contract_types_templates"]["contract_type2"],
            "/*сумма долга*/": self.config["table_info"]["all_debt"],
            "/*истец огрн*/": self.config["plaintiff_info"]["ogrn"],
            "/*истец инн*/": self.config["plaintiff_info"]["inn"],
            "/*ответчик огрн*/": self.config["defendant_info"]["ogrn"],
            "/*ответчик инн*/": self.config["defendant_info"]["inn"],
            "/*поставляемые ресурсы*/": self.config["contract_types_templates"]["supplied_resources"],
            "/*поставляемые ресурсы2*/": self.config["contract_types_templates"]["supplied_resources2"],
            "/*поставляемые ресурсы3*/": self.config["contract_types_templates"]["supplied_resources3"],
            "/*поставляемые ресурсы4*/": self.config["contract_types_templates"]["supplied_resources4"],
            "/*мн.ч.*/": self.config["contract_types_templates"]["plural_template_1"],
            "/*мн.ч.2*/": self.config["contract_types_templates"]["plural_template_2"],
            "/*мн.ч.3*/": self.config["contract_types_templates"]["plural_template_3"],
            "/*мн.ч.4*/": self.config["contract_types_templates"]["plural_template_4"],
            "/*мн.ч.5*/": self.config["contract_types_templates"]["plural_template_5"],
            "/*мн.ч.6*/": self.config["contract_types_templates"]["plural_template_6"],
        }
        for paragraph in self.doc.paragraphs:
            runs = []
            for run in paragraph.runs:
                runs.append(run.text)
                for k, v in to_replace.items():
                    if k in run.text:
                        run.text = run.text.replace(k, v)
            print(runs)
