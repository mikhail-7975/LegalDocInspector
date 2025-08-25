"""
Главный модуль Streamlit приложения для обработки юридических документов.
Чистая архитектура с разделением ответственности между компонентами.
"""

import logging

from components import (
    ApplicationsComponent,
    ClaimsComponent,
    CourtInfoComponent,
    DefendantInfoComponent,
    DocumentDownloadComponent,
    FileUploadComponent,
    LawsuitInfoComponent,
    PersonInfoComponent,
    PlaintiffInfoComponent,
)
from models import FormData, ProcessingStage
from services import APIError, ApplicationStateService, DocumentProcessingService

import streamlit as st

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Главная функция приложения."""
    try:
        app_state = ApplicationStateService.get_state()

        # Этап 1: Загрузка и обработка файлов
        if app_state.stage == ProcessingStage.INITIAL:
            handle_file_upload(app_state)

        # Этап 2: Заполнение форм после парсинга
        elif app_state.stage == ProcessingStage.DOCUMENTS_PARSED:
            handle_form_filling(app_state)

        # Этап 3: Скачивание готовых документов
        elif app_state.stage == ProcessingStage.DOCUMENTS_GENERATED:
            handle_document_download(app_state)

    except Exception as e:
        logger.error(f"Ошибка в главной функции: {e}")
        st.error(f"Произошла непредвиденная ошибка: {e}")
        # Сбрасываем состояние при критической ошибке
        if st.button("Начать заново"):
            ApplicationStateService.update_state(stage=ProcessingStage.INITIAL)
            st.rerun()


def handle_file_upload(app_state):
    """Обрабатывает этап загрузки файлов."""
    date_selected, payment_day, company_type, files = FileUploadComponent.render()

    # Показываем кнопку отправки только если есть файлы
    if files.has_files():
        if st.button("Отправить на сервер", type="primary"):
            process_uploaded_files(
                app_state, files, date_selected, payment_day, company_type
            )
    else:
        st.info("Пожалуйста, загрузите хотя бы один файл для продолжения")


def process_uploaded_files(app_state, files, date_selected, payment_day, company_type):
    """Обрабатывает загруженные файлы через API."""
    form_data = FormData(
        date=date_selected.strftime("%Y-%m-%d"),
        company_type=company_type,
        day_of_penalty=payment_day,
    )

    with st.spinner("Обрабатываем документы, пожалуйста подождите..."):
        try:
            result = DocumentProcessingService.parse_documents(files, form_data)

            ApplicationStateService.update_state(
                parsed_result=result, stage=ProcessingStage.DOCUMENTS_PARSED
            )

            st.success("Документы успешно обработаны!")
            st.rerun()

        except APIError as e:
            logger.error(f"Ошибка API при обработке файлов: {e}")
            st.error(f"Ошибка сервера: {e.message}")
            if e.status_code == 0:
                st.error("Проверьте подключение к серверу")

        except ValueError as e:
            st.error(f"Ошибка данных: {e}")

        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке файлов: {e}")
            st.error(f"Произошла ошибка при обработке: {e}")


def handle_form_filling(app_state):
    """Обрабатывает этап заполнения форм."""
    st.success("Документы успешно обработаны!")
    st.markdown("## Заполнение информации для генерации иска")
    st.info(
        "Пожалуйста, внимательно проверьте все поля и отредактируйте при необходимости"
    )

    parsed_data = app_state.parsed_result or {}

    # Рендерим все компоненты форм
    app_state.court_info = CourtInfoComponent.render(app_state.court_info)

    app_state.plaintiff_info = PlaintiffInfoComponent.render(
        app_state.plaintiff_info, parsed_data
    )

    app_state.defendant_info = DefendantInfoComponent.render(
        app_state.defendant_info, parsed_data
    )

    # Получаем payment_day из parsed_data или используем значение по умолчанию
    payment_day = 18  # Можно извлечь из parsed_data если нужно
    app_state.lawsuit_info = LawsuitInfoComponent.render(
        app_state.lawsuit_info, parsed_data, payment_day
    )

    app_state.claims_edit = ClaimsComponent.render(app_state.claims_edit, parsed_data)

    app_state.applications_info = ApplicationsComponent.render(
        app_state.applications_info, parsed_data
    )

    app_state.person_info = PersonInfoComponent.render(app_state.person_info)

    # Кнопка подтверждения данных
    st.markdown("### Подтверждение данных")
    if st.button("Создать документы", type="primary"):
        generate_documents(app_state, parsed_data)


def generate_documents(app_state, parsed_data):
    """Генерирует итоговые документы."""
    # Подготавливаем данные для API
    request_data = prepare_document_request_data(app_state, parsed_data)

    with st.spinner("Генерируем документы..."):
        try:
            # Создаем иск
            lawsuit_document = DocumentProcessingService.create_lawsuit_document(
                request_data
            )

            # Создаем таблицу расчетов
            files_info = parsed_data.get("files_table", {})
            lawsuit_table = DocumentProcessingService.create_calculation_table(
                files_info
            )

            # Сохраняем документы в состоянии
            ApplicationStateService.update_state(
                lawsuit_document=lawsuit_document,
                lawsuit_table=lawsuit_table,
                stage=ProcessingStage.DOCUMENTS_GENERATED,
                forms_changed=False,
            )

            st.success("Документы успешно созданы!")
            st.rerun()

        except APIError as e:
            logger.error(f"Ошибка API при создании документов: {e}")
            if e.status_code == 404:
                st.error("Не удалось создать таблицу расчетов")
                st.json({"error": e.message})
            else:
                st.error(f"Ошибка сервера: {e.message}")

        except Exception as e:
            logger.error(f"Ошибка при создании документов: {e}")
            st.error(f"Произошла ошибка при создании документов: {e}")


def prepare_document_request_data(app_state, parsed_data):
    """Подготавливает данные для запроса создания документа."""
    return {
        "person_info": {
            "vacancy": app_state.person_info.position,
            "name": app_state.person_info.name,
        },
        "applications_info": app_state.applications_info,
        "table_info": parsed_data.get("contracts_info", {}),
        "court_info": {
            "name": app_state.court_info.name,
            "addres": app_state.court_info.address,  # Оставляем 'addres' для совместимости с API
        },
        "plaintiff_info": {
            "inn": app_state.plaintiff_info.inn,
            "full_name": app_state.plaintiff_info.full_name,
            "short_name": app_state.plaintiff_info.short_name,
            "addres": app_state.plaintiff_info.address,  # Оставляем 'addres' для совместимости с API
            "correspondency_addres": app_state.plaintiff_info.correspondence_address,
            "ogrn": app_state.plaintiff_info.ogrn,
        },
        "defendant_info": {
            "full_name": app_state.defendant_info.full_name,
            "short_name": app_state.defendant_info.short_name,
            "addres": app_state.defendant_info.address,  # Оставляем 'addres' для совместимости с API
            "inn": app_state.defendant_info.inn,
            "ogrn": app_state.defendant_info.ogrn,
        },
        "lawsuit_info": {
            "cost": app_state.lawsuit_info.cost,
            "tax": app_state.lawsuit_info.tax,
            "last_day": app_state.lawsuit_info.last_day,
            "service_type": app_state.lawsuit_info.service_type,
            "claims": app_state.claims_edit,
        },
        "files_info": parsed_data.get("files_table", {}),
    }


def handle_document_download(app_state):
    """Обрабатывает этап скачивания документов."""
    # Показываем формы только если они не изменились
    if not app_state.forms_changed:
        DocumentDownloadComponent.render(
            app_state.lawsuit_document, app_state.lawsuit_table
        )

        # Кнопка для создания новых документов
        if st.button("Создать новые документы"):
            ApplicationStateService.update_state(stage=ProcessingStage.INITIAL)
            st.rerun()
    else:
        st.warning("Данные формы были изменены. Пожалуйста, пересоздайте документы.")
        if st.button("Пересоздать документы"):
            ApplicationStateService.update_state(stage=ProcessingStage.DOCUMENTS_PARSED)
            st.rerun()


if __name__ == "__main__":
    main()
