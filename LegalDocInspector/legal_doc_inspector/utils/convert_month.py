def last_day_of_month(month: str) -> str:
    """Метод вычисляет последний день месяца (например, в июне последний день 30, а в июле 31)
    и возвращает дату в формате ДД.ММ.ГГГГ (строка)

    Args:
        month (str): месяц, в котором нужно найти последнюю дату. Принимает строку формата ММ.ГГГГ

    Returns:
        str: дата в формате ДД.ММ.ГГГГ (строка)
    """
    _month = int(month.split(".")[0])

    if _month in [1, 3, 5, 7, 8, 10, 12]:
        return "31." + month
    elif _month in [4, 6, 9, 11]:
        return "30." + month
    elif _month == 2:
        _year = int(month.split(".")[1])
        if (_year - 2000) % 4 == 0:
            return "29." + month    # Год високосный
        else:
            return "28." + month    # Год не високосный


def convert_month(month: str) -> str:
    match month.lower():
        case "январь":
            return "01"
        case "февраль":
            return "02"

        case "март":
            return "03"
        case "апрель":
            return "04"
        case "май":
            return "05"

        case "июнь":
            return "06"
        case "июль":
            return "07"
        case "август":
            return "08"

        case "сентябрь":
            return "09"
        case "октябрь":
            return "10"
        case "ноябрь":
            return "11"

        case "декабрь":
            return "12"

        case _:
            print(f"Месяц {month.lower()} не соответствует ни одному нормальному месяцу")
            raise RuntimeError(f"Invalid month: {month.lower()}")