"""
Модуль для извлечения данных из выписки из ЕГРЮЛ в формате PDF
"""
import logging
import re
from pathlib import Path
from io import StringIO
from typing import Dict, List, Optional

import pandas as pd

_log = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> tuple[str,str]:
    """
    Извлекает текст из текстового PDF документа без использования OCR.
    
    Args:
        pdf_path: Путь к PDF файлу
        
    Returns:
        Текст документа в виде строки
    """
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")
    
    text_content = ""
    # Резервный метод: используем docling без OCR (для текстовых PDF)
    try:
        import torch
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.base_models import ConversionStatus, InputFormat
        from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline
        
        pipeline_options = ThreadedPdfPipelineOptions(
            accelerator_options=AcceleratorOptions(
                device=AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU,
                num_threads=64
            ),
            ocr_batch_size=4,
            layout_batch_size=16,
            table_batch_size=4,
            do_ocr=False,  # Отключаем OCR для текстовых PDF
            do_table_structure=True,
            do_picture_description=False,
        )
        
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        
        doc_converter.initialize_pipeline(InputFormat.PDF)
        conv_result = doc_converter.convert(pdf_path)
        
        if conv_result.status != ConversionStatus.SUCCESS:
            raise RuntimeError(f"Ошибка конвертации документа: {pdf_path}")
        
        document = conv_result.document
        data = list(document.export_to_dict().values())
        if len(data) >= 8:
            text_blocks = data[7]
            for block in text_blocks:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    if text:
                        text_content += text + "\n\n"
        
        _log.info("Текст успешно извлечен из PDF с помощью docling (без OCR)")
        return text_content.strip(), document.export_to_markdown()
    
    except ImportError:
        raise ImportError(
            "Не установлена ни одна из библиотек для работы с PDF: PyPDF2, PyMuPDF или docling. "
            "Установите хотя бы одну: pip install PyPDF2 или pip install pymupdf"
        )
    except Exception as e:
        raise RuntimeError(f"Не удалось извлечь текст из PDF: {e}")


def parse_egrul_certificate(pdf_path: str | Path) -> tuple[Dict[str, str], str]:
    """
    Извлекает данные из выписки из ЕГРЮЛ в формате PDF.
    Для текстовых PDF использует прямое извлечение текста без OCR.
    
    Args:
        pdf_path: Путь к PDF файлу выписки из ЕГРЮЛ
        
    Returns:
        Кортеж из двух элементов:
        - Словарь с данными:
          {
              'full_name': str,      # Полное наименование организации
              'short_name': str,      # Сокращенное наименование организации
              'address': str,         # Адрес организации
              'kpp': str,            # КПП
              'ogrn': str            # ОГРН
          }
        - Markdown контент в виде строки
    """
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}")
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")
    
    _log.info(f"Начало обработки документа: {pdf_path}")
    
    # Извлечение текста из PDF без OCR
    text_content, text_md = extract_text_from_pdf(pdf_path)
    
    # Проверка, что текст был извлечен
    if not text_content or not text_content.strip():
        _log.warning("Предупреждение: извлеченный текст пуст или содержит только пробелы")
    
    _log.info(f"Извлечено символов текста: {len(text_content)}")
    
    # Форматирование текста как markdown
    # Простое форматирование: каждая строка текста становится параграфом
    res_list = extract_all_tables_to_dataframes(text_md)
    # Извлечение данных из текста
    address = get_table_info(res_list, "Адрес юридического лица")
    full_name = get_table_info(res_list, "Полное наименование на русском языке")
    short_name = get_table_info(res_list, "Сокращенное наименование на русском языке")
    kpp = get_table_info(res_list, "КПП юридического лица")
    ogrn = get_table_info(res_list, "ОГРН")
    
    result = {
        'full_name': full_name,      # Полное наименование организации
        'short_name': short_name,     # Сокращенное наименование организации
        'address': address,        # Адрес организации
        'kpp': kpp,            # КПП
        'ogrn': ogrn            # ОГРН
    }
    
    return replace_quotes(full_name), replace_quotes(short_name), clean_address(address), kpp, ogrn, text_content


def plaintiff_tuple_from_egrul_pdf(pdf_path: str | Path) -> tuple[str, str, str, str, str]:
    """
    Те же 5 полей, что у parse_html (itsoft): полное и сокращённое наименование, адрес, КПП, ОГРН.
    Использует уже загруженную выписку ЕГРЮЛ (PDF), как в /parse.
    """
    full_name, short_name, address, kpp, ogrn, _ = parse_egrul_certificate(pdf_path)
    if not (full_name or short_name):
        raise ValueError(
            "Не удалось извлечь наименование организации из PDF выписки ЕГРЮЛ. "
            "Убедитесь, что файл — выписка из ЕГРЮЛ и текст в PDF доступен для извлечения."
        )
    if not short_name and full_name:
        short_name = full_name
    if not full_name and short_name:
        full_name = short_name
    return full_name, short_name, address or "", kpp or "", ogrn or ""


def get_table_info(res_list:str, pattern) -> str:

    for df in res_list:
        # Строгое совпадение с учетом регистра
        matches = df[df.iloc[:, 1].astype(str) == pattern]
        
        if not matches.empty and len(df) > 2:
            first_match = str(matches.iloc[0, 2])
            return first_match
    
    return ""

def get_address_info_legacy(text_content: str) -> str:
    """
    Извлекает адрес юридического лица из текста выписки из ЕГРЮЛ.
    
    Адрес включает:
    - Почтовый индекс, расположенный на одной строке со словами "адрес юридического лица"
    - Последующие строки до строки "ГРН и дата внесения в ЕГРЮЛ записи"
    
    Args:
        text_content: Текст выписки из ЕГРЮЛ
        
    Returns:
        Адрес юридического лица в виде строки, или пустая строка, если адрес не найден
    """
    # Разбиваем текст на строки для обработки
    lines = text_content.split('\n')
    
    # Ищем строку с "Адрес юридического лица" и почтовым индексом
    # Почтовый индекс обычно состоит из 6 цифр
    address_start_idx = None
    
    for i, line in enumerate(lines):
        # Ищем строку, содержащую "Адрес юридического лица" и почтовый индекс (6 цифр)
        if re.search(r'Адрес юридического лица.*\d{6}', line, re.IGNORECASE):
            address_start_idx = i
            break
    
    if address_start_idx is None:
        _log.warning("Не найдена строка с адресом юридического лица")
        return ''
    
    # Извлекаем строку с адресом (начинается с "Адрес юридического лица" и индекса)
    address_lines = []
    
    # Начинаем с найденной строки
    current_line = lines[address_start_idx]
    
    # Извлекаем адрес из строки: убираем номер пункта и "Адрес юридического лица", оставляем индекс и остальное
    # Паттерн: номер пункта + "Адрес юридического лица" + индекс + остальное
    address_match = re.search(r'Адрес юридического лица\s*(\d{6}[,\s]?.*)', current_line, re.IGNORECASE)
    if address_match:
        # Извлекаем индекс и остальное содержимое строки
        address_part = address_match.group(1).strip()
        # Убираем запятую в конце, если есть
        address_part = address_part.rstrip(',')
        if address_part:
            address_lines.append(address_part)
    
    # Собираем последующие строки до строки "ГРН и дата внесения в ЕГРЮЛ записи"
    for i in range(address_start_idx + 1, len(lines)):
        line = lines[i].strip()
        
        # Проверяем, не достигли ли мы строки с "ГРН и дата внесения в ЕГРЮЛ записи"
        if re.search(r'ГРН и дата внесения в ЕГРЮЛ записи', line, re.IGNORECASE):
            break
        
        # Пропускаем пустые строки и строки только с дефисами
        if line and line not in ['-', '-,']:
            # Убираем запятые в конце строк
            line = line.rstrip(',')
            if line:
                address_lines.append(line)
    
    # Объединяем строки адреса
    if address_lines:
        # Объединяем через запятую и пробел, убирая лишние пробелы
        address = ', '.join(line.strip() for line in address_lines if line.strip())
        # Очищаем от множественных пробелов и запятых
        address = re.sub(r'\s+', ' ', address)
        address = re.sub(r',\s*,', ',', address)
        address = address.strip()
        
        _log.info(f"Извлечен адрес: {address[:100]}...")  # Логируем первые 100 символов
        return address
    else:
        _log.warning("Не удалось извлечь строки адреса")
        return ''


def get_full_name_info(text_content: str) -> str:
    """
    Извлекает полное наименование юридического лица из текста выписки из ЕГРЮЛ.
    
    Полное наименование начинается после слов "Полное наименование на русском языке"
    и продолжается до ближайшей строки со словами "ГРН и дата внесения в ЕГРЮЛ записи".
    
    Args:
        text_content: Текст выписки из ЕГРЮЛ
        
    Returns:
        Полное наименование юридического лица в виде строки, или пустая строка, если не найдено
    """
    # Разбиваем текст на строки для обработки
    lines = text_content.split('\n')
    
    # Ищем строку с "Полное наименование на русском языке"
    full_name_start_idx = None
    
    for i, line in enumerate(lines):
        # Ищем строку, содержащую "Полное наименование на русском языке"
        if re.search(r'Полное наименование на русском языке', line, re.IGNORECASE):
            full_name_start_idx = i
            break
    
    if full_name_start_idx is None:
        _log.warning("Не найдена строка с полным наименованием на русском языке")
        return ''
    
    # Извлекаем полное наименование
    full_name_lines = []
    
    # Начинаем с найденной строки
    current_line = lines[full_name_start_idx]
    
    # Извлекаем текст после "Полное наименование на русском языке"
    # Паттерн: номер пункта + "Полное наименование на русском языке" + название
    name_match = re.search(r'Полное наименование на русском языке\s*(.+)', current_line, re.IGNORECASE)
    if name_match:
        # Извлекаем название из текущей строки
        name_part = name_match.group(1).strip()
        if name_part:
            full_name_lines.append(name_part)
    
    # Собираем последующие строки до строки "ГРН и дата внесения в ЕГРЮЛ записи"
    for i in range(full_name_start_idx + 1, len(lines)):
        line = lines[i].strip()
        
        # Проверяем, не достигли ли мы строки с "ГРН и дата внесения в ЕГРЮЛ записи"
        if re.search(r'ГРН и дата внесения в ЕГРЮЛ записи', line, re.IGNORECASE):
            break
        
        # Пропускаем пустые строки
        if line:
            # Убираем лишние пробелы и добавляем строку
            line = line.strip()
            if line:
                full_name_lines.append(line)
    
    # Объединяем строки полного наименования
    if full_name_lines:
        # Объединяем через пробел, убирая лишние пробелы
        full_name = ' '.join(line.strip() for line in full_name_lines if line.strip())
        # Очищаем от множественных пробелов
        full_name = re.sub(r'\s+', ' ', full_name)
        full_name = full_name.strip()
        
        _log.info(f"Извлечено полное наименование: {full_name[:100]}...")  # Логируем первые 100 символов
        return full_name
    else:
        _log.warning("Не удалось извлечь строки полного наименования")
        return ''


def get_short_name_info(text_content: str) -> str:
    """
    Извлекает сокращённое наименование юридического лица из текста выписки из ЕГРЮЛ.
    
    Сокращённое наименование начинается после слов "Сокращённое наименование на русском языке"
    и продолжается до ближайшей строки со словами "ГРН и дата внесения в ЕГРЮЛ записи".
    
    Args:
        text_content: Текст выписки из ЕГРЮЛ
        
    Returns:
        Сокращённое наименование юридического лица в виде строки, или пустая строка, если не найдено
    """
    # Разбиваем текст на строки для обработки
    lines = text_content.split('\n')
    
    # Ищем строку с "Сокращенное наименование на русском"
    # Текст может быть разбит на две строки: "Сокращенное наименование на русском" и "языке..."
    short_name_start_idx = None
    
    for i, line in enumerate(lines):
        # Ищем строку, содержащую "Сокращенное наименование на русском"
        if re.search(r'Сокращенное наименование на русском', line, re.IGNORECASE):
            short_name_start_idx = i
            break
    
    if short_name_start_idx is None:
        _log.warning("Не найдена строка с сокращенным наименованием на русском языке")
        return ''
    
    # Извлекаем сокращённое наименование
    short_name_lines = []
    
    # Проверяем следующую строку, которая должна начинаться с "языке"
    if short_name_start_idx + 1 < len(lines):
        next_line = lines[short_name_start_idx + 1].strip()
        
        # Извлекаем текст после "языке" (может быть без пробела)
        # Паттерн: "языке" + сокращенное наименование
        name_match = re.search(r'языке\s*(.+)', next_line, re.IGNORECASE)
        if name_match:
            # Извлекаем сокращенное наименование
            name_part = name_match.group(1).strip()
            if name_part:
                short_name_lines.append(name_part)
        else:
            # Если паттерн не сработал, пробуем просто взять всю строку после "языке"
            # Иногда может быть "языкеООО" без пробела
            if re.search(r'языке', next_line, re.IGNORECASE):
                # Разделяем по "языке" и берем вторую часть
                parts = re.split(r'языке', next_line, flags=re.IGNORECASE, maxsplit=1)
                if len(parts) > 1:
                    name_part = parts[1].strip()
                    if name_part:
                        short_name_lines.append(name_part)
    
    # Собираем последующие строки до строки "ГРН и дата внесения в ЕГРЮЛ записи"
    # Начинаем со строки после "языке"
    start_idx = short_name_start_idx + 2 if short_name_start_idx + 1 < len(lines) else short_name_start_idx + 1
    
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        
        # Проверяем, не достигли ли мы строки с "ГРН и дата внесения в ЕГРЮЛ записи"
        if re.search(r'ГРН и дата внесения в ЕГРЮЛ записи', line, re.IGNORECASE):
            break
        
        # Пропускаем пустые строки
        if line:
            # Убираем лишние пробелы и добавляем строку
            line = line.strip()
            if line:
                short_name_lines.append(line)
    
    # Объединяем строки сокращённого наименования
    if short_name_lines:
        # Объединяем через пробел, убирая лишние пробелы
        short_name = ' '.join(line.strip() for line in short_name_lines if line.strip())
        # Очищаем от множественных пробелов
        short_name = re.sub(r'\s+', ' ', short_name)
        short_name = short_name.strip()
        
        _log.info(f"Извлечено сокращённое наименование: {short_name[:100]}...")  # Логируем первые 100 символов
        return short_name
    else:
        _log.warning("Не удалось извлечь строки сокращённого наименования")
        return ''


def get_kpp_info(text_content: str) -> str:
    """
    Извлекает КПП (код причины постановки на учет) юридического лица из текста выписки из ЕГРЮЛ.
    
    КПП - это число, следующее после строки "КПП юридического лица".
    КПП обычно состоит из 9 цифр.
    
    Args:
        text_content: Текст выписки из ЕГРЮЛ
        
    Returns:
        КПП юридического лица в виде строки, или пустая строка, если не найдено
    """
    # Разбиваем текст на строки для обработки
    lines = text_content.split('\n')
    
    # Ищем строку с "КПП юридического лица"
    kpp_line = None
    
    for line in lines:
        # Ищем строку, содержащую "КПП юридического лица"
        if re.search(r'КПП юридического лица', line, re.IGNORECASE):
            kpp_line = line
            break
    
    if kpp_line is None:
        _log.warning("Не найдена строка с КПП юридического лица")
        return ''
    
    # Извлекаем КПП из строки
    # Паттерн: "КПП юридического лица" + пробелы + число (обычно 9 цифр)
    kpp_match = re.search(r'КПП юридического лица\s+(\d{9})', kpp_line, re.IGNORECASE)
    
    if kpp_match:
        kpp = kpp_match.group(1)
        _log.info(f"Извлечен КПП: {kpp}")
        return kpp
    else:
        # Пробуем более гибкий паттерн на случай, если формат немного отличается
        # Ищем любое число после "КПП юридического лица"
        kpp_match = re.search(r'КПП юридического лица\s+(\d+)', kpp_line, re.IGNORECASE)
        if kpp_match:
            kpp = kpp_match.group(1)
            _log.info(f"Извлечен КПП (гибкий паттерн): {kpp}")
            return kpp
        else:
            _log.warning(f"Не удалось извлечь КПП из строки: {kpp_line}")
            return ''


def get_ogrn_info(text_content: str) -> str:
    """
    Извлекает ОГРН (основной государственный регистрационный номер) юридического лица 
    из текста выписки из ЕГРЮЛ.
    
    ОГРН - это число, следующее после первого включения в текст строки "ОГРН ".
    ОГРН юридического лица обычно состоит из 13 цифр.
    
    Args:
        text_content: Текст выписки из ЕГРЮЛ
        
    Returns:
        ОГРН юридического лица в виде строки, или пустая строка, если не найдено
    """
    # Ищем первое вхождение "ОГРН " в тексте
    # Используем регулярное выражение для поиска первого вхождения
    ogrn_match = re.search(r'ОГРН\s+(\d{13,15})', text_content, re.IGNORECASE)
    
    if ogrn_match:
        ogrn = ogrn_match.group(1)
        _log.info(f"Извлечен ОГРН: {ogrn}")
        return ogrn
    else:
        # Пробуем более гибкий паттерн на случай, если формат немного отличается
        # Ищем любое число после первого "ОГРН "
        ogrn_match = re.search(r'ОГРН\s+(\d+)', text_content, re.IGNORECASE)
        if ogrn_match:
            ogrn = ogrn_match.group(1)
            _log.info(f"Извлечен ОГРН (гибкий паттерн): {ogrn}")
            return ogrn
        else:
            _log.warning("Не найдена строка с ОГРН")
            return ''

def replace_quotes(text:str):
    text = re.sub(r'"([^"]*)"', r'«\1»', text)
    return text

def clean_address(text: str) -> str:
    
    text = re.sub(r',\s*,', ',', text)        
    text = re.sub(r'\s+,', ',', text)          
    text = re.sub(r',(?=[^ \w])', '', text)    
    text = re.sub(r'\s+', ' ', text).strip() 
    return text

def find_all_md_tables(md_text: str) -> List[str]:
    """
    Находит все markdown таблицы в тексте
    Возвращает список строк с таблицами
    """
    tables = []
    
    # Более точное регулярное выражение для поиска таблиц
    # Ищет блоки, где есть хотя бы одна строка-разделитель
    pattern = r'((?:^\|.*\|\s*$\n)+)'
    
    lines = md_text.split('\n')
    current_block = []
    in_table = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Проверяем, начинается ли строка с | и не является ли кодом
        if stripped.startswith('|') and not stripped.startswith('|```') and '```|' not in stripped:
            # Проверяем, является ли это строкой-разделителем таблицы
            is_separator = bool(re.match(r'^\|[-:\s|]+\|$', stripped.replace(' ', '')))
            
            if not in_table:
                # Начало новой таблицы
                in_table = True
                current_block = [stripped]
            else:
                # Продолжение таблицы
                current_block.append(stripped)
                
                # Если это разделитель и мы уже собрали заголовок
                if is_separator and len(current_block) >= 2:
                    # Проверяем следующие строки
                    j = i + 1
                    while j < len(lines) and lines[j].strip().startswith('|'):
                        current_block.append(lines[j].strip())
                        j += 1
                    
                    tables.append('\n'.join(current_block))
                    current_block = []
                    in_table = False
                    continue
        elif in_table and not stripped:
            # Пустая строка внутри таблицы - допустимо
            continue
        elif in_table:
            # Конец таблицы
            if len(current_block) > 1:
                # Проверяем, что в блоке есть разделитель
                has_separator = any(
                    re.match(r'^\|[-:\s|]+\|$', line.replace(' ', '')) 
                    for line in current_block
                )
                if has_separator:
                    tables.append('\n'.join(current_block))
            current_block = []
            in_table = False
    
    return tables

def parse_md_table(table_text: str) -> Optional[pd.DataFrame]:
    """
    Парсит отдельную markdown таблицу в DataFrame
    """
    try:
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        # Убедимся, что это таблица (есть строка-разделитель)
        has_separator = False
        clean_lines = []
        
        for line in lines:
            # Пропускаем строки-разделители для pandas
            if re.match(r'^\|[-:\s|]+\|$', line.replace(' ', '')):
                has_separator = True
                continue
            clean_lines.append(line)
        
        if not has_separator or len(clean_lines) < 2:
            return None
        
        # Парсим с помощью pandas
        df = pd.read_csv(StringIO('\n'.join(clean_lines)), sep='|')
        
        # Очистка и валидация
        if df.empty:
            return None
        
        # Удаляем пробелы
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Удаляем полностью пустые колонки
        df = df.dropna(axis=1, how='all')
        
        # Удаляем пустые колонки по краям
        if df.columns[0] == '':
            df = df.iloc[:, 1:]
        if not df.empty and df.columns[-1] == '':
            df = df.iloc[:, :-1]
        
        # Проверяем, что остались данные
        if df.empty or len(df.columns) == 0:
            return None
        
        return df
        
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {e}")
        return None

def extract_all_tables_to_dataframes(md_text: str) -> List[pd.DataFrame]:
    """
    Основная функция: извлекает все таблицы и конвертирует в DataFrames
    """
    tables_text = find_all_md_tables(md_text)
    dataframes = []
    
    # print(f"Найдено таблиц в тексте: {len(tables_text)}")
    
    for i, table_text in enumerate(tables_text, 1):
        # print(f"\n{'='*50}")
        # print(f"Обработка таблицы {i}:")
        # print(table_text[:200] + "..." if len(table_text) > 200 else table_text)
        
        df = parse_md_table(table_text)
        if df is not None:
            dataframes.append(df)
            # print(f"Успешно создан DataFrame с формой: {df.shape}")
        else:
            print("Не удалось создать DataFrame")
    
    return dataframes