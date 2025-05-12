# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 20:30:05 2025

@author: marin
"""

import requests
import time

def get_company_info_by_inn(inn):
    # Шаг 1: Получаем идентификатор запроса
    url = "https://egrul.nalog.ru/"
    payload = {
        "vyp3CaptchaToken": "",
        "page": "",
        "query": inn,
        "region": "",
        "PreventChromeAutocomplete": ""
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    try:
        # Отправляем запрос для получения ID поиска
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()

        # Получаем ID из ответа
        search_id = response.json().get('t')

        if not search_id:
            return None, None, None

        # Шаг 2: Получаем результаты поиска по ID
        result_url = f"https://egrul.nalog.ru/search-result/{search_id}"

        # Даем серверу время на обработку запроса
        time.sleep(0.1)

        result_response = requests.get(result_url, headers=headers)
        result_response.raise_for_status()

        data = result_response.json()

        # Проверяем наличие данных
        if 'rows' in data and len(data['rows']) > 0:
            # Берем первую запись (самую релевантную)
            first_record = data['rows'][0]
            ogrn = first_record.get('o')
            company_name = first_record.get('n')
            address = first_record.get('a')
            return ogrn, company_name, address
        else:
            return None, None, None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None, None, None

