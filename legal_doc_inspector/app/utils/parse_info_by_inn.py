import requests

from bs4 import BeautifulSoup

def parse_html(inn):
    plaintiff_html = requests.get(f"https://egrul.itsoft.ru/{inn}").text
    soup = BeautifulSoup(plaintiff_html, 'html.parser')
    address = soup.find('div', {'id': 'address'}).text.strip()
    kpp = soup.find('div', {'id': 'kpp'}).text.strip()
    ogrn = soup.find('span', {'id': 'ogrn'}).text.strip()
    name = soup.find('h1', {'id': 'short_name'}).text.strip()
    return name, address, kpp, ogrn
