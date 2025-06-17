import math

def calculate_state_duty(amount_str: str):
    rubles, kopecks = amount_str.replace(' ','').split(',')
    total_rubles = int(rubles) + int(kopecks) / 100

    if total_rubles <= 100_000:
        duty = 10_000.0
    elif total_rubles <= 1_000_000:
        excess = total_rubles - 100_000
        duty = 10_000.0 + excess * 0.05
    elif total_rubles <= 10_000_000:
        excess = total_rubles - 1_000_000
        duty = 55_000.0 + excess * 0.03
    elif total_rubles <= 50_000_000:
        excess = total_rubles - 10_000_000
        duty = 325_000.0 + excess * 0.01
    else: 
        excess = total_rubles - 50_000_000
        duty = 725_000.0 + excess * 0.005
        if duty > 10_000_000:
            duty = 10_000_000.0

    value = round(duty, 2)  
    rubbles = int(value)
    kopecks = int(round(value - rubbles, 2) * 100)

    rubbles_str = str(rubbles)
    formatted = ''
    for i, digit in enumerate(rubbles_str[::-1]):
        if i % 3 == 0 and i != 0:
            formatted = ' ' + formatted
        formatted = digit + formatted

    text = math.ceil(float(f"{formatted}.{kopecks}"))
    
    return f"{text},00"
