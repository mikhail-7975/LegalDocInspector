import pandas as pd
from datetime import datetime, timedelta
from utils.HolidayChecker import HolidayChecker  # Импортируем наш класс для проверки праздников

# Инициализация проверщика праздников
holiday_checker = HolidayChecker(offline=True)

# Ставка ЦБ РФ (9.5%)
CB_RATE = 9.5 / 100

def get_next_workday_after_n_days(start_date, n_days):
    """Возвращает дату, которая наступает через n рабочих дней после start_date"""
    current_date = start_date
    workdays_passed = 0

    while workdays_passed < n_days:
        current_date += timedelta(days=1)
        if not holiday_checker.is_holiday_or_weekend(current_date):
            workdays_passed += 1

    return current_date

def calculate_penalty(debt, start_date, end_date, consumer_type, payment_amount=0, payment_date=None):
    """
    Расчет пеней в зависимости от типа потребителя и периода просрочки.

    :param debt: Сумма долга
    :param start_date: Начало периода просрочки (строка в формате "YYYY-MM-DD")
    :param end_date: Конец периода просрочки (строка в формате "YYYY-MM-DD")
    :param consumer_type: Тип потребителя ("Управляющая компания", "ТСЖ", "ЖСК", "ТСН", "Прочие")
    :param payment_amount: Сумма оплаты
    :param payment_date: Дата оплаты (объект datetime или None)
    :return: Сумма пеней и общее количество дней просрочки
    """
    # Преобразуем даты начала и конца просрочки в datetime
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Если payment_date уже является объектом datetime, преобразование не требуется
    # Если payment_date - строка, преобразуем её в datetime
    if payment_date and isinstance(payment_date, str):
        payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
    elif payment_date and isinstance(payment_date, datetime):
        payment_date = payment_date.date()

    # Инициализация переменной для хранения суммы пеней
    total_penalty = 0

    # Общее количество дней просрочки
    delta = (end_date - start_date).days + 1  # +1 чтобы включить оба конца периода

    # Учет оплаты, если она была произведена до или в период просрочки
    if payment_date:
        if payment_date < start_date:
            # Если оплата была произведена до начала периода, уменьшаем долг с самого начала
            debt -= payment_amount
            print(f"Оплата {payment_amount} руб. произведена до начала периода {start_date.strftime('%Y-%m-%d')}. Новый долг: {debt:.2f} руб.")
        elif start_date <= payment_date <= end_date:
            # Если оплата была произведена в период просрочки, уменьшаем долг на момент оплаты
            debt -= payment_amount
            print(f"Оплата {payment_amount} руб. произведена {payment_date.strftime('%Y-%m-%d')}. Новый долг: {debt:.2f} руб.")
        else:
            # Если оплата была произведена после окончания периода, она не учитывается
            print(f"Оплата {payment_amount} руб. произведена после окончания периода {end_date.strftime('%Y-%m-%d')} и не учитывается.")

    # Определяем подпериоды в зависимости от типа потребителя
    if consumer_type == "Управляющая компания":
        # Подпериод 1: с 1 по 60 день (рабочие дни)
        period1_start = get_next_workday_after_n_days(start_date, 1)  # Первый рабочий день
        period1_end = get_next_workday_after_n_days(period1_start, 59)  # +59 рабочих дней = всего 60

        # Рассчитываем фактическое количество дней между датами (включая выходные)
        days1 = (min(period1_end, end_date) - start_date).days + 1
        if days1 > 0:
            rate1 = 1 / 300
            penalty1 = debt * days1 * rate1 * CB_RATE
            total_penalty += penalty1
            print(f"{start_date.strftime('%Y-%m-%d')} -> {period1_end.strftime('%Y-%m-%d')}: {days1} дней, Пени: {penalty1:.2f} руб., Долг: {debt:.2f} руб.")

        # Подпериод 2: с 61 по 90 день (рабочие дни)
        if end_date > period1_end:
            period2_start = get_next_workday_after_n_days(period1_end, 1)
            period2_end = get_next_workday_after_n_days(period2_start, 29)  # +29 рабочих дней = всего 30 (61-90)

            days2 = (min(period2_end, end_date) - period2_start).days + 1
            if days2 > 0:
                rate2 = 1 / 170
                penalty2 = debt * days2 * rate2 * CB_RATE
                total_penalty += penalty2
                print(f"{period2_start.strftime('%Y-%m-%d')} -> {period2_end.strftime('%Y-%m-%d')}: {days2} дней, Пени: {penalty2:.2f} руб., Долг: {debt:.2f} руб.")

        # Подпериод 3: с 91 дня (рабочие дни)
        if end_date > period2_end:
            period3_start = get_next_workday_after_n_days(period2_end, 1)
            days3 = (end_date - period3_start).days + 1
            if days3 > 0:
                rate3 = 1 / 130
                penalty3 = debt * days3 * rate3 * CB_RATE
                total_penalty += penalty3
                print(f"{period3_start.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}: {days3} дней, Пени: {penalty3:.2f} руб., Долг: {debt:.2f} руб.")

    elif consumer_type in ["ТСЖ", "ЖСК", "ТСН"]:
        # Подпериод 1: с 1 по 30 день (рабочие дни)
        period1_start = get_next_workday_after_n_days(start_date, 1)  # Первый рабочий день
        period1_end = get_next_workday_after_n_days(period1_start, 29)  # +29 рабочих дней = всего 30

        days1 = (min(period1_end, end_date) - start_date).days + 1
        if days1 > 0:
            rate1 = 0  # Пени не начисляются
            penalty1 = debt * days1 * rate1 * CB_RATE
            total_penalty += penalty1
            print(f"{start_date.strftime('%Y-%m-%d')} -> {period1_end.strftime('%Y-%m-%d')}: {days1} дней, Пени: {penalty1:.2f} руб., Долг: {debt:.2f} руб.")

        # Подпериод 2: с 31 по 90 день (рабочие дни)
        if end_date > period1_end:
            period2_start = get_next_workday_after_n_days(period1_end, 1)
            period2_end = get_next_workday_after_n_days(period2_start, 59)  # +59 рабочих дней = всего 60 (31-90)

            days2 = (min(period2_end, end_date) - period2_start).days + 1
            if days2 > 0:
                rate2 = 1 / 300
                penalty2 = debt * days2 * rate2 * CB_RATE
                total_penalty += penalty2
                print(f"{period2_start.strftime('%Y-%m-%d')} -> {period2_end.strftime('%Y-%m-%d')}: {days2} дней, Пени: {penalty2:.2f} руб., Долг: {debt:.2f} руб.")

        # Подпериод 3: с 91 дня (рабочие дни)
        if end_date > period2_end:
            period3_start = get_next_workday_after_n_days(period2_end, 1)
            days3 = (end_date - period3_start).days + 1
            if days3 > 0:
                rate3 = 1 / 130
                penalty3 = debt * days3 * rate3 * CB_RATE
                total_penalty += penalty3
                print(f"{period3_start.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}: {days3} дней, Пени: {penalty3:.2f} руб., Долг: {debt:.2f} руб.")

    else:  # Прочие потребители
        # Подпериод 1: с 1 дня (рабочие дни)
        period1_start = get_next_workday_after_n_days(start_date, 1)
        days1 = (end_date - period1_start).days + 1
        if days1 > 0:
            rate1 = 1 / 130
            penalty1 = debt * days1 * rate1 * CB_RATE
            total_penalty += penalty1
            print(f"{period1_start.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}: {days1} дней, Пени: {penalty1:.2f} руб., Долг: {debt:.2f} руб.")

    return total_penalty, delta

if __name__ == "__main__":
    file_path = '08.184032-ТЭ 08.2023-10.2024.XLS'
    sheet_name = 'Лист1'

    # Чтение данных из файла
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    # Поиск строки с потребителем ТЭ
    consumer_te_row_index = None
    for i in range(len(df)):
        if "Потребитель ТЭ" in str(df.iloc[i, 0]):
            consumer_te_row_index = i
            break

    if consumer_te_row_index is None:
        raise ValueError("Строка с потребителем ТЭ не найдена.")

    # Извлечение данных о потребителе ТЭ
    consumer_te = df.iloc[consumer_te_row_index, 1]

    # Проверка, что consumer_te является строкой
    if not isinstance(consumer_te, str):
        consumer_te = str(consumer_te)

    # Определение типа потребителя
    consumer_type = "Прочие"  # По умолчанию

    # Приводим название потребителя к нижнему регистру для унификации
    consumer_te_lower = consumer_te.lower()

    # Проверяем все возможные варианты написания
    if any(keyword in consumer_te_lower for keyword in ["управляющая компания", "управляющая организация"]):
        consumer_type = "Управляющая компания"
    elif any(keyword in consumer_te_lower for keyword in ["товарищество собственников жилья", "тсж"]):
        consumer_type = "ТСЖ"
    elif any(keyword in consumer_te_lower for keyword in ["жилищно-строительный кооператив", "жилищно - строительный кооператив", "жск"]):
        consumer_type = "ЖСК"
    elif any(keyword in consumer_te_lower for keyword in ["товарищество собственников недвижимости", "тсн"]):
        consumer_type = "ТСН"

    # Поиск строки с заголовком "Задолженность"
    header_row_index = None
    for i, row in df.iterrows():
        if any("Задолженность" in str(cell) for cell in row):
            header_row_index = i
            break

    if header_row_index is None:
        raise ValueError("Строка с заголовком 'Задолженность' не найдена.")

    # Установка заголовков столбцов
    df.columns = df.iloc[header_row_index]

    # Удаление строк до заголовка
    df = df.iloc[header_row_index + 1:].reset_index(drop=True)

    def parse_date(date_str):
        if pd.notna(date_str):
            return datetime.strptime(date_str, "%d.%m.%Y")  # Формат "дд.мм.гггг"
        return None

    # Инициализация списков для хранения данных
    months = []          # Список для хранения месяцев
    debts = []           # Список для хранения задолженностей
    payments = []        # Список для хранения сумм оплат
    payment_dates = []   # Список для хранения дат оплат

    # Проход по строкам для извлечения данных о месяце, задолженности, оплате и дате оплаты
    for i in range(len(df)):
        month = df.iloc[i, 0]  # Месяц (например, "05.2024")
        debt = df.iloc[i, 1]   # Задолженность (столбец "Сумма")

        # Проверка, что месяц обозначен числом (например, "05.2024")
        if pd.notna(month) and isinstance(month, str) and '.' in month:
            # Оставляем только месяц в формате чисел (например, "05.2024" -> "05")
            month_number = month.split('.')[0]
            year_number = month.split('.')[1]
            months.append(f"{month_number}.{year_number}")  # Сохраняем месяц и год
            debts.append(debt if pd.notna(debt) else 0)  # Если задолженность не указана, считаем её равной 0

            # Поиск оплаты для этого месяца (она может быть на следующей строке)
            payment = 0
            payment_date = None
            if i + 1 < len(df):  # Проверяем, что следующая строка существует
                next_row = df.iloc[i + 1]
                if pd.notna(next_row[2]):  # Если в следующей строке есть дата оплаты (столбец "C")
                    payment_date = next_row[2]  # Дата оплаты
                    payment = next_row[3] if pd.notna(next_row[3]) else 0  # Сумма оплаты (столбец "D")

            payments.append(payment)
            payment_dates.append(payment_date)

    # Определение первой даты из таблицы
    first_month_year = months[0]  # Первый месяц и год из списка (например, "08.2023")
    first_month, first_year = first_month_year.split('.')
    first_date = datetime(year=int(first_year), month=int(first_month), day=1)  # Первый день месяца

    # Функция для расчета дней от 18 числа следующего месяца до 25.11.2024
    def calculate_days_from_18(month, year, target_date="25.11.2024"):
        # Преобразуем месяц в число
        month = int(month)
        year = int(year)
        # Создаем дату 18 числа следующего месяца
        next_month = month + 1 if month < 12 else 1
        #next_year = year if month < 12 else year + 1
        date_18 = datetime(year=year, month=next_month, day=18)
        # Преобразуем целевую дату в объект datetime
        target_date = datetime.strptime(target_date, "%d.%m.%Y")
        # Вычисляем разницу в днях
        delta = (target_date - date_18).days
        return delta

    # Вывод извлеченных данных и расчет пеней
    print(f"Потребитель ТЭ: {consumer_te}")
    print(f"Тип потребителя: {consumer_type}")
    total_penalty_sum = 0  # Итоговая сумма пеней

    for month_year, debt, payment, payment_date in zip(months, debts, payments, payment_dates):
        month, year = month_year.split('.')
        # Дата начала просрочки: 18 число следующего месяца
        start_date = datetime(int(year), int(month) + 1, 18) if int(month) < 12 else datetime(int(year) + 1, 1, 18)
        end_date = datetime(2025, 1, 25)  # Фиксированная конечная дата
        days_from_18 = (end_date - start_date).days

        # Преобразуем payment_date в datetime, если он указан
        if payment_date and isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, "%d.%m.%Y")

        # Вызов функции calculate_penalty с учетом оплаты
        penalty, delta = calculate_penalty(debt, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), consumer_type, payment, payment_date)
        total_penalty_sum += penalty  # Суммируем пени
        print(f"Месяц: {month_year}, Задолженность: {debt}, Оплата: {payment}, Дата оплаты: {payment_date}, Дней от 18 числа следующего месяца до 25.11.2024: {days_from_18}, Пени: {penalty:.2f} руб.")

    # Вывод итоговой суммы пеней
    print(f"Итоговая сумма пеней: {total_penalty_sum:.2f} руб.")