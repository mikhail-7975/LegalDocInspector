import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from docx import Document

st.title("Загрузка и обработка XLS/ZIP файла")

# Загрузчик файла

date_selected = st.date_input("Выберите дату Г-М-Д")
company_type = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"])
uploaded_file = st.file_uploader("Выберите XLS/ZIP файл")

if uploaded_file is not None:
    # Показываем данные из файла
    
    

    # Кнопка отправки
    if st.button("Отправить на сервер"):
        # Восстанавливаем указатель файла
        uploaded_file.seek(0)

        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
            "company_type": company_type
        }


        # Подготавливаем файл к отправке
        files = {"file": (uploaded_file.name, uploaded_file, "application/vnd.ms-excel")}
        
        # Отправляем POST-запрос
        response = requests.post("http://localhost:5001/parse",
                                  files=files,
                                  data= data
                                  )
        
        if response.status_code == 200:
            st.success("Файл успешно отправлен!")
            result = response.json()
            st.text('Результат парсинга справки')
            st.json(result)  # Показываем ответ от сервера
        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)


def create_docx_from_json(data)