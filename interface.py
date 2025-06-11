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
                # st.download_button(
                #     label="⬇️ Скачать расчёт к иску",
                #     data=file_data,
                #     file_name="расчёт_к_иску.docx"
                # )
                
                
            else:
                st.error(f"Ошибка: {response.status_code}")
                st.text(response.text)

    