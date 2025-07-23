import requests
from datetime import datetime, date
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import streamlit as st
import pandas as pd
from docx import Document

from legal_doc_inspector.app.utils.parse_info_by_inn import parse_html
from legal_doc_inspector.app.utils.calculate_tax import calculate_state_duty

if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'court_info': {},
        
        'lawsuit_info': {},
        'service_type_info': [],
        'claims': [],
        'result': {},
        'flag':False,
        'flag2':False,
        'plaintiff_correct':True,
        'plaintiff_uncorrect':False,
        'defendant_correct':True,
        'defendant_uncorrect':False,
        'forms_changed': False,
        'need_parse_plaintiff_info':True,
        'need_parse_defendant_info':True
    }

def on_change_handler():
    st.session_state.form_data['forms_changed'] = True


st.title("LegalDocInspector: Альфа-версия")

# Загрузчик файла

col1, col2 = st.columns(2)

with col1:
    date_selected = st.date_input("Выберите дату конца просрочки",
                                  format='DD.MM.YYYY',
                                  on_change=on_change_handler)

with col2:
    day_of_penalty = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
                                     value=18,
                                     min_value=1,
                                     max_value=31,
                                     on_change=on_change_handler)

company_type = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"],
                            on_change=on_change_handler)

st.text("Поле для договора")
contract_uploaded_file = st.file_uploader("Выберите Документ с договором", accept_multiple_files=True)
st.text("Поле для претензии")
claim_uploaded_file = st.file_uploader("Выберите Документ с претензией", accept_multiple_files=True)
st.text("Поле для Excel справки о задожленности")
debt_certificate_file = st.file_uploader("Выберите Excel справку о задолженности", accept_multiple_files=True)
st.text("Поле для ZIP архива с приложением к иску")
zip_uploaded_file = st.file_uploader("Выберите ZIP файл")

if zip_uploaded_file is not None or len(claim_uploaded_file)!=0 or len(contract_uploaded_file)!=0 or len(debt_certificate_file) !=0:    

    files = {}


    # Кнопка отправки
    if st.button("Отправить на сервер"):
        # Восстанавливаем указатель файла
        if zip_uploaded_file:
            zip_uploaded_file.seek(0)
            files["zip_file"] = (zip_uploaded_file.name, zip_uploaded_file)

        if claim_uploaded_file:
            if isinstance(claim_uploaded_file, list):
                for i, file in enumerate(claim_uploaded_file):
                    file.seek(0)
                    files[f'claim_file_{i}'] = (file.name, file)
            else:
                claim_uploaded_file.seek(0)
                files["claim_file"] = (claim_uploaded_file.name, claim_uploaded_file)
            

        if contract_uploaded_file:
            if isinstance(contract_uploaded_file, list):
                for i, file in enumerate(contract_uploaded_file):
                    file.seek(0)
                    files[f'contract_file_{i}'] = (file.name, file)
            else:
                contract_uploaded_file.seek(0)
                files['contract_file'] = (contract_uploaded_file.name, contract_uploaded_file)
            
        
        if debt_certificate_file:
            if isinstance(debt_certificate_file, list):
                for i, file in enumerate(debt_certificate_file):
                    file.seek(0)
                    files[f'certificate_file_{i}'] = (file.name, file)
            else:
                debt_certificate_file.seek(0)
                files["certificate_file"] = (debt_certificate_file.name, debt_certificate_file)
        
        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
            "company_type": company_type,
            "day_of_penalty":day_of_penalty
        }

        if len(files) < 1:
            st.error("Загружены не все файлы")

        
        else:
            with st.spinner(text="Ваш запрос обрабатывается, пожалуйста, подождите"):
                response = requests.post("http://localhost:5001/parse",
                                        files=files,
                                        data= data
                                        )
            if response.status_code == 200:
                flag = True
                st.session_state.form_data['flag'] = flag
                st.session_state.form_data['result'] = response.json()


            else:
                st.error(f"Ошибка: {response.status_code}")
                st.text(response.text)

        
if st.session_state.form_data['flag']:
    result = st.session_state.form_data['result']

    

    st.success("Файл успешно обработан!")
    # st.text("Результат обработки документов")
    # st.json(result)

    st.markdown("## Заполнение информации для генерациии иска (поля, которые будут далее, можно отредактировать)")

    st.success("Пожалуйста, внимательно проверьте все пункты!")
    for key, value in result['result_of_llm_parsers'].items():
        if "claim" in key:
            plaintiff_info_parsed = value['plaintiff_info']




    court_info = {}
    plaintiff_info = {}
    defendant_info = {}
    lawsuit_info = {}

    st.markdown("### Данные о месте проведения")
    court_info['name'] = st.text_input(label="Название Органа", value="Арбитражный суд города Москвы" , on_change=on_change_handler)
    court_info['addres'] = st.text_input(label="Адрес Органа", value="115225, г. Москва, ул. Большая Тульская, д. 17", on_change= on_change_handler)

        
    
    st.markdown("### Данные об Истце")
    plaintiff_info['inn'] = st.text_input(label='ИНН Истца', value=f"{plaintiff_info_parsed['plaintiff_inn']}", on_change= on_change_handler)
    if not 'plaintiff_info' in st.session_state.form_data:
        try:
            print('идёт первый запрос истец')
            plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(plaintiff_info_parsed['plaintiff_inn'])
            plaintiff_info['full_name'] = plaintiff_full_name
            plaintiff_info['short_name'] = plaintiff_short_name
            plaintiff_info['addres'] = plaintiff_address
            plaintiff_info['correspondency_addres'] = "121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613 (МГКА «КДЗП»)"
            plaintiff_info['ogrn'] = plaintiff_ogrn
            st.session_state.form_data['plaintiff_info'] = plaintiff_info
        except Exception as e :
            print(e)
            st.error("К сожалению, не удалось получить данные об истце, проверьте ИНН, пожалуйста")
    plaintiff_edit_info = st.session_state.form_data['plaintiff_info']

    plaintiff_info['full_name'] = st.text_input(label="Название Истца", value=f"{plaintiff_edit_info['full_name']}", key="full_name_1", on_change= on_change_handler)
    plaintiff_info['short_name'] = st.text_input(label="Название Истца(аббревиатура)", value=f"{plaintiff_edit_info['short_name']}", key="short_name_1", on_change= on_change_handler)
    plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f"{plaintiff_edit_info['addres']}", key="addres_1", on_change= on_change_handler)
    plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value=f"{plaintiff_edit_info['correspondency_addres']}", key="cor_addr1", on_change= on_change_handler)
    plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f"{plaintiff_edit_info['ogrn']}", key="ogrn_1", on_change= on_change_handler)
    st.session_state.form_data['plaintiff_info'] = plaintiff_info

    if st.button(label="Обновить данные об истце"):
       
        try:
            plaintiff_full_name, plaintiff_short_name, plaintiff_address, plaintiff_kpp, plaintiff_ogrn = parse_html(st.session_state.form_data['plaintiff_info']['inn'])
            plaintiff_info['full_name'] = plaintiff_full_name
            plaintiff_info['short_name'] = plaintiff_short_name
            plaintiff_info['addres'] = plaintiff_address
            plaintiff_info['correspondency_addres'] = f"{st.session_state.form_data['plaintiff_info']['correspondency_addres']}"
            plaintiff_info['ogrn'] = plaintiff_ogrn
            st.session_state.form_data['plaintiff_info'] = plaintiff_info
            print('идёт запрос истец по кнопке')

        except Exception as e:
            # st.error(e)
            print(e)
            st.error("К сожалению, не удалось получить данные об истце, проверьте ИНН, попробуйте ещё раз, пожалуйста")
                
            


    st.markdown("### Данные об ответчике")
    defendant_info['inn'] = st.text_input(label="ИНН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['inn']}", on_change= on_change_handler)
    if not 'defendant_info' in st.session_state.form_data:
        try:
            print("запрос ответчик первый")
            full_name, short_name, address, kpp, ogrn = parse_html(result['results_of_name_parser']['defendant_info']['inn'])
            defendant_info['full_name'] = full_name
            defendant_info['short_name'] = short_name
            defendant_info['addres'] = address 
            defendant_info['ogrn'] = ogrn
            st.session_state.form_data['defendant_info'] = defendant_info
        except Exception as e:
            print(e)
            st.error("К сожалению, не удалось получить данные об ответчике, проверьте ИНН, пожалуйста")

    defendant_edit_info = st.session_state.form_data['defendant_info']
    defendant_info['full_name'] = st.text_input(label="Название ответчика", value=f"{defendant_edit_info['full_name']}", on_change= on_change_handler)
    defendant_info['short_name'] = st.text_input(label="Название ответчика(аббревиатура)", value=f"{defendant_edit_info['short_name']}", on_change= on_change_handler)
    defendant_info['addres'] = st.text_input(label="Адрес ответчика", value=f"{defendant_edit_info['addres']}", on_change= on_change_handler)
    defendant_info['ogrn'] = st.text_input(label="ОГРН ответчика", value=f"{defendant_edit_info['ogrn']}", on_change= on_change_handler)
    st.session_state.form_data['defendant_info'] = defendant_info
    if st.button(label="Обновить данные об ответчике"):
        try:
            print("запрос ответчик по кнопке")
            full_name, short_name, address, kpp, ogrn = parse_html(st.session_state.form_data['defendant_info']['inn'])
            defendant_info['full_name'] = full_name
            defendant_info['short_name'] = short_name
            defendant_info['addres'] = address
            defendant_info['ogrn'] = ogrn
            st.session_state.form_data['defendant_info'] = defendant_info
                
            
        except Exception as e:
            # st.error(e)
            print(e)
            st.error("К сожалению, не удалось получить данные об ответчике, проверьте ИНН, попробуйте ещё раз, пожалуйста")

    st.markdown("### Данные о договорах")
    if 'contracts' not in st.session_state.form_data:
        contracts = []
        
        for key, value in result['contracts_info'].items():
            if "№" in key:

                contracts.append((str(uuid4()), key, value))
        st.session_state.form_data['contracts'] = contracts
    
    st.markdown("### Результаты работы нейросети")
    contract_data = []
    for  key, value in result['result_of_llm_parsers'].items():
        if "contract" in key:
            st.markdown(f"### {result['result_of_llm_parsers'][key]['path_name']} \n {result['result_of_llm_parsers'][key]['overdue_date']}")

    contracts = st.session_state.form_data['contracts']

    st.markdown("### редактирование информации о договорах \n (нажатие на кнопки ⬆️ и ⬇️ изменяет порядок договоров в иске)")
    for i in range(len(contracts)):
        uid, name, content = contracts[i]
        st.write("")
        st.markdown(f"**{name}**")
        col1, col2 = st.columns([1, 4])
        with col1:
            st.write("")  # Отступ сверху для центровки
            if st.button("⬆️", use_container_width=True, key=f"contract_up_{uid}"):
                if i>0:
                    on_change_handler()
                    contracts[i], contracts[i-1] = contracts[i-1], contracts[i]
                    st.session_state.form_data['contracts'] = contracts
                    st.rerun()
            if st.button("⬇️", use_container_width=True, key=f"contract_down_{uid}"):
                if i<len(contracts)-1:
                    on_change_handler()
                    contracts[i],contracts[i+1] = contracts[i+1],contracts[i]
                    st.session_state.form_data['contracts'] = contracts
                    st.rerun()
        with col2:
            content['last_day'] = st.text_input(label="число месяца, после которого следует просрочка", value=f"{'До 18 числа месяца, следующего за расчётным' if 'last_day' not in content else content['last_day']}", on_change=on_change_handler, key=f"day_last_{uid}")
            content['contract_point'] = st.text_input(label="пункт договора", value=f"{'5.5' if 'contract_point' not in content else content['contract_point']}", on_change=on_change_handler, key=f"point_contract_{uid}")
    st.session_state.form_data['contracts'] = contracts

    request_json = {}
    
    lawsuit_info['cost'] = st.text_input(label="Цена иска", value=f"{result['contracts_info']['cost_of_lawsuit']} руб.", on_change= on_change_handler)
    lawsuit_info['tax'] = st.text_input(label="Госпошлина", value=f"{calculate_state_duty(result['contracts_info']['cost_of_lawsuit'])} руб." , on_change= on_change_handler)
    
    service_type_info = []
    claims = []
    applications = {}

    for key, value in result['result_of_llm_parsers'].items():
        if "contract" in key:
            service_type_info.append(result['result_of_llm_parsers'][key]['service_type'])
        if "claim" in key:
            claims.append(f"№ {result['result_of_llm_parsers'][key]['claim_number']} от {result['result_of_llm_parsers'][key]['claim_date']}")
        if "zip" in key:
            applications = value
    
    st.markdown(f"### Данные об услуге, полученные из договоров")
    st.markdown(f"{'___'.join(f' - {elem}' for elem in service_type_info)}")
    lawsuit_info['service_type'] = st.selectbox("Выберите вид услуги", ["ГВС + ТЭ", "ТЭ", "ГВС"], on_change=on_change_handler)
    
    st.markdown(f'### Данные о претензиях')
    claims_edit = []
    # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
    for i, claim in enumerate(claims):
        new_value = st.text_input(
            label=f"Претензия #{i + 1}",
            value=claim,
            key=f"claim_{i}",
            on_change= on_change_handler
        )
        claims_edit.append(new_value)
    st.session_state.form_data['claims'] = claims_edit
    lawsuit_info['claims'] = st.session_state.form_data['claims']
    
    st.markdown("### Данные о приложенных документах")

    if 'apps_edit' not in st.session_state.form_data:
        applications_edit = []
        number = 1
        
        for key, value in applications.items():
            
            applications_edit.append((str(uuid4()), key, value))

        st.session_state.form_data['apps_edit'] = applications_edit


    # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
    applications_edit = st.session_state.form_data['apps_edit']
    
    for i in range(len(applications_edit)):
        uid, path, content = applications_edit[i]
        name = Path(path).name
        st.write("")
        st.markdown(f"**{name}**")
        col1, col2 = st.columns([1, 4])
        with col1:
            st.write("")  # Отступ сверху для центровки
            if st.button("⬆️", use_container_width=True, key=f"app_up_{uid}"):
                if i>0:
                    on_change_handler()
                    applications_edit[i], applications_edit[i-1] = applications_edit[i-1], applications_edit[i]
                    st.session_state.form_data['apps_edit'] = applications_edit
                    st.rerun()
            if st.button("⬇️", use_container_width=True, key=f"app_down_{uid}"):
                if i<len(applications_edit)-1:
                    on_change_handler()
                    applications_edit[i], applications_edit[i+1] = applications_edit[i+1], applications_edit[i]
                    st.session_state.form_data['apps_edit'] = applications_edit
                    st.rerun()
        with col2:
            content = st.text_input(label=f"{name}", value=f"{content}", on_change=on_change_handler, key=f"day_last_{uid}")
            

        
    st.session_state.form_data['applications_info'] = applications_edit
    person_info = {}
    st.markdown("### Данные об ответственном лице")
    col3, col4 = st.columns(2)

    with col3:
        person_info['vacancy'] = st.text_input(label = "Должность", value=f'Представитель ПАО «МОЭК» по доверенности', on_change= on_change_handler)

    with col4:
        person_info['name'] = st.text_input(label = "ФИО", value=f'Самошкина А.Е.', on_change= on_change_handler)

    request_json['company_type'] = company_type
    request_json['current_date'] =  date_selected.strftime("%Y-%m-%d")
    request_json['contracts_info'] = st.session_state.form_data['contracts']
    request_json['person_info'] = person_info
    request_json['applications_info'] = st.session_state.form_data['applications_info']
    request_json['court_info'] = court_info
    request_json['plaintiff_info'] = st.session_state.form_data['plaintiff_info']
    request_json['defendant_info'] = st.session_state.form_data['defendant_info']
    request_json['lawsuit_info'] = lawsuit_info
    request_json['files_info'] = result['files_table']
    request_json['table_info'] = result['contracts_info']
    request_json['results_of_data_saving'] = result['results_of_data_saving']
    request_json['parsing_table_result'] = result['parsing_table_result']

    st.markdown(f"### подтверждение данных")
    if st.button(label="Нажмите, чтобы подтвердить правильность данных"):
            st.session_state.form_data['forms_changed'] = False
            first_response = requests.post("http://localhost:5001/create_doc",
                                json=request_json
                                )
            
            if first_response.status_code == 200:
                lawsuit = BytesIO(first_response.content)
                st.session_state.form_data['lawsuit'] = lawsuit

                
            
            else:
                st.error(f"Ошибка: {first_response.status_code}")
                st.text(first_response.text)

            second_response = requests.post("http://localhost:5001/create_calculating_table",
                                    json=request_json
                            )
            
            if second_response.status_code == 200:
                lawsuit_table = BytesIO(second_response.content)
                st.session_state.form_data['lawsuite_table'] = lawsuit_table
                st.session_state.form_data['flag2'] = True
            
            elif second_response.status_code == 404:
                st.error("Ошибка")
                st.json(second_response.json())
            else:
                st.error(f"Ошибка: {second_response.status_code}")
                st.text(second_response.text)

            # with col1:
            #     if st.button(label="Создать Иск"):
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

