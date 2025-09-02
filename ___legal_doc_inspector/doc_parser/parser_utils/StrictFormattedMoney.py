from decimal import Decimal, ROUND_HALF_UP

class StrictFormattedMoney:
    def __init__(self, amount, currency='RUB'):
        # Всегда преобразуем к Decimal с 2 знаками после запятой
        if not isinstance(amount, (Decimal, StrictFormattedMoney, str)):
            amount = Decimal(str(amount))
        if isinstance(amount, str):
            amount = amount.replace(' ', '')
            amount = amount.replace(',','.')
            if 'руб.' in amount:
                amount = amount.replace('руб.', '')
            # print(amount)
            self.amount = Decimal(str(amount))
            self.currency = currency
        if isinstance(amount, StrictFormattedMoney):
            self.amount = amount.amount
            self.currency = amount.currency
        if isinstance(amount, Decimal):
            self.amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.currency = currency
    
    def __str__(self):
        return self.format()
    
    def format(self, decimal_separator=',', thousands_separator=' '):
        """Форматирование суммы с правильной обработкой отрицательных чисел"""
        amount_str = str(self.amount)
        
        # Проверяем, отрицательное ли число
        is_negative = amount_str.startswith('-')
        if is_negative:
            amount_str = amount_str[1:]  # Убираем минус для обработки
        
        # Разделяем целую и дробную части
        if '.' in amount_str:
            integer_part, decimal_part = amount_str.split('.')
        else:
            integer_part, decimal_part = amount_str, '00'
        
        # Добиваем дробную часть до 2 знаков
        decimal_part = decimal_part.ljust(2, '0')[:2]
        
        # Добавляем разделители тысяч
        formatted_integer = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = thousands_separator + formatted_integer
            formatted_integer = digit + formatted_integer
        
        # Добавляем минус обратно без пробела
        if is_negative:
            formatted_integer = '-' + formatted_integer
        
        return f"{formatted_integer}{decimal_separator}{decimal_part}"
    
    def __add__(self, other):
        if not isinstance(other, StrictFormattedMoney):
            raise TypeError("Можно складывать только с StrictFormattedMoney")
        if self.currency != other.currency:
            raise ValueError("Валюты должны совпадать")
        
        return StrictFormattedMoney(self.amount + other.amount, self.currency)
    
    def __sub__(self, other):
        if not isinstance(other, StrictFormattedMoney):
            raise TypeError("Можно вычитать только StrictFormattedMoney")
        if self.currency != other.currency:
            raise ValueError("Валюты должны совпадать")
        
        return StrictFormattedMoney(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier):
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Можно умножать только на число")
        
        return StrictFormattedMoney(self.amount * Decimal(str(multiplier)), self.currency)
    
    def __truediv__(self, divisor):
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Можно делить только на число")
        
        return StrictFormattedMoney(self.amount / Decimal(str(divisor)), self.currency)
