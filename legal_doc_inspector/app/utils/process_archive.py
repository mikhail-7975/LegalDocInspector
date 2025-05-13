from pathlib import Path

from legal_doc_inspector.doc_parser.table_parser import TableParser

def process_files_from_folder(path_to_folder:Path):

    parser = TableParser()
    tables =  path_to_folder.rglob('*.XLS')
    pdf_files = path_to_folder.rglob('*.pdf')
    docx_files = path_to_folder.rglob('*.docx')

    for excel_table in tables:
        result_dict = parser.parse_excel_table(excel_table)


