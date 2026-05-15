import requests
# from datetime import datetime
from io import BytesIO
from pathlib import Path
# from urllib.parse import quote
# from collections import defaultdict
# from uuid import uuid4
import streamlit as st
# import pandas as pd
#   from docx import Document

from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import (
    EgrulItsoftParseError,
    parse_html,
)
from LegalDocInspector.legal_doc_inspector.utils.parse_egrul_sertificate import (
    plaintiff_tuple_from_egrul_pdf,
)
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import calculate_state_duty

if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'court_info': {},
        'plaintiff_info': {},
        'defendant_info': {},
        'lawsuit_info': {},
        'service_type_info': [],
        'claims': [],
        'result': {},
        'flag':False,
        'flag2':False,
        'flag3':False,
        'forms_changed': False,
        'num_complects': 1,
        'responsitive_name': None
    }

if 'complects' not in st.session_state:
    st.session_state.complects = {}
    st.session_state.complects[st.session_state.form_data['num_complects']] = {
        'contract_uploaded_file':None,
        'claim_uploaded_file':None,
        'debt_certificate_file':None
    }
if "egrul_certificate" not in st.session_state:
    st.session_state.egrul = None

def on_change_handler():
    st.session_state.form_data['forms_changed'] = True


def _parser_penalty_day_value(raw) -> int | None:
    """День месяца 1..31 из ответа парсера или None, если не распознан."""
    if raw is None:
        return None
    try:
        d = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= d <= 31:
        return d
    return None


def _parser_penalty_day_recognized(raw) -> bool:
    return _parser_penalty_day_value(raw) is not None


def get_documents_complect_form(form_id:int, day_of_penalty: int | None = None, contract_uploaded_file = None, claim_uploaded_file = None, debt_certificate_file = None):
    st.markdown(f"### Набор {form_id}")

    # st.session_state.complects[form_id]['day_of_penalty'] = st.number_input(label="Выберите число месяца, которое является последним днём оплаты счёта",
    #                                 value=18,
    #                                 min_value=1,
    #                                 max_value=31,
    #                                 key='day_of_penalty'+str(form_id))

    st.text("Поле для договора")
    st.session_state.complects[form_id]['contract_uploaded_file'] = st.file_uploader("Выберите Документ с договором",
                                            accept_multiple_files=False,
                                            key='contract_uploaded_file'+str(form_id))
    st.text("Поле для претензии")
    st.session_state.complects[form_id]['claim_uploaded_file'] = st.file_uploader("Выберите Документ с претензией",
                                           accept_multiple_files=False,
                                           key='claim_uploaded_file'+str(form_id))
    st.text("Поле для Excel справки о задожленности")
    st.session_state.complects[form_id]['debt_certificate_file'] = st.file_uploader("Выберите Excel справку о задолженности",
                                            accept_multiple_files=True,
                                            key='debt_certificate_file'+str(form_id))
def get_service_type():
    res = []
    ans = ''
    for contract_num, value in st.session_state.contracts.items():
        res.append(value['contract_type'])
    
    res = set(res)
    for i in res:
        ans += str(i)

    return ans
    
def get_contract_form(contract_number:str):

    
    st.markdown(f"### информация из договора {contract_number}")
    st.text(f"Тип договора (ответ нейросети) - {st.session_state.contracts[contract_number]['contract_type_parsed']}")

    if st.session_state.contracts[contract_number]['contract_type'] is None:
        try:
            index = ['ТЭ', 'ГВС', 'СОИ', 'ФОТЭ'].index(st.session_state.contracts[contract_number]['contract_type_parsed'])
        except ValueError:
            index = 0
    else:
        index = ['ТЭ', 'ГВС', 'СОИ', 'ФОТЭ'].index(st.session_state.contracts[contract_number]['contract_type'])

    st.session_state.contracts[contract_number]['contract_type'] = st.selectbox(label="Выберите тип договора",
                                                                                options=['ТЭ', 'ГВС', 'СОИ', 'ФОТЭ'],
                                                                                index=index,
                                                                                on_change=on_change_handler,
                                                                                key="c_t"+str(contract_number)
                                                                            )
    
    st.text(f"{st.session_state.contracts[contract_number]['contract_text_parsed']}")
    
    
    col1, col2 = st.columns(2)
    # st.json(st.session_state.contracts[contract_number])
    with col1:
        contract = st.session_state.contracts[contract_number]
        recognized = contract.get('overdue_date_recognized')
        if recognized is None:
            recognized = _parser_penalty_day_recognized(contract.get('overdue_date_parsed'))
            contract['overdue_date_recognized'] = recognized
        if not recognized:
            st.warning(
                "День месяца (последний день оплаты счёта) из договора не распознан автоматически. "
                "Введите его вручную в поле ниже (число от 1 до 31)."
            )
        parsed_day = _parser_penalty_day_value(contract.get('overdue_date_parsed'))
        if contract['day_of_penalty'] is None:
            default_day = parsed_day if parsed_day is not None else 18
        else:
            default_day = int(contract['day_of_penalty'])

        st.session_state.contracts[contract_number]['day_of_penalty'] = st.number_input(
            label="Выберите число месяца, которое является последним днём оплаты счёта",
            value=default_day,
            min_value=1,
            max_value=31,
            key='day_of_penalty'+str(contract_number),
            on_change=on_change_handler,
        )
    with col2:
        st.session_state.contracts[contract_number]['contract_point']  = st.text_input(label="напишите номер пункта договора, в котором говорится о дне начала просрочки ",
                                                                                      key="c_p"+str(contract_number),
                                                                                      on_change=on_change_handler,
                                                                                      value=st.session_state.contracts[contract_number]['contract_point_parsed'] if st.session_state.contracts[contract_number]['contract_point'] is None else st.session_state.contracts[contract_number]['contract_point']   )


def _contract_field_from_session(contract_number: str, field: str):
    """Актуальное значение поля договора: contracts + виджет Streamlit по key."""
    contract = st.session_state.contracts.get(contract_number) or {}
    value = contract.get(field)
    if value is not None and str(value).strip() != "":
        return value
    if field == "contract_point":
        widget_val = st.session_state.get(f"c_p{contract_number}")
        if widget_val is not None and str(widget_val).strip():
            return widget_val
        parsed = contract.get("contract_point_parsed")
        if parsed is not None and str(parsed).strip():
            return parsed
    if field == "day_of_penalty":
        widget_val = st.session_state.get(f"day_of_penalty{contract_number}")
        if widget_val is not None:
            return widget_val
    if field == "contract_type":
        widget_val = st.session_state.get(f"c_t{contract_number}")
        if widget_val is not None and str(widget_val).strip():
            return widget_val
        parsed = contract.get("contract_type_parsed")
        if parsed is not None and str(parsed).strip():
            return parsed
    return value


def build_calculate_penalty_request(parse_result: dict) -> dict:
    """Тело POST /calculate_penalty с актуальными пунктом договора и днём просрочки."""
    request_json = {
        "company_type": st.session_state.form_data["company_type"],
        "end_date": st.session_state.form_data["end_date"],
        "parsing_results": [],
    }
    for contract_info in parse_result["table_parser_result"]:
        contract_number = contract_info[1]
        parsing_result = {
            "parsed_info": contract_info[0],
            "contract_number": contract_number,
            "contract_point": _contract_field_from_session(contract_number, "contract_point"),
            "day_of_penalty": _contract_field_from_session(contract_number, "day_of_penalty"),
            "contract_type": _contract_field_from_session(contract_number, "contract_type"),
        }
        request_json["parsing_results"].append(parsing_result)
    return request_json


def run_calculate_penalty(parse_result: dict):
    """Вызов /calculate_penalty. Возвращает (ok, response_json, error_text)."""
    request_json = build_calculate_penalty_request(parse_result)
    try:
        response = requests.post(
            "http://localhost:5001/calculate_penalty",
            json=request_json,
            timeout=120,
        )
    except requests.RequestException as exc:
        return False, None, str(exc)
    if response.status_code == 200:
        return True, response.json(), None
    return False, None, f"{response.status_code}\n{response.text}"


st.title("Загрузка и обработка документов (Нейросети включены)")


# Загрузчик файла

col1, col2 = st.columns(2)

with col1:
    date_selected = st.date_input("Выберите дату конца просрочки",
                                  format='DD.MM.YYYY',
                                  value= st.session_state.form_data['end_date'] if 'end_date' in st.session_state else 'today',
                                  on_change=on_change_handler)
    st.session_state.form_data['end_date'] = date_selected.strftime("%d.%m.%Y")
with col2:
    st.session_state.form_data['company_type'] = st.selectbox("Выберите тип компании", ["Прочие", "УК", "ТСЖ"],
                                                              on_change=on_change_handler)

st.markdown("### Выписка из ЕГРЮЛ")
st.session_state.egrul = st.file_uploader("Выберите Документ с выпиской из ЕГРЮЛ",
                                            accept_multiple_files=False,
                                            key='egrul_certificate')

for form_num, form_info in st.session_state.complects.items():
    get_documents_complect_form(
        form_id=form_num,
        # day_of_penalty=form_info['day_of_penalty'],
        claim_uploaded_file=form_info['claim_uploaded_file'],
        contract_uploaded_file=form_info['contract_uploaded_file'],
        debt_certificate_file=form_info['debt_certificate_file']
    )
col1, col2 = st.columns(2)
with col1 :
    if st.button("➕ Добавить набор документов"):
        if 'num_complects' not in st.session_state.form_data:
            st.session_state.form_data['num_complects'] = 1
        else:
            st.session_state.form_data['num_complects'] += 1
            st.session_state.complects[st.session_state.form_data['num_complects']] = {
            # 'day_of_penalty':18,
            'contract_uploaded_file':None,
            'claim_uploaded_file':None,
            'debt_certificate_file':None
        }
            st.session_state.form_data['flag'] = False
            on_change_handler()
            st.rerun()

with col2:
    if st.button("➖ Убрать набор документов"):
        if  st.session_state.form_data['num_complects'] == 1:
            st.session_state.form_data['num_complects'] = 1
            st.error('Должен быть хотя бы один набор')
        else:
            del st.session_state.complects[st.session_state.form_data['num_complects']]
            st.session_state.form_data['num_complects'] -= 1
            st.session_state.form_data['flag']
            on_change_handler()
            st.rerun()


# st.json(st.session_state.complects)

if st.session_state.complects[st.session_state.form_data['num_complects']]['claim_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['contract_uploaded_file'] is not None and st.session_state.complects[st.session_state.form_data['num_complects']]['debt_certificate_file'] is not None and st.session_state.egrul is not None:


    # Кнопка отправки
    if st.button("Отправить на сервер"):

        files = {}
        data = {
            "date": date_selected.strftime("%Y-%m-%d"),  # форматируем дату
        }
        egrul_certificate_file = st.session_state.egrul
        egrul_certificate_file.seek(0)
        files['egrul_certificate_file'] = (egrul_certificate_file.name, egrul_certificate_file)
        for complect_id, complect_info in st.session_state.complects.items():
            claim_uploaded_file = complect_info['claim_uploaded_file']
            contract_uploaded_file = complect_info['contract_uploaded_file']
            debt_certificate_files  = complect_info['debt_certificate_file']
            claim_uploaded_file.seek(0)
            contract_uploaded_file.seek(0)
            # debt_certificate_file.seek(0)

            files[f'complect_{complect_id}_claim_file'] = (claim_uploaded_file.name, claim_uploaded_file)
            files[f'complect_{complect_id}_contract_file'] = (contract_uploaded_file.name, contract_uploaded_file)
            # files[f'complect_{complect_id}_certificate_file'] = (debt_certificate_file.name, debt_certificate_file)
            for i, debt_certificate_file in enumerate(debt_certificate_files):
                print(debt_certificate_file.name)
                if debt_certificate_file is not None:
                    debt_certificate_file.seek(0)
                    files[f'complect_{complect_id}_certificate_file_{i}'] = (
                        debt_certificate_file.name, 
                        debt_certificate_file   
                    )
                    data[f'{complect_id}_certificates_count'] = str(i+1)
        data['complects_count'] = str(complect_id)



        with st.spinner(text="Ваш запрос обрабатывается, пожалуйста, подождите, обработка одного набора занимает в среднем 2 минуты"):
            response = requests.post("http://localhost:5001/parse",
                                    files=files,
                                    data= data
                                    )
        if response.status_code == 200:
            flag = True
            st.session_state.form_data['flag'] = flag
            st.session_state.form_data['result'] = response.json()
            st.session_state.form_data['path_to_save'] = response.json()['path_to_save']
            # st.json(response.json())


        else:
            st.error(f"Ошибка: {response.status_code}")
            st.text(response.text)


if st.session_state.form_data['flag']:
    result = st.session_state.form_data['result']
    i = 1
    if not "contracts" in st.session_state:
        st.session_state.contracts = {}
        for contract_info in result['table_parser_result']:
            contract_number = contract_info[1]
            contract_type = contract_info[2]
            contract_point = contract_info[3]
            overdue_date = contract_info[4]
            contract_text = contract_info[5]
            # result['result_of_llm_parsers'] = {}
            # result['result_of_llm_parsers'][f"contract_{contract_number}"] = {
            #     "service_type":"тепловую энергию/теплоноситель (ТЭ) и горячую воду (ГВС))",
            #     "overdue_date":"В следующем фрагменте указан срок, в течение которого Исполнитель должен произвести оплату:\n\n\"5. 5. Исполнитель в срок до 18-го числа месяца, следующего за расчетным, производит оплату стоимости тепловой энергии, теплоносителя, указанной в счете. Датой оплаты считается дата поступления денежных средств на расчетный счет Теплоснабжающей организации.\"",
            # }
            # result['result_of_llm_parsers'][f"claim_0"] = {"claim_date":"17.10.2024","claim_number":"517305"}


            # json_info = result['result_of_llm_parsers'][f"contract_{contract_number}"]
            st.session_state.contracts[contract_number] = {
                'contract_type_parsed': contract_type,
                'contract_point_parsed': contract_point,
                'overdue_date_parsed': overdue_date,
                'overdue_date_recognized': _parser_penalty_day_recognized(overdue_date),
                'contract_text_parsed' : contract_text,
                'contract_point' : None,
                'day_of_penalty' : None,
                'contract_type': None
            }
    # st.json(st.session_state.contracts)


    st.success("Файл успешно обработан!")
    st.text("Результат обработки документов")
    # st.json(result)

    st.markdown("## Заполение информации для генерациии иска (поля которые будут далее, можно отредактировать)")

    st.success("Пожалуйста, внимательно проверьте все пункты!")
    # for key, value in result['result_of_llm_parsers'].items():
    #     if "claim" in key:
    #         plaintiff_info_parsed = value['plaintiff_info']




    court_info = {}
    plaintiff_info = {}
    defendant_info = {}
    lawsuit_info = {}

    st.markdown("### Данные о месте проведения")
    court_info['name'] = st.text_input(label="Название Органа", value="Арбитражный суд города Москвы" , on_change=on_change_handler)
    court_info['addres'] = st.text_input(label="Адресс Органа", value="115225, г. Москва, ул. Большая Тульская, д. 17", on_change= on_change_handler)


    st.markdown("### Данные об Истце")
    _DEFAULT_PLAINTIFF_INN = "7720518494"
    _DEFAULT_PLAINTIFF_FULL_NAME = (
        "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «МОСКОВСКАЯ ОБЪЕДИНЕННАЯ ЭНЕРГЕТИЧЕСКАЯ КОМПАНИЯ»"
    )
    _DEFAULT_PLAINTIFF_SHORT_NAME = 'ПАО "МОЭК"'
    _DEFAULT_PLAINTIFF_OGRN = "1047796974092"
    _DEFAULT_PLAINTIFF_ADDRES = (
        "119526, г. Москва, проспект Вернадского, д. 101, к. 3, эт/каб 20/2017"
    )
    _DEFAULT_PLAINTIFF_CORR = (
        "121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613"
    )
    for _wk, _dv in (
        ("_plaintiff_w_inn", _DEFAULT_PLAINTIFF_INN),
        ("_plaintiff_w_full_name", _DEFAULT_PLAINTIFF_FULL_NAME),
        ("_plaintiff_w_short_name", _DEFAULT_PLAINTIFF_SHORT_NAME),
        ("_plaintiff_w_addres", _DEFAULT_PLAINTIFF_ADDRES),
        ("_plaintiff_w_ogrn", _DEFAULT_PLAINTIFF_OGRN),
        ("_plaintiff_w_correspondency", _DEFAULT_PLAINTIFF_CORR),
    ):
        st.session_state.setdefault(_wk, _dv)

    _seed_marker = (
        str(result.get("path_to_save") or ""),
        str(result.get("egrul_certificate_filename") or ""),
    )
    if st.session_state.get("_plaintiff_seed_marker") != _seed_marker:
        st.session_state["_plaintiff_seed_marker"] = _seed_marker
        st.session_state["_plaintiff_w_inn"] = _DEFAULT_PLAINTIFF_INN
        st.session_state["_plaintiff_w_full_name"] = _DEFAULT_PLAINTIFF_FULL_NAME
        st.session_state["_plaintiff_w_short_name"] = _DEFAULT_PLAINTIFF_SHORT_NAME
        st.session_state["_plaintiff_w_addres"] = _DEFAULT_PLAINTIFF_ADDRES
        st.session_state["_plaintiff_w_ogrn"] = _DEFAULT_PLAINTIFF_OGRN
        st.session_state["_plaintiff_w_correspondency"] = _DEFAULT_PLAINTIFF_CORR

    _path_save = st.session_state.form_data.get("path_to_save") or result.get("path_to_save")
    _egrul_fn = result.get("egrul_certificate_filename")
    _egrul_path = (
        Path(_path_save) / _egrul_fn if _path_save and _egrul_fn else None
    )

    if st.session_state.get("_plaintiff_parse_error"):
        st.error(st.session_state["_plaintiff_parse_error"])

    _col_it, _col_pdf = st.columns(2)
    with _col_it:
        if st.button("Заполнить из itsoft по ИНН", key="plaintiff_btn_itsoft"):
            _inn_try = str(st.session_state.get("_plaintiff_w_inn", _DEFAULT_PLAINTIFF_INN)).strip()
            try:
                _fn, _sn, _ad, _kpp, _og = parse_html(_inn_try)
                st.session_state["_plaintiff_w_full_name"] = _fn.upper()
                st.session_state["_plaintiff_w_short_name"] = _sn
                st.session_state["_plaintiff_w_addres"] = _ad
                st.session_state["_plaintiff_w_ogrn"] = _og
                st.session_state["_plaintiff_parse_error"] = None
            except EgrulItsoftParseError as _e:
                st.session_state["_plaintiff_parse_error"] = str(_e)
            except Exception as _e:
                st.session_state["_plaintiff_parse_error"] = (
                    f"Не удалось разобрать страницу ЕГРЮЛ (itsoft): {_e}"
                )
            st.rerun()
    with _col_pdf:
        if st.button("Заполнить из PDF выписки ЕГРЮЛ", key="plaintiff_btn_egrul_pdf"):
            if _egrul_path is None or not _egrul_path.is_file():
                st.session_state["_plaintiff_parse_error"] = (
                    "Нет сохранённой выписки на сервере: повторите загрузку и «Отправить на сервер», "
                    "или заполните поля вручную."
                )
            else:
                try:
                    _fn, _sn, _ad, _kpp, _og = plaintiff_tuple_from_egrul_pdf(_egrul_path)
                    st.session_state["_plaintiff_w_full_name"] = _fn.upper()
                    st.session_state["_plaintiff_w_short_name"] = _sn
                    st.session_state["_plaintiff_w_addres"] = _ad
                    st.session_state["_plaintiff_w_ogrn"] = _og
                    st.session_state["_plaintiff_parse_error"] = None
                except Exception as _e:
                    st.session_state["_plaintiff_parse_error"] = str(_e)
            st.rerun()

    plaintiff_info["inn"] = st.text_input(
        label="ИНН истца",
        key="_plaintiff_w_inn",
        on_change=on_change_handler,
    )
    plaintiff_info["full_name"] = st.text_input(
        label="Полное наименование истца",
        key="_plaintiff_w_full_name",
        on_change=on_change_handler,
    )
    plaintiff_info["short_name"] = st.text_input(
        label="Сокращённое наименование (аббревиатура)",
        key="_plaintiff_w_short_name",
        on_change=on_change_handler,
    )
    plaintiff_info["addres"] = st.text_input(
        label="Адрес истца",
        key="_plaintiff_w_addres",
        on_change=on_change_handler,
    )
    plaintiff_info["ogrn"] = st.text_input(
        label="ОГРН истца",
        key="_plaintiff_w_ogrn",
        on_change=on_change_handler,
    )
    plaintiff_info["correspondency_addres"] = st.text_input(
        label="Адрес для направления корреспонденции",
        key="_plaintiff_w_correspondency",
        on_change=on_change_handler,
    )

    st.session_state.form_data["plaintiff_info"] = plaintiff_info


    st.markdown("### Данные об ответчике")


    defendant_info['full_name'] = st.text_input(label="Название ответчика", value=f"{result['results_of_name_parser']['defendant_info']['full_name']}".upper(), on_change= on_change_handler)
    defendant_info['short_name'] = st.text_input(label="Название ответчика(аббревиатура)", value=f"{result['results_of_name_parser']['defendant_info']['short_name']}", on_change= on_change_handler)
    defendant_info['addres'] = st.text_input(label="Адрес ответчика", value=f"{result['results_of_name_parser']['defendant_info']['address']}", on_change= on_change_handler)
    defendant_info['inn'] = st.text_input(label="ИНН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['inn']}", on_change= on_change_handler)
    defendant_info['ogrn'] = st.text_input(label="ОГРН ответчика", value=f"{result['results_of_name_parser']['defendant_info']['ogrn']}", on_change= on_change_handler)


    st.markdown("### Данные о договорах")
    for contract_num, value in st.session_state.contracts.items():
        get_contract_form(contract_number=contract_num)
    if st.button("Произвести расчёты по загруженным наборам документов"):
        with st.spinner(text="Ваш запрос обрабатывается, пожалуйста, подождите"):
            ok, calc_json, err = run_calculate_penalty(result)
        if ok:
            st.session_state.form_data["flag2"] = True
            st.session_state.form_data["result2"] = calc_json
        else:
            st.error("Ошибка при расчёте пени")
            st.text(err or "Неизвестная ошибка")

    # st.json(st.session_state.form_data)

if st.session_state.form_data['flag2']:
    _parse_result = st.session_state.form_data.get("result") or {}
    st.success('Расчёты успешно произведены !')
    # st.json(st.session_state.form_data['result2'])

#     request_json = {}
    st.markdown("#### Проверьте данные об иске")

    st.session_state.form_data['lawsuit_info']['cost'] = st.text_input(label="Цена иска", value=f"{st.session_state.form_data['result2']['claim_data']['table_info']['cost_of_lawsuit']}", on_change= on_change_handler)

    st.session_state.form_data['lawsuit_info']['tax'] = st.text_input(label="Госпошлина", value=f"{calculate_state_duty(st.session_state.form_data['result2']['claim_data']['table_info']['cost_of_lawsuit'])}" , on_change= on_change_handler)
    # FIXME добавить 4 разных [ТЭ ГВС ФОТЭ СОИ] - вроде done
    st.session_state.form_data['lawsuit_info']['service_type'] = get_service_type()

#     service_type_info = []
    st.session_state.form_data['lawsuit_info']['claims'] = []
#     applications = {}
    #TODO: может быть несколько претензий в файле
    for contract_info in _parse_result.get("table_parser_result", []):
        claim_info = contract_info[6]
        for claim_item in claim_info:
            st.session_state.form_data['lawsuit_info']['claims'].append(f"№ {claim_item['claim_number']} от {claim_item['claim_date']}")

#     st.markdown(f"### Данные об услуге, полученные из договоров")
#     st.markdown(f"{'___'.join(f' - {elem}' for elem in service_type_info)}")

#     st.markdown(f'### Данные о претензиях')
    claims_edit = []
    # st.markdown(f"номера и даты претензий\n {'___'.join(f'- {claim}' for claim in claims)}")
    for i, claim in enumerate(st.session_state.form_data['lawsuit_info']['claims']):
        new_value = st.text_input(
            label=f"Претензия #{i + 1}",
            value=claim,
            key=f"claim_{i}",
            on_change= on_change_handler
        )
        claims_edit.append(new_value)
    st.session_state.form_data['lawsuit_info']['claims'] = claims_edit

    st.session_state.form_data['plaintiff_info'] = plaintiff_info

    st.session_state.form_data['defendant_info'] = defendant_info
#     lawsuit_info['claims'] = st.session_state.form_data['claims']

    st.markdown(f"### ФИО ответственного лица, подписывающего иск")
    st.session_state.form_data['responsitive_name'] = st.text_input("Введите имя ответственного лица", value="Самошкина А.Е." if st.session_state.form_data['responsitive_name'] is None else st.session_state.form_data['responsitive_name'] )

    st.markdown(f"### подтверждение данных и создание документов")
    if st.button(label="Нажмите, чтобы подтвердить правильность данных"):
        st.session_state.form_data['forms_changed'] = False
        _pi = st.session_state.form_data.get('plaintiff_info') or {}
        _plaintiff_labels = {
            'full_name': 'полное наименование истца',
            'short_name': 'сокращённое наименование истца',
            'addres': 'адрес истца',
            'ogrn': 'ОГРН истца',
            'inn': 'ИНН истца',
        }
        _missing_pl = [
            _plaintiff_labels[k]
            for k in _plaintiff_labels
            if not str(_pi.get(k, '')).strip()
        ]
        if _missing_pl:
            st.error(
                "Заполните данные об истце перед созданием документов: "
                + ", ".join(_missing_pl)
                + "."
            )
        elif not _parse_result.get("table_parser_result"):
            st.error("Нет данных парсинга документов. Повторите загрузку и расчёт.")
        else:
            with st.spinner(
                "Пересчёт пени с актуальными пунктами договоров и создание документов…"
            ):
                ok, calc_json, err = run_calculate_penalty(_parse_result)
            if not ok:
                st.error("Не удалось пересчитать пени перед созданием документов")
                st.text(err or "Неизвестная ошибка")
            else:
                st.session_state.form_data["result2"] = calc_json
                request_json = dict(calc_json["claim_data"])
                request_json["plaintiff_info"] = st.session_state.form_data["plaintiff_info"]
                request_json["defendant_info"] = st.session_state.form_data["defendant_info"]
                request_json["lawsuit_info"] = st.session_state.form_data["lawsuit_info"]
                request_json["responsitive_name"] = st.session_state.form_data["responsitive_name"]

                doc_creator_json = {
                    "claim_data": request_json,
                    "calculator_list": calc_json["calculator_list"],
                    "path_to_save": st.session_state.form_data["path_to_save"],
                }

                first_response = requests.post(
                    "http://localhost:5001/create_doc",
                    json=doc_creator_json,
                )

                if first_response.status_code == 200:
                    lawsuit = BytesIO(first_response.content)
                    st.session_state.form_data['lawsuit'] = lawsuit

                else:
                    st.error(f"Ошибка: {first_response.status_code}")
                    st.text(first_response.text)

                second_response = requests.post(
                    "http://localhost:5001/create_calculating_table",
                    json=doc_creator_json,
                )

                if second_response.status_code == 200:
                    lawsuit_table = BytesIO(second_response.content)
                    st.session_state.form_data['lawsuite_table'] = lawsuit_table
                    st.session_state.form_data['flag3'] = True

                elif second_response.status_code == 404:
                    st.error("Ошибка, проверьте, все ли поля заполнены корректно")
                else:
                    st.error("Ошибка, проверьте, все ли поля заполнены корректно")

if st.session_state.form_data['flag3'] and st.session_state.form_data['forms_changed']==False:
    col1, col2, = st.columns(2)

    with col1:
        st.download_button(
            label="Скачать иск",
            data=st.session_state.form_data['lawsuit'],
            file_name="Иск.docx",

        )

    with col2:
        st.download_button(
            label="Скачать расчёт к иску",
            data=st.session_state.form_data['lawsuite_table'],
            file_name="Расчёт к иску.docx",

        )

