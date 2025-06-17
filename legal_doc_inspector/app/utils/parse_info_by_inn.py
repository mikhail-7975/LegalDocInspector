import requests

from bs4 import BeautifulSoup

def parse_html(inn):
    plaintiff_html = requests.get(f"https://egrul.itsoft.ru/{inn}").text
    soup = BeautifulSoup(plaintiff_html, 'html.parser')
    address = soup.find('div', {'id': 'address'}).text.strip()
    kpp = soup.find('div', {'id': 'kpp'}).text.strip()
    ogrn = soup.find('span', {'id': 'ogrn'}).text.strip()
    short_name = soup.find('h1', {'id': 'short_name'}).text.strip()
    full_name = soup.find('h2', {'id': 'full_name'}).text.strip()
    return full_name, short_name, address, kpp, ogrn
