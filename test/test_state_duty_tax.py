import pytest
from LegalDocInspector.legal_doc_inspector.utils.calculate_tax import StrictFormattedMoney, calculate_state_duty


# Тестовые кейсы: (вход, ожидаемая пошлина ЦЕЛЫМИ РУБЛЯМИ)
TEST_CASES_ROUNDED = [
    # До 100k
    ("50 000,00", "10 000,00"),
    ("100 000,00", "10 000,00"),

    # 5% диапазон
    ("100 000,01", "10 000,00"),   # 10000.0005 → 10000
    ("100 009,99", "10 000,00"),   # 10000 + 9.99*0.05 = 10000.4995 → 10000
    ("100 010,00", "10 001,00"),   # 10.00 * 0.05 = 0.50 → 10000.50 → округляется до 10001!
    ("200 000,00", "15 000,00"),

    # 3% диапазон
    ("1 000 000,00", "55 000,00"),
    ("1 000 033,33", "55 001,00"),  # 33.33 * 0.03 = 0.9999 → 55000.9999 → 55001
    ("1 000 033,34", "55 001,00"),  # всё ещё < 55001.50
    ("1 000 066,66", "55 002,00"),  # 66.66 * 0.03 = 1.9998 → 55001.9998 → 55002

    # 1% диапазон
    ("10 000 000,00", "325 000,00"),
    ("10 000 049,99", "325 000,00"),  # 49.99 * 0.01 = 0.4999 → 325000.4999 → 325000
    ("10 000 050,00", "325 001,00"),  # 0.50 → округляется вверх

    # 0.5% диапазон
    ("50 000 000,00", "725 000,00"),
    ("50 000 099,99", "725 000,00"),  # 99.99 * 0.005 = 0.49995 → 725000.49995 → 725000
    ("50 000 100,00", "725 001,00"),  # 100 * 0.005 = 0.50 → 725000.50 → 725001

    # Максимум
    ("2 000 000 000,00", "10 000 000,00"),
]


@pytest.mark.parametrize("input_amount, expected_rubles", TEST_CASES_ROUNDED)
def test_calculate_state_duty_whole_rubles(input_amount, expected_rubles):
    result = calculate_state_duty(input_amount)
    
    assert str(result) == expected_rubles

TEST_CASES_CUSTOM = [
    ("669 241,87", "38 462,00")
]
@pytest.mark.parametrize("input, expected", TEST_CASES_CUSTOM)
def test_calculating(input, expected):
    assert calculate_state_duty(input) == expected