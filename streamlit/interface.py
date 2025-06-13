import requests
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import streamlit as st
import pandas as pd
from docx import Document



st.title("Загрузка и обработка документов")

# Загрузчик файла

col1, col2 = st.columns(2)

with col1:
    date_selected = st.date_input("Выберите дату конца просрочки",
                                  format='DD.MM.YYYY')

with col2:
    day_of_penalty = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
                                     value=18,
                                     min_value=1,
                                     max_value=31)

company_type = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"])

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
                result = response.json()

                st.success("Файл успешно обработан!")
                st.text("Результат обработки документов")
                st.json(result)

                st.markdown("## Заполение информации для генерациии иска (поля которые будут далее, можно отредактировать)")

                for key, value in result['result_of_llm_parsers'].items():
                    if "claim" in key:
                        plaintiff_info_parsed = value['plaintiff_info']




                court_info = {}
                plaintiff_info = {}
                defendant_info = {}
                lawsuit_info = {}

                st.markdown("### Данные о месте проведения")
                court_info['name'] = st.text_input(label="Название Органа", value="Арбитражный суд города Москвы")
                court_info['addres'] = st.text_input(label="Адресс Органа", value="115225, г. Москва, ул. Большая Тульская, д. 17")

                
                st.markdown("### Данные об Истце")
                plaintiff_info['name'] = st.text_input(label="Название Истца", value="Публичное акционерное общество «Московская объединенная энергетическая компания» ")
                plaintiff_info['addres'] = st.text_input(label="Адрес Истца", value=f'{plaintiff_info_parsed['plaintiff_address']}')
                plaintiff_info['correspondency_addres'] = st.text_input(label='Адрес для направления корреспонденции', value="121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613 (МГКА «КДЗП»)")
                # эти данные надо парсить
                plaintiff_info['inn'] = st.text_input(label='ИНН Истца', value=f'{plaintiff_info_parsed['plaintiff_inn']}')
                plaintiff_info['ogrn'] = st.text_input(label='ОГРН Истца', value=f'{plaintiff_info_parsed['plaintiff_ogrn']}')


                st.markdown("### Данные об ответчике")
                #все эти данные надо парсить
                defendant_info['name'] = st.text_input(label="Название ответчика", value=f'{result['results_of_name_parser']['defendant_info']['name']}')
                defendant_info['addres'] = st.text_input(label="Адрес ответчика", value=f'{result['results_of_name_parser']['defendant_info']['address']}')
                defendant_info['inn'] = st.text_input(label="ИНН ответчика", value=f'{result['results_of_name_parser']['defendant_info']['inn']}')
                defendant_info['ogrn'] = st.text_input(label="ОГРН ответчика", value=f'{result['results_of_name_parser']['defendant_info']['ogrn']}')
                
                st.markdown("### Данные о договоре")
                lawsuit_info['cost'] = st.text_input(label="Цена иска", value=f'{1000} р.')
                lawsuit_info['tax'] = st.text_input(label="Госпошлина", value=f'{1000} р.')
                lawsuit_info['last_day'] = st.text_input(label = "Срок оплаты", value=f'До {day_of_penalty} числа месяца, следующего за расчётным')
                
                service_type_info = []
                claims = []
                for key, value in result['result_of_llm_parsers'].items():
                    if "contract" in key:
                        service_type_info.append(result['result_of_llm_parsers'][key]['service_type'])
                    if "claim" in key:
                        claims.append(f"№ {result['result_of_llm_parsers'][key]['claim_number']} от {result['result_of_llm_parsers'][key]['claim_date']}")

                st.markdown(f"### Данные об услуге, полученные из договоров\n {"\n".join(f" - {elem}" for elem in service_type_info)}")
                lawsuit_info['service_type'] = st.selectbox("Выберите вид услугии", ["ГВС + ТЭ", "ТЭ", "ГВС"])

                st.markdown(f'### Данные о претензиях')
                st.markdown(f"номера и даты претензий\n {"\n".join(f"- {claim}" for claim in claims)}")
                lawsuit_info['claims'] = claims 
                
                st.markdown(f"### Создание документов")
                col1, col2, = st.columns(2)
                with col1:
                    if st.button(label="Создать Иск"):
                        response = requests.post("http://localhost:5001/create_doc",
                                            
                                            
                                            )

                with col2:
                    if st.button(label="Создать расчёт к иску"):
                        response = requests.post("http://localhost:5001/create_calculating_table",
                                        
                                        
                                        )
                
            else:
                st.error(f"Ошибка: {response.status_code}")
                st.text(response.text)

    