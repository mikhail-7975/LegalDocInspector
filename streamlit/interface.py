import requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from collections import defaultdict

import streamlit as st
import pandas as pd
from docx import Document

from legal_doc_inspector.app.utils.parse_info_by_inn import parse_html
from legal_doc_inspector.app.utils.calculate_tax import calculate_state_duty

if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'court_info': {},
        'plaintiff_info': {},
        'defendant_info': {},
        'lawsuit_info': {},
        'service_type_info': [],
        'claims': [],
        'result': {},
        'flag':False,
        'flag2':False,
        'plaintiff_correct':True,
        'plaintiff_uncorrect':False,
        'forms_changed': False,
        'num_complects': 1
    }

if 'complects' not in st.session_state:
    st.session_state.complects = {}
    st.session_state.complects[st.session_state.form_data['num_complects']] = {
        'day_of_penalty':18,
        'contract_uploaded_file':None,
        'claim_uploaded_file':None,
        'debt_certificate_file':None
    }

def on_change_handler():
    st.session_state.form_data['forms_changed'] = True

def get_documents_complect_form(form_id:int, day_of_penalty: int | None = None, contract_uploaded_file = None, claim_uploaded_file = None, debt_certificate_file = None):
    st.markdown(f"### Набор {form_id}")
    
    st.session_state.complects[form_id]['day_of_penalty'] = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
                                    value=18,
                                    min_value=1,
                                    max_value=31,
                                    key='day_of_penalty'+str(form_id))

    st.text("Поле для договора")
    st.session_state.complects[form_id]['contract_uploaded_file'] = st.file_uploader("Выберите Документ с договором",
                                            accept_multiple_files=False,
                                            key='contract_uploaded_file'+str(form_id))
    st.text("Поле для претензии")
    st.session_state.complects[form_id]['claim_uploaded_file'] = st.file_uploader("Выберите Документ с претензией", 
                                           accept_multiple_files=False,
                                           key='claim_uploaded_file'+str(form_id))
    st.text("Поле для Excel справки о задожленности")
    st.session_state.complects[form_id]['debt_certificate_file'] = st.file_uploader("Выберите Excel справку о задолженности",
                                            accept_multiple_files=False,
                                            key='debt_certificate_file'+str(form_id))

st.title("Загрузка и обработка документов")


# Загрузчик файла

col1, col2 = st.columns(2)

with col1:
    date_selected = st.date_input("Выберите дату конца просрочки",
                                  format='DD.MM.YYYY')

with col2:
    company_type = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"])

for form_num, form_info in st.session_state.complects.items():
    get_documents_complect_form(
        form_id=form_num,
        day_of_penalty=form_info['day_of_penalty'],
        claim_uploaded_file=form_info['claim_uploaded_file'],
        contract_uploaded_file=form_info['contract_uploaded_file'],
        debt_certificate_file=form_info['debt_certificate_file']
    )
col1, col2 = st.columns(2)
with col1 :
    if st.button("➕ Добавить набор документов"):
        if 'num_complects' not in st.session_state.form_data:
            st.session_state.form_data['num_complects'] = 1
        else:
            st.session_state.form_data['num_complects'] += 1
            st.session_state.complects[st.session_state.form_data['num_complects']] = {
            'day_of_penalty':18,
            'contract_uploaded_file':None,
            'claim_uploaded_file':None,
            'debt_certificate_file':None
        }
            st.rerun()

with col2:
    if st.button("➖ Убрать набор документов"):
        if  st.session_state.form_data['num_complects'] == 1:
            st.session_state.form_data['num_complects'] = 1
            st.error('Должен быть хотя бы один набор')
        else:
            del st.session_state.complects[st.session_state.form_data['num_complects']]
            st.session_state.form_data['num_complects'] -= 1
            st.rerun()


st.json(st.session_state.complects)

if st.session_state.complects[st.session_state.form_data['num_complects']]['claim_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['contract_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['debt_certificate_file'] is not None:    

    
    # Кнопка отправки
    if st.button("Отправить на сервер"):
        
        files = {}
        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
            "company_type": company_type,
        }
        for complect_id, complect_info in st.session_state.complects.items():
            day_of_penalty = complect_info['day_of_penalty']
            claim_uploaded_file = complect_info['claim_uploaded_file']
            contract_uploaded_file = complect_info['contract_uploaded_file']
            debt_certificate_file  = complect_info['debt_certificate_file']
            claim_uploaded_file.seek(0)
            contract_uploaded_file.seek(0)
            debt_certificate_file.seek(0)

            data[f'complect_{complect_id}_day_of_penalty'] = str(day_of_penalty)
            files[f'complect_{complect_id}_claim_file'] = (claim_uploaded_file.name, claim_uploaded_file)
            files[f'complect_{complect_id}_contract_file'] = (contract_uploaded_file.name, contract_uploaded_file)
            files[f'complect_{complect_id}_certificate_file'] = (debt_certificate_file.name, debt_certificate_file)

        data['complects_count'] = str(complect_id)

        
        
        with st.spinner(text="Ваш запрос обрабатывается, пожалуйста, подождите"):
            response = requests.post("http://localhost:5001/parse",
                                    files=files,
                                    data= data
                                    )
        if response.status_code == 200:
            flag = True
            st.session_state.form_data['flag'] = flag
            st.session_state.form_data['result'] = response.json()
            st.json(response.json())

        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)

        
# if st.session_state.form_data['flag']:
#     result = st.session_state.form_data['result']

    

#     st.success("Файл успешно обработан!")
#     # st.text("Результат обработки документов")
#     # st.json(result)

#     st.markdown("## Заполение информации для генерациии иска (поля которые будут далее, можно отредактировать)")

#     st.success("Пожалуйста, внимательно проверьте все пункты!")
#     for key, value in result['result_of_llm_parsers'].items():
#         if "claim" in key:
#             plaintiff_info_parsed = value['plaintiff_info']




#     court_info = {}
#     plaintiff_info = {}
#     defendant_info = {}
#     lawsuit_info = {}

#     st.markdown("### Данные о месте проведения")
#     court_info['name'] = st.text_input(label="Название Органа", value="Арбитражный суд города Москвы" , on_change=on_change_handler)
#     court_info['addres'] = st.text_input(label="Адресс Органа", value="115225, г. Москва, ул. Большая Тульская, д. 17", on_change= on_change_handler)

    
#     st.markdown("### Данные об Истце")
#     plaintiff_info['inn'] = st.text_input(label='ИНН Истца', value=f"{plaintiff_info_parsed['plaintiff_inn']}", on_change= on_change_handler)
#     if st.session_state.form_data['plaintiff_correct']:
#         try:
#             plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(plaintiff_info_parsed['plaintiff_inn'])

#             plaintiff_info['full_name'] = st.text_input(label="Название Истца", value=f"{plaintiff_full_name}", key="full_name_1", on_change= on_change_handler)
#             plaintiff_info['short_name'] = st.text_input(label="Название Истца(аббревиатура)", value=f"{plaintiff_short_name}", key="short_name_1", on_change= on_change_handler)
#             plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f"{plaintiff_address}", key="addres_1", on_change= on_change_handler)
#             plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value="121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613 (МГКА «КДЗП»)", key="cor_addr1", on_change= on_change_handler)
#             plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f"{plaintiff_ogrn}", key="ogrn_1", on_change= on_change_handler)
#         except Exception as e:
#             st.error(e)
#             st.session_state.form_data['plaintiff_correct'] = False
#             st.markdown("К сожалению, не получилось получить данные об истце, проверьте ИНН, пожалуйста")

#     if st.button(label="Обновить данные об истце") or st.session_state.form_data['plaintiff_uncorrect'] == True:
#         st.session_state.form_data['plaintiff_correct'] = False
#         try:
#             plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(plaintiff_info['inn'])

#             plaintiff_info['full_name'] = st.text_input(label="Название Истца", value=f"{plaintiff_full_name}", key="full_name_2", on_change= on_change_handler)
#             plaintiff_info['short_name'] = st.text_input(label="Название Истца(аббревиатура)", value=f"{plaintiff_short_name}", key="short_name_2", on_change= on_change_handler)
#             plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f"{plaintiff_address}", key="addr_2", on_change= on_change_handler)
#             plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value="121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613 (МГКА «КДЗП»)", key="coraddr_2", on_change= on_change_handler)
#             plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f"{plaintiff_ogrn}", key="ogrn_2", on_change= on_change_handler)
#             if st.session_state.form_data['plaintiff_uncorrect'] ==False:
#                 st.session_state.form_data['plaintiff_uncorrect'] = True
#                 st.rerun()
                
            
#         except Exception as e:
#             st.error(e)
#             st.markdown("К сожалению, не получилось получить данные об истце, проверьте ИНН, пожалуйста")
            

#     st.markdown("### Данные об ответчике")
#     #все эти данные надо парсить
#     defendant_info['full_name'] = st.text_input(label="Название ответчика", value=f"{result['results_of_name_parser']['defendant_info']['full_name']}", on_change= on_change_handler)
#     defendant_info['short_name'] = st.text_input(label="Название ответчика(аббревиатура)", value=f"{result['results_of_name_parser']['defendant_info']['short_name']}", on_change= on_change_handler)
#     defendant_info['addres'] = st.text_input(label="Адрес ответчика", value=f"{result['results_of_name_parser']['defendant_info']['address']}", on_change= on_change_handler)
#     defendant_info['inn'] = st.text_input(label="ИНН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['inn']}", on_change= on_change_handler)
#     defendant_info['ogrn'] = st.text_input(label="ОГРН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['ogrn']}", on_change= on_change_handler)
    
#     st.markdown("### Данные о договорах")
#     contracts = []
#     request_json = {}
    
#     lawsuit_info['cost'] = st.text_input(label="Цена иска", value=f"{result['contracts_info']['cost_of_lawsuit']} р.", on_change= on_change_handler)
#     lawsuit_info['tax'] = st.text_input(label="Госпошлина", value=f"{calculate_state_duty(result['contracts_info']['cost_of_lawsuit'])} р." , on_change= on_change_handler)
#     lawsuit_info['last_day'] = st.text_input(label = "Срок оплаты", value=f'До {day_of_penalty} числа месяца, следующего за расчётным', on_change= on_change_handler)
    
#     service_type_info = []
#     claims = []
#     applications = {}

#     for key, value in result['result_of_llm_parsers'].items():
#         if "contract" in key:
#             service_type_info.append(result['result_of_llm_parsers'][key]['service_type'])
#         if "claim" in key:
#             claims.append(f"№ {result['result_of_llm_parsers'][key]['claim_number']} от {result['result_of_llm_parsers'][key]['claim_date']}")
#         if "zip" in key:
#             applications = value
#     st.markdown(f"### Данные об услуге, полученные из договоров")
#     st.markdown(f"{'___'.join(f' - {elem}' for elem in service_type_info)}")
#     lawsuit_info['service_type'] = st.selectbox("Выберите вид услугии", ["ГВС + ТЭ", "ТЭ", "ГВС"])

#     st.markdown(f'### Данные о претензиях')
#     claims_edit = []
#     # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
#     for i, claim in enumerate(claims):
#         new_value = st.text_input(
#             label=f"Претензия #{i + 1}",
#             value=claim,
#             key=f"claim_{i}",
#             on_change= on_change_handler
#         )
#         claims_edit.append(new_value)
#     st.session_state.form_data['claims'] = claims_edit
#     lawsuit_info['claims'] = st.session_state.form_data['claims']
    
#     st.markdown("### Данные о приложенных документах")

#     applications_edit = {}
#     # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
#     for application_path, application_name in applications.items():
#         new_value = st.text_input(
#             label=f"{Path(application_path).name}",
#             value=application_name,
#             key=f"application_{Path(application_path).name}",
#             on_change= on_change_handler
#         )
#         applications_edit[f"{Path(application_path).name}"] = new_value
#     st.session_state.form_data['applications_info'] = applications_edit
#     person_info = {}
#     st.markdown("### Данные об ответственном лице")
#     col3, col4 = st.columns(2)

#     with col3:
#         person_info['vacancy'] = st.text_input(label = "Должность", value=f'Представитель ПАО «МОЭК» по доверенности', on_change= on_change_handler)

#     with col4:
#         person_info['name'] = st.text_input(label = "ФИО", value=f'Самошкина А.Е.', on_change= on_change_handler)



#     request_json['person_info'] = person_info
#     request_json['applications_info'] = st.session_state.form_data['applications_info']
#     request_json['table_info'] = result['contracts_info']
#     request_json['court_info'] = court_info
#     request_json['plaintiff_info'] = plaintiff_info
#     request_json['defendant_info'] = defendant_info
#     request_json['lawsuit_info'] = lawsuit_info
#     request_json['files_info'] = result['files_table']



#     st.markdown(f"### подтверждение данных")
#     if st.button(label="Нажмите, чтобы подтвердить правильность данных"):
#             st.session_state.form_data['forms_changed'] = False
#             first_response = requests.post("http://localhost:5001/create_doc",
#                                 json=request_json
#                                 )
            
#             if first_response.status_code == 200:
#                 lawsuit = BytesIO(first_response.content)
#                 st.session_state.form_data['lawsuit'] = lawsuit

                
            
#             else:
#                 st.error(f"Ошибка: {first_response.status_code}")
#                 st.text(first_response.text)

#             second_response = requests.post("http://localhost:5001/create_calculating_table",
#                                      json=request_json['files_info']
#                             )
            
#             if second_response.status_code == 200:
#                 lawsuit_table = BytesIO(second_response.content)
#                 st.session_state.form_data['lawsuite_table'] = lawsuit_table
#                 st.session_state.form_data['flag2'] = True
            
#             elif second_response.status_code == 404:
#                 st.error("Ошибка")
#                 st.json(second_response.json())
#             else:
#                 st.error(f"Ошибка: {second_response.status_code}")
#                 st.text(second_response.text)

#             # with col1:
#             #     if st.button(label="Создать Иск"):
# if st.session_state.form_data['flag2'] and st.session_state.form_data['forms_changed']==False:             
#     col1, col2, = st.columns(2)

#     with col1:
#         st.download_button(
#             label="Скачать иск",
#             data=st.session_state.form_data['lawsuit'],
#             file_name="Иск.docx",
            
#         )

#     with col2:
#         st.download_button(
#             label="Скачать расчёт к иску",
#             data=st.session_state.form_data['lawsuite_table'],
#             file_name="Расчёт к иску.docx",
            
#         )

