import json
import random
from datetime import datetime
from datetime import timedelta


def generate_date(_start_date: datetime = None, _end_date: datetime = None) -> datetime:
    start_date = datetime(998, 1, 1) if _start_date is None else _start_date
    end_date = datetime(2025, 12, 31) if _end_date is None else _end_date

    # Вычисляем разницу в днях между датами
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days

    # Генерируем случайное число дней
    random_number_of_days = random.randrange(days_between_dates)

    # Добавляем случайное количество дней к начальной дате
    random_date = start_date + timedelta(days=random_number_of_days)

    return random_date


def generate_contract_number():
    number = random.randrange(100000, 999999)
    date = generate_date()
    return f"01.{number} от {date.strftime("%d.%m.%Y")}"


def generate_debt():
    return f"{random.randrange(1, 9)} {random.randrange(100, 999)} {random.randrange(100, 999)},{random.randrange(10, 99)}"


def generate_peny():
    return f"{random.randrange(10, 99)} {random.randrange(100, 999)},{random.randrange(10, 99)}"


def generate_payment():
    debt = generate_debt()
    start_date = generate_date()
    end_date = generate_date(_start_date = start_date)
    period_days = end_date - start_date
    share = random.randrange(100, 999)
    payment = {
        "debt": debt,
        "start_date": start_date.strftime("%d.%m.%Y"),
        "end_date": end_date.strftime("%d.%m.%Y"),
        "period_days": str(period_days.days),
        "interest_rate": "9.5%",
        "share": f"1/{share}",
        "formulae": f"{debt} × {str(period_days.days)} × 1/{share} × 9.5%",
        "peny": generate_peny()
    }
    return payment


def generate_period(number_of_payments_1: int = 3, number_of_payments_2: int = 3):
    period = {
        "period": f"{generate_date().strftime("%m.%Y")}-{generate_date().strftime("%m.%Y")}",
        "first_debt": generate_debt(),
        "first_date": generate_date().strftime("%d.%m.%Y"),
        "payments_1": [generate_payment() for _ in range(number_of_payments_1)],
        "second_debt": generate_debt(),
        "second_date": generate_date().strftime("%d.%m.%Y"),
        "payments_2": [generate_payment() for _ in range(number_of_payments_2)],
        "result": generate_debt()
    }
    return period


def generate_contract(number_of_periods: int):
    contract = {
        "contract_number": generate_contract_number(),
        "start_date_of_delay": generate_date().strftime("%d.%m.%Y"),
        "end_date_of_delay": generate_date().strftime("%d.%m.%Y"),
        "periods": [generate_period() for _ in range(number_of_periods)],
        "sum_debt": generate_debt(),
        "sum_peny": generate_peny()
    }
    return contract


def load_config(filename: str):
    data = {"contracts": []}
    for i in range(5):
        data["contracts"].append(generate_contract(3))

    with open(filename, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    filename = "lawsuits.json"
    load_config(filename)
