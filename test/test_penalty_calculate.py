from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import _calculate_penalty_for_each_period, StrictFormattedMoney

def test_penalty_calculation_261437_43_130():
    """Специфический тест для случая: 261 437,00 × 43 × 1/130 × 9,5% = 8 215,15"""
    periods = [{
        'type': 'penalty_period',
        'debt': '261437,00',
        'period': ('2023-01-01', '2023-02-12', 43),
        'penalty_period_info': (Decimal('0.095'), '1/130')
    }]
    
    updated_periods, total_penalty, total_debt = _calculate_penalty_for_each_period(periods)
    
    # Проверяем, что пеня равна 8 215,15 (а не 8 215,16)
    assert updated_periods[0]['penalty'] == '8 215,15', f"Expected 8 215,15, got {updated_periods[0]['penalty']}"
    assert total_penalty == StrictFormattedMoney('8215,15')
    assert total_debt == StrictFormattedMoney('261437,00')

def test_penalty_truncation_method():
    """Тест метода отбрасывания знаков после третьего"""
    # Пример: 8215,154961538461...
    penalty_value = Decimal('8215.154961538461')
    
    # Отбрасываем все после третьего знака (не округляем)
    penalty_truncated = penalty_value.quantize(Decimal('0.001'), rounding=ROUND_DOWN)
    assert penalty_truncated == Decimal('8215.154')
    
    # Затем округляем до 2 знаков
    penalty_rounded = penalty_truncated.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    assert penalty_rounded == Decimal('8215.15')
    
    # Другой пример: 8215,155961538461...
    penalty_value2 = Decimal('8215.155961538461')
    penalty_truncated2 = penalty_value2.quantize(Decimal('0.001'), rounding=ROUND_DOWN)
    assert penalty_truncated2 == Decimal('8215.155')
    
    penalty_rounded2 = penalty_truncated2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    assert penalty_rounded2 == Decimal('8215.16')

def test_penalty_calculation_edge_cases():
    """Тест граничных случаев с отбрасыванием знаков"""
    test_cases = [
        # (точное значение, ожидаемый результат)
        ('8215.154961538461', '8 215,15'),  # третий знак 4 -> округляем вниз
        ('8215.155000000000', '8 215,16'),  # третий знак 5 -> округляем вверх
        ('8215.154999999999', '8 215,15'),  # третий знак 4 -> округляем вниз
        ('8215.155000000001', '8 215,16'),  # третий знак 5 -> округляем вверх
        ('100.004999999999', '100,00'),    # третий знак 4 -> округляем вниз
        ('100.005000000000', '100,01'),    # третий знак 5 -> округляем вверх
    ]
    
    for exact_value, expected in test_cases:
        penalty_value = Decimal(exact_value)
        
        # Отбрасываем все после третьего знака
        penalty_truncated = penalty_value.quantize(Decimal('0.001'), rounding=ROUND_DOWN)
        
        # Округляем до 2 знаков
        penalty_rounded = penalty_truncated.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Создаем StrictFormattedMoney для форматирования
        penalty = StrictFormattedMoney(penalty_rounded)
        
        assert str(penalty) == expected, f"Failed for {exact_value}: expected {expected}, got {penalty}"