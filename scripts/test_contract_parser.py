#!/usr/bin/env python3
"""
Скрипт для тестирования PDFContractParser:
- Извлечение текста из PDF
- Сохранение текста в файл
- Проверка работы метода analyse_contract
"""
import argparse
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Добавляем путь к корню проекта для импорта модулей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import PDFContractParser


def extract_text_from_html(html_content: str) -> str:
    """
    Извлекает чистый текст из HTML контента.
    
    Args:
        html_content: HTML строка
        
    Returns:
        Чистый текст без HTML тегов
    """
    soup = BeautifulSoup(html_content, 'lxml')
    # Удаляем скрипты и стили
    for script in soup(["script", "style"]):
        script.decompose()
    # Получаем текст
    text = soup.get_text()
    # Очищаем от лишних пробелов и переносов строк
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text


def main():
    parser = argparse.ArgumentParser(
        description='Тестирование PDFContractParser: извлечение текста из PDF и анализ договора',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python scripts/test_contract_parser.py /path/to/contract.pdf
  python scripts/test_contract_parser.py /path/to/contract.pdf --output-text output.txt
  python scripts/test_contract_parser.py /path/to/contract.pdf --output-html output.html
        """
    )
    
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Путь к PDF файлу договора'
    )
    
    parser.add_argument(
        '--output-text', '-t',
        type=str,
        default=None,
        help='Путь для сохранения извлеченного текста (по умолчанию: {pdf_name}.txt)'
    )
    
    parser.add_argument(
        '--output-html',
        type=str,
        default=None,
        help='Путь для сохранения HTML представления документа (опционально)'
    )
    
    parser.add_argument(
        '--no-analysis',
        action='store_true',
        help='Пропустить анализ договора (только извлечение текста)'
    )
    
    args = parser.parse_args()
    
    # Проверка существования файла
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Ошибка: Файл не найден: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"Предупреждение: Файл не имеет расширения .pdf: {pdf_path}", file=sys.stderr)
    
    try:
        print("=" * 70)
        print(f"Обработка файла: {pdf_path}")
        print("=" * 70)
        
        # Создание парсера
        print("\n1. Инициализация PDFContractParser...")
        contract_parser = PDFContractParser(device='cpu')
        print("   ✓ Парсер инициализирован")
        
        # Извлечение текста
        print("\n2. Извлечение текста из PDF...")
        document = contract_parser._parse_contract_text(pdf_path)
        print("   ✓ Текст извлечен")
        
        # Получение HTML представления
        html_content = document.export_to_html()
        
        # Определение путей для сохранения
        if args.output_text:
            text_output_path = Path(args.output_text)
        else:
            text_output_path = pdf_path.parent / f"{pdf_path.stem}_extracted.txt"
        
        if args.output_html:
            html_output_path = Path(args.output_html)
        else:
            html_output_path = None
        
        # Извлечение чистого текста из HTML
        print("\n3. Обработка HTML и извлечение текста...")
        extracted_text = extract_text_from_html(html_content)
        print(f"   ✓ Извлечено символов: {len(extracted_text)}")
        
        # Сохранение текста
        print(f"\n4. Сохранение текста в файл: {text_output_path}")
        text_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(text_output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        print(f"   ✓ Текст сохранен: {text_output_path}")
        
        # Сохранение HTML (если указано)
        if html_output_path:
            print(f"\n5. Сохранение HTML в файл: {html_output_path}")
            html_output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   ✓ HTML сохранен: {html_output_path}")
        
        # Анализ договора
        if not args.no_analysis:
            print("\n6. Анализ договора (analyse_contract)...")
            print("   Выполняется поиск точки просрочки и типа услуги...")
            point_of_contract, type_of_service = contract_parser.analyse_contract(pdf_path)
            
            print("\n" + "=" * 70)
            print("РЕЗУЛЬТАТЫ АНАЛИЗА:")
            print("=" * 70)
            print(f"\nТочка просрочки (point_of_contract):")
            print("-" * 70)
            print(point_of_contract)
            print(f"\nТип услуги (type_of_service):")
            print("-" * 70)
            print(type_of_service)
            print("=" * 70)
        else:
            print("\n6. Анализ договора пропущен (--no-analysis)")
        
        print("\n✓ Готово!")
        
    except FileNotFoundError as e:
        print(f"\nОшибка: Файл не найден: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"\nОшибка конвертации: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nНеожиданная ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

