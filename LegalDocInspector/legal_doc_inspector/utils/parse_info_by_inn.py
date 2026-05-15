import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup, Tag


class EgrulItsoftParseError(RuntimeError):
    """Не удалось извлечь данные с сайта egrul.itsoft.ru (разметка или ответ сервера)."""


def _text_from_tag(el: Tag | None) -> str | None:
    if el is None:
        return None
    t = el.get_text(separator=" ", strip=True)
    return t if t else None


def _first_by_ids(soup: BeautifulSoup, ids: Iterable[str]) -> str | None:
    for elem_id in ids:
        node = soup.find(id=elem_id)
        txt = _text_from_tag(node)
        if txt:
            return txt
    return None


def _parse_itsoft_html(soup: BeautifulSoup) -> tuple[str, str, str, str, str]:
    """
    Извлекает поля со страницы itsoft; перебирает несколько возможных id (старая и новая вёрстка).
    """
    address = _first_by_ids(
        soup,
        ("address", "legal-address", "juridical_address", "address_jur", "addr"),
    )
    kpp = _first_by_ids(soup, ("kpp", "kpp_jur"))
    ogrn = _first_by_ids(soup, ("ogrn", "ogrn_jur"))
    short_name = _first_by_ids(
        soup,
        ("short_name", "short-name", "name_short", "shortname"),
    )
    full_name = _first_by_ids(
        soup,
        ("full_name", "full-name", "name_full", "fullname"),
    )

    missing = []
    if not address:
        missing.append("адрес")
    if not kpp:
        missing.append("КПП")
    if not ogrn:
        missing.append("ОГРН")
    if not short_name:
        missing.append("сокращённое наименование")
    if missing:
        raise EgrulItsoftParseError(
            "Не удалось разобрать страницу ЕГРЮЛ (itsoft): не найдены поля: "
            + ", ".join(missing)
            + ". Возможно, сайт изменил вёрстку или вернул нестандартную страницу."
        )

    if not full_name:
        full_name = short_name

    return (
        replace_quotes(full_name),
        replace_quotes(short_name),
        clean_address(address),
        kpp,
        ogrn,
    )


def parse_html(inn: str):
    """
    Данные организации по ИНН с egrul.itsoft.ru.
    Возвращает (full_name, short_name, address, kpp, ogrn).
    При ошибке разбора — EgrulItsoftParseError с понятным текстом.
    """
    inn = str(inn).strip()
    if not inn:
        raise EgrulItsoftParseError("ИНН пустой: укажите ИНН организации.")

    url = f"https://egrul.itsoft.ru/{inn}"
    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as e:
        raise EgrulItsoftParseError(
            f"Не удалось разобрать страницу ЕГРЮЛ (itsoft): сетевая ошибка при запросе {url}: {e}"
        ) from e

    if response.status_code != 200:
        raise EgrulItsoftParseError(
            "Не удалось разобрать страницу ЕГРЮЛ (itsoft): "
            f"сервер вернул код {response.status_code} для {url}."
        )

    plaintiff_html = response.text
    if not plaintiff_html or len(plaintiff_html) < 200:
        raise EgrulItsoftParseError(
            "Не удалось разобрать страницу ЕГРЮЛ (itsoft): пустой или слишком короткий ответ."
        )

    soup = BeautifulSoup(plaintiff_html, "html.parser")

    # Резерв: старая вёрстка с явными тегами (если id не сработали — пробуем как раньше)
    def _legacy() -> tuple[str | None, str | None, str | None, str | None, str | None]:
        def gt(tag: str, attrs: dict) -> str | None:
            el = soup.find(tag, attrs)
            return _text_from_tag(el)

        addr = gt("div", {"id": "address"})
        kp = gt("div", {"id": "kpp"})
        og = gt("span", {"id": "ogrn"})
        sn = gt("h1", {"id": "short_name"})
        fn = gt("h2", {"id": "full_name"})
        return fn, sn, addr, kp, og

    try:
        return _parse_itsoft_html(soup)
    except EgrulItsoftParseError as primary_err:
        fn, sn, addr, kp, og = _legacy()
        if addr and kp and og and sn:
            if not fn:
                fn = sn
            return (
                replace_quotes(fn),
                replace_quotes(sn),
                clean_address(addr),
                kp,
                og,
            )
        raise primary_err from None


def replace_quotes(text: str) -> str:
    text = re.sub(r'"([^"]*)"', r"«\1»", text)
    return text


def clean_address(text: str) -> str:
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",(?=[^ \w])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
