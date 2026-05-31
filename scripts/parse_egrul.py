#!/usr/bin/env python3
"""
Скрипт для извлечения данных из выписки из ЕГРЮЛ в формате PDF
"""
import argparse
import json
import sys
from pathlib import Path

# Добавляем путь к корню проекта для импорта модулей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import parse_egrul_certificate


def main():
    parser = argparse.ArgumentParser(
        description='Извлечение данных из выписки из ЕГРЮЛ в формате PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python scripts/parse_egrul.py /path/to/egrul_certificate.pdf
  python scripts/parse_egrul.py /path/to/egrul_certificate.pdf --output result.json
  python scripts/parse_egrul.py /path/to/egrul_certificate.pdf --pretty
        """
    )
    
    parser.add_argument(
        'pdf_path',
        type=str,
        default="data/input_examples/комплект 1/Документы для иска/04.303360-ТЭ/ul-1047796974092-20251210152907.pdf",
        help='Путь к PDF файлу выписки из ЕГРЮЛ'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Путь для сохранения результата в JSON формате (опционально)'
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Красивый вывод JSON с отступами'
    )
    
    parser.add_argument(
        '--markdown-path',
        type=str,
        default="/home/user/projects/LegalDocInspector/egrul_certificate.md",
        help='Путь для сохранения markdown файла (по умолчанию сохраняется рядом с PDF)'
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
        print(f"Обработка файла: {pdf_path}")
        print("Конвертация PDF в markdown...")
        
        # Вызов функции парсинга
        result, markdown_content = parse_egrul_certificate(pdf_path)
        
        # Определение пути для markdown файла
        if args.markdown_path:
            markdown_path = Path(args.markdown_path)
        else:
            markdown_path = pdf_path.parent / f"{pdf_path.stem}.md"
        
        # Сохранение markdown файла
        try:
            # Убеждаемся, что директория существует
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем файл
            with open(markdown_path, 'w', encoding='utf-8') as f:
                bytes_written = f.write(markdown_content)
                f.flush()
                import os
                if hasattr(f, 'fileno'):
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
            
            # Проверка существования файла
            if markdown_path.exists():
                file_size = markdown_path.stat().st_size
                print(f"Markdown файл сохранен: {markdown_path} (размер: {file_size} байт)")
            else:
                print(f"Ошибка: Markdown файл не был создан: {markdown_path}", file=sys.stderr)
        
        except Exception as e:
            print(f"Ошибка при сохранении markdown файла: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        print("\nИзвлеченные данные:")
        print("=" * 50)
        
        # Вывод результатов
        for key, value in result.items():
            label = {
                'full_name': 'Полное наименование',
                'short_name': 'Сокращенное наименование',
                'address': 'Адрес',
                'kpp': 'КПП',
                'ogrn': 'ОГРН'
            }.get(key, key)
            print(f"{label:30}: {value if value else '(не заполнено)'}")
        
        print("=" * 50)
        
        # Сохранение в JSON файл, если указан путь
        if args.output:
            output_path = Path(args.output)
            indent = 2 if args.pretty else None
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=indent)
            print(f"\nРезультат сохранен в JSON: {output_path}")
        
        # Вывод JSON в консоль, если не указан файл вывода
        elif args.pretty:
            print("\nJSON результат:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\nГотово!")
        
    except FileNotFoundError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Ошибка конвертации: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

