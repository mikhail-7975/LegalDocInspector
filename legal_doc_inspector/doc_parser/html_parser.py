from bs4 import BeautifulSoup  # работа с html
import requests


def parse_html(inn):
    # фкнция принимает инн и через запрос получает html с нужными данными
    plaintiff_html = requests.get(f"https://egrul.itsoft.ru/{inn}").text
    # подключаем модуль для рабоыт с html
    soup = BeautifulSoup(plaintiff_html, "html.parser")
    # находим адресс
    address = soup.find("div", {"id": "address"}).text.strip()
    # нахожим кпп
    kpp = soup.find("div", {"id": "kpp"}).text.strip()
    # находим оргн
    ogrn = soup.find("span", {"id": "ogrn"}).text.strip()
    # нахожим имя
    name = soup.find("h1", {"id": "short_name"}).text.strip()
    return name, address, kpp, ogrn
