import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from docx import Document

st.title("Загрузка и обработка документов")

# Загрузчик файла

date_selected = st.date_input("Выберите дату")
company_type = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"])

st.text("Поле для договора")
contract_uploaded_file = st.file_uploader("Выберите Документ с договором")
st.text("Поле для претензии")
claim_uploaded_file = st.file_uploader("Выберите Документ с претензией")
st.text("Поле для Excel справки о задожленности")
debt_certificate_file = st.file_uploader("Выберите Excel справку о задолженности")
st.text("Поле для ZIP архива с приложением к иску")
zip_uploaded_file = st.file_uploader("Выберите ZIP файл")

if zip_uploaded_file is not None or claim_uploaded_file is not None or contract_uploaded_file is not None or debt_certificate_file is not None:    
    files = {}


    # Кнопка отправки
    if st.button("Отправить на сервер"):
        # Восстанавливаем указатель файла
        if zip_uploaded_file:
            zip_uploaded_file.seek(0)
            files["zip_file"] = (zip_uploaded_file.name, zip_uploaded_file)
        
        if claim_uploaded_file:
            claim_uploaded_file.seek(0)
            files["claim_file"] = (claim_uploaded_file.name, claim_uploaded_file)
            

        if contract_uploaded_file:
            contract_uploaded_file.seek(0)
            files['contract_file'] = (contract_uploaded_file.name, contract_uploaded_file)
            
        
        if debt_certificate_file:
            debt_certificate_file.seek(0)
            files["certificate_file"] = (debt_certificate_file.name, debt_certificate_file)
        
        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
            "company_type": company_type
        }

        if len(files) < 3:
            st.error("Загружены не все файлы")

        
        else:
            response = requests.post("http://localhost:5001/parse",
                                    files=files,
                                    data= data
                                    )
            
            if response.status_code == 200:
                st.success("Файл успешно отправлен!")
                result = response.json()
                st.text('Результат сохранения файлов')
                st.json(result)  # Показываем ответ от сервера
            else:
                st.error(f"Ошибка: {response.status_code}")
                st.text(response.text)

    