import re

from bs4 import BeautifulSoup
import requests


def parse_html(inn):
    plaintiff_html = requests.get(f"https://egrul.itsoft.ru/{inn}").text
    soup = BeautifulSoup(plaintiff_html, "html.parser")
    address = soup.find("div", {"id": "address"}).text.strip()
    kpp = soup.find("div", {"id": "kpp"}).text.strip()
    ogrn = soup.find("span", {"id": "ogrn"}).text.strip()
    short_name = soup.find("h1", {"id": "short_name"}).text.strip()
    full_name = soup.find("h2", {"id": "full_name"}).text.strip()
    return (
        replace_quotes(full_name),
        replace_quotes(short_name),
        clean_address(address),
        kpp,
        ogrn,
    )


def replace_quotes(text: str):
    text = re.sub(r'"([^"]*)"', r"«\1»", text)
    return text


def clean_address(text: str) -> str:
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",(?=[^ \w])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
