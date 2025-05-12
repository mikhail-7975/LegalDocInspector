import streamlit as st
import pandas as pd
import requests

st.title("Загрузка и обработка XLS файла")

# Загрузчик файла
uploaded_file = st.file_uploader("Выберите XLS файл")

if uploaded_file is not None:
    # Показываем данные из файла
    df = pd.read_excel(uploaded_file, engine='xlrd')
    # st.write("Предпросмотр данных:")
    # st.dataframe(df)

    # Кнопка отправки
    if st.button("Отправить на сервер"):
        # Восстанавливаем указатель файла
        uploaded_file.seek(0)

        # Подготавливаем файл к отправке
        files = {"file": (uploaded_file.name, uploaded_file, "application/vnd.ms-excel")}
        print('post')
        # Отправляем POST-запрос
        response = requests.post("http://localhost:5001/parse", files=files)
        print('post')
        if response.status_code == 200:
            st.success("Файл успешно отправлен!")
            result = response.json()
            st.json(result)  # Показываем ответ от сервера
        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)