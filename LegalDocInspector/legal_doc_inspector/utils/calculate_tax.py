from decimal import Decimal, ROUND_HALF_UP
from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import StrictFormattedMoney
def calculate_state_duty(amount_input):
    if isinstance(amount_input, str):
        amount = StrictFormattedMoney(amount_input)
    elif isinstance(amount_input, StrictFormattedMoney):
        amount = amount_input
    else:
        raise TypeError("Ожидалась строка или StrictFormattedMoney")

    total = amount.amount  # Decimal с 2 знаками

    if total <= Decimal('100000'):
        duty = Decimal('10000')
    elif total <= Decimal('1000000'):
        excess = total - Decimal('100000')
        duty = Decimal('10000') + excess * Decimal('0.05')
    elif total <= Decimal('10000000'):
        excess = total - Decimal('1000000')
        duty = Decimal('55000') + excess * Decimal('0.03')
    elif total <= Decimal('50000000'):
        excess = total - Decimal('10000000')
        duty = Decimal('325000') + excess * Decimal('0.01')
    else:
        excess = total - Decimal('50000000')
        duty = Decimal('725000') + excess * Decimal('0.005')
        if duty > Decimal('10000000'):
            duty = Decimal('10000000')

    # 🔑 Округляем до целого рубля по правилам НК РФ: ROUND_HALF_UP до 0 знаков
    duty = duty.quantize(Decimal('1'), rounding=ROUND_HALF_UP)  # ← целое число рублей

    return str(StrictFormattedMoney(duty, currency='RUB'))