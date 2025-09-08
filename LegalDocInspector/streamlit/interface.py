import requests
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from collections import defaultdict
from uuid import uuid4
import streamlit as st
import pandas as pd
from docx import Document

from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import parse_html
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty

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
        'contract_uploaded_file':None,
        'claim_uploaded_file':None,
        'debt_certificate_file':None
    }

def on_change_handler():
    st.session_state.form_data['forms_changed'] = True

def get_documents_complect_form(form_id:int, day_of_penalty: int | None = None, contract_uploaded_file = None, claim_uploaded_file = None, debt_certificate_file = None):
    st.markdown(f"### Набор {form_id}")

    # st.session_state.complects[form_id]['day_of_penalty'] = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
    #                                 value=18,
    #                                 min_value=1,
    #                                 max_value=31,
    #                                 key='day_of_penalty'+str(form_id))

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

def get_contract_form(contract_number:str):

    st.markdown(f"#### информация из договора {contract_number}")
    st.text(f"{st.session_state.contracts[contract_number]['overdue_date']}")
    st.text(f"{st.session_state.contracts[contract_number]['service_type']}")
    col1, col2 = st.columns(2)
    # st.json(st.session_state.contracts[contract_number])
    with col1:
        st.session_state.contracts[contract_number]['day_of_penalty'] = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
                                        value=18 ,
                                        min_value=1,
                                        max_value=31,
                                        key='day_of_penalty'+str(contract_number),
                                        on_change=on_change_handler)


    with col2:
        st.session_state.contracts[contract_number]['contract_point']  = st.text_input(label="напишите номер пункта договора, в котором говорится о дне начала просрочки ",
                                                                                      key="c_p"+str(contract_number),
                                                                                      on_change=on_change_handler)


st.title("Загрузка и обработка документов")


# Загрузчик файла

col1, col2 = st.columns(2)

with col1:
    date_selected = st.date_input("Выберите дату конца просрочки",
                                  format='DD.MM.YYYY',
                                  value= st.session_state.form_data['end_date'] if 'end_date' in st.session_state else 'today',
                                  on_change=on_change_handler)
    st.session_state.form_data['end_date'] = date_selected.strftime("%d.%m.%Y")
with col2:
    st.session_state.form_data['company_type'] = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"],
                                                              on_change=on_change_handler)

for form_num, form_info in st.session_state.complects.items():
    get_documents_complect_form(
        form_id=form_num,
        # day_of_penalty=form_info['day_of_penalty'],
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
            # 'day_of_penalty':18,
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


# st.json(st.session_state.complects)

if st.session_state.complects[st.session_state.form_data['num_complects']]['claim_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['contract_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['debt_certificate_file'] is not None:


    # Кнопка отправки
    if st.button("Отправить на сервер"):

        files = {}
        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
        }
        for complect_id, complect_info in st.session_state.complects.items():
            claim_uploaded_file = complect_info['claim_uploaded_file']
            contract_uploaded_file = complect_info['contract_uploaded_file']
            debt_certificate_file  = complect_info['debt_certificate_file']
            claim_uploaded_file.seek(0)
            contract_uploaded_file.seek(0)
            debt_certificate_file.seek(0)

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
            # st.json(response.json())


        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)


if st.session_state.form_data['flag']:
    result = st.session_state.form_data['result']
    i = 1
    if not "contracts" in st.session_state:
        st.session_state.contracts = {}
        for contract_info in result['table_parser_result']:
            contract_number = contract_info[1]
            overdue_date_info = contract_info[2]
            service_type_info = contract_info[3]
            claim_info = contract_info[4]
            # result['result_of_llm_parsers'] = {}
            # result['result_of_llm_parsers'][f"contract_{contract_number}"] = {
            #     "service_type":"тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))",
            #     "overdue_date":"В следующем фрагменте указан срок, в течение которого Исполнитель должен произвести оплату:\n\n\"5. 5. Исполнитель в срок до 18-го числа месяца, следующего за расчетным, производит оплату стоимости тепловой энергии, теплоносителя, указанной в счете. Датой оплаты считается дата поступления денежных средств на расчетный счет Теплоснабжающей организации.\"",
            # }
            # result['result_of_llm_parsers'][f"claim_0"] = {"claim_date":"17.10.2024","claim_number":"517305"}


            # json_info = result['result_of_llm_parsers'][f"contract_{contract_number}"]
            st.session_state.contracts[contract_number] = {
                'service_type': service_type_info,
                'overdue_date': overdue_date_info
            }
    # st.json(st.session_state.contracts)


    st.success("Файл успешно обработан!")
    st.text("Результат обработки документов")
    # st.json(result)

    st.markdown("## Заполение информации для генерациии иска (поля которые будут далее, можно отредактировать)")

    st.success("Пожалуйста, внимательно проверьте все пункты!")
    # for key, value in result['result_of_llm_parsers'].items():
    #     if "claim" in key:
    #         plaintiff_info_parsed = value['plaintiff_info']




    court_info = {}
    plaintiff_info = {}
    defendant_info = {}
    lawsuit_info = {}

    st.markdown("### Данные о месте проведения")
    court_info['name'] = st.text_input(label="Название Органа", value="Арбитражный суд города Москвы" , on_change=on_change_handler)
    court_info['addres'] = st.text_input(label="Адресс Органа", value="115225, г. Москва, ул. Большая Тульская, д. 17", on_change= on_change_handler)


    st.markdown("### Данные об Истце")
    # plaintiff_info['inn'] = st.text_input(label='ИНН Истца', value=f"{plaintiff_info_parsed['plaintiff_inn']}", on_change= on_change_handler)
    plaintiff_info['inn'] = st.text_input(label='ИНН Истца', value=f"7720518494", on_change= on_change_handler)

    if st.session_state.form_data['plaintiff_correct']:
        try:
            plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(plaintiff_info['inn'])

            plaintiff_info['full_name'] = st.text_input(label="Название Истца", value=f"{plaintiff_full_name}", key="full_name_1", on_change= on_change_handler)
            plaintiff_info['short_name'] = st.text_input(label="Название Истца(аббревиатура)", value=f"{plaintiff_short_name}", key="short_name_1", on_change= on_change_handler)
            plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f"{plaintiff_address}", key="addres_1", on_change= on_change_handler)
            plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value="121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613", key="cor_addr1", on_change= on_change_handler)
            plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f"{plaintiff_ogrn}", key="ogrn_1", on_change= on_change_handler)
        except Exception as e:
            st.error(e)
            st.session_state.form_data['plaintiff_correct'] = False
            st.markdown("К сожалению, не получилось получить данные об истце, проверьте ИНН, пожалуйста")

    if st.button(label="Обновить данные об истце") or st.session_state.form_data['plaintiff_uncorrect'] == True:
        st.session_state.form_data['plaintiff_correct'] = False
        try:
            plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(plaintiff_info['inn'])

            plaintiff_info['full_name'] = st.text_input(label="Название Истца", value=f"{plaintiff_full_name}", key="full_name_2", on_change= on_change_handler)
            plaintiff_info['short_name'] = st.text_input(label="Название Истца(аббревиатура)", value=f"{plaintiff_short_name}", key="short_name_2", on_change= on_change_handler)
            plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f"{plaintiff_address}", key="addr_2", on_change= on_change_handler)
            plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value="121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613", key="coraddr_2", on_change= on_change_handler)
            plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f"{plaintiff_ogrn}", key="ogrn_2", on_change= on_change_handler)
            if st.session_state.form_data['plaintiff_uncorrect'] ==False:
                st.session_state.form_data['plaintiff_uncorrect'] = True
                st.rerun()


        except Exception as e:
            st.error(e)
            st.markdown("К сожалению, не получилось получить данные об истце, проверьте ИНН, пожалуйста")


    st.markdown("### Данные об ответчике")


    defendant_info['full_name'] = st.text_input(label="Название ответчика", value=f"{result['results_of_name_parser']['defendant_info']['full_name']}", on_change= on_change_handler)
    defendant_info['short_name'] = st.text_input(label="Название ответчика(аббревиатура)", value=f"{result['results_of_name_parser']['defendant_info']['short_name']}", on_change= on_change_handler)
    defendant_info['addres'] = st.text_input(label="Адрес ответчика", value=f"{result['results_of_name_parser']['defendant_info']['address']}", on_change= on_change_handler)
    defendant_info['inn'] = st.text_input(label="ИНН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['inn']}", on_change= on_change_handler)
    defendant_info['ogrn'] = st.text_input(label="ОГРН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['ogrn']}", on_change= on_change_handler)



    # я хз ваще что теперь тут нейронка выдает
    st.markdown("### Данные о договорах")
    for contract_num, value in st.session_state.contracts.items():
        get_contract_form(contract_number=contract_num)
    calculator_list = {}
    if st.button("Произвести расчёты по загруженным наборам документов"):
        request_json  = {}
        request_json['company_type'] = st.session_state.form_data['company_type']
        request_json['end_date'] = st.session_state.form_data['end_date']
        request_json['parsing_results'] = []
        for contract_info in result['table_parser_result']:
            parsed_info  = contract_info[0]
            contract_number = contract_info[1]
            overdue_date_info = contract_info[2]
            service_type_info = contract_info[3]
            claim_info = contract_info[4]
            parsing_result = {}
            parsing_result['parsed_info'] = parsed_info
            parsing_result['contract_point'] = st.session_state.contracts[contract_number]['contract_point']
            parsing_result['day_of_penalty'] = st.session_state.contracts[contract_number]['day_of_penalty']
            parsing_result['contract_number'] = contract_number
            request_json['parsing_results'].append(parsing_result)

        with st.spinner(text="Ваш запрос обрабатывается, пожалуйста, подождите"):
            response = requests.post("http://localhost:5001/calculate_penalty",
                                    json=request_json
                                    )
        if response.status_code == 200:
            flag = True
            st.session_state.form_data['flag2'] = flag
            st.session_state.form_data['result2'] = response.json()
            st.json(response.json())


        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)

    # st.json(st.session_state.form_data)

if st.session_state.form_data['flag2']:
    st.success('Расчёты успешно произведены !')
    # st.json(st.session_state.form_data['result2'])

#     request_json = {}
    st.markdown("#### Проверьте данные об иске")

    st.session_state.form_data['lawsuit_info']['cost'] = st.text_input(label="Цена иска", value=f"{st.session_state.form_data['result2']['claim_data']['table_info']['cost_of_lawsuit']}", on_change= on_change_handler)

    st.session_state.form_data['lawsuit_info']['tax'] = st.text_input(label="Госпошлина", value=f"{calculate_state_duty(st.session_state.form_data['result2']['claim_data']['table_info']['cost_of_lawsuit'])}" , on_change= on_change_handler)
    st.session_state.form_data['lawsuit_info']['service_type'] = st.selectbox("Выберите вид услугии", ["ГВС + ТЭ", "ТЭ", "ГВС"])

#     service_type_info = []
    st.session_state.form_data['lawsuit_info']['claims'] = []
#     applications = {}

    for contract_info in result['table_parser_result']:
        claim_info = contract_info[4]
        st.session_state.form_data['lawsuit_info']['claims'].append(f"№ {claim_info['claim_number']} от {claim_info['claim_date']}")

#     st.markdown(f"### Данные об услуге, полученные из договоров")
#     st.markdown(f"{'___'.join(f' - {elem}' for elem in service_type_info)}")

#     st.markdown(f'### Данные о претензиях')
    claims_edit = []
    # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
    for i, claim in enumerate(st.session_state.form_data['lawsuit_info']['claims']):
        new_value = st.text_input(
            label=f"Претензия #{i + 1}",
            value=claim,
            key=f"claim_{i}",
            on_change= on_change_handler
        )
        claims_edit.append(new_value)
    st.session_state.form_data['lawsuit_info']['claims'] = claims_edit

    st.session_state.form_data['plaintiff_info'] = plaintiff_info

    st.session_state.form_data['defendant_info'] = defendant_info
#     lawsuit_info['claims'] = st.session_state.form_data['claims']


    request_json = st.session_state.form_data['result2']['claim_data']
    request_json['plaintiff_info'] = st.session_state.form_data['plaintiff_info']
    request_json['defendant_info'] = st.session_state.form_data['defendant_info']
    request_json['lawsuit_info'] = st.session_state.form_data['lawsuit_info']

    doc_creator_json = {}
    doc_creator_json['claim_data'] = request_json
    doc_creator_json['calculator_list'] = st.session_state.form_data['result2']['calculator_list']

    

    # print(doc_creator_json)
    st.markdown(f"### подтверждение данных и создание документов")
    if st.button(label="Нажмите, чтобы подтвердить правильность данных"):
            st.session_state.form_data['forms_changed'] = False
            first_response = requests.post("http://localhost:5001/create_doc",
                                json=doc_creator_json
                                )

            if first_response.status_code == 200:
                lawsuit = BytesIO(first_response.content)
                st.session_state.form_data['lawsuit'] = lawsuit



            else:
                st.error(f"Ошибка: {first_response.status_code}")
                st.text(first_response.text)

            second_response = requests.post("http://localhost:5001/create_calculating_table",
                                     json=doc_creator_json
                            )

            if second_response.status_code == 200:
                lawsuit_table = BytesIO(second_response.content)
                st.session_state.form_data['lawsuite_table'] = lawsuit_table
                st.session_state.form_data['flag2'] = True

            elif second_response.status_code == 404:
                st.error("Ошибка")
                # st.json(second_response.json())
            else:
                st.error(f"Ошибка: {second_response.status_code}")
                st.text(second_response.text)

if st.session_state.form_data['flag2'] and st.session_state.form_data['forms_changed']==False:
    col1, col2, = st.columns(2)

    with col1:
        st.download_button(
            label="Скачать иск",
            data=st.session_state.form_data['lawsuit'],
            file_name="Иск.docx",

        )

    with col2:
        st.download_button(
            label="Скачать расчёт к иску",
            data=st.session_state.form_data['lawsuite_table'],
            file_name="Расчёт к иску.docx",

        )

