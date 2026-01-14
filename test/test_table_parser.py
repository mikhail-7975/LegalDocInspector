import pytest
from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser

TEST_CASES = [
    "test/excel_test_cases/1. 02.108320-ТЭ   08.2025.XLSM",
    "test/excel_test_cases/3. 05.415425-ТЭ.XLSM",
    "test/excel_test_cases/4. Справка  06.530445-ТЭ 06.2025-08.2025.XLSM",
    "test/excel_test_cases/6. 07.642317-ТЭ(0825).XLSM",
]
TEST_RESULTS = [
    {'Август 2025': {'accrual': {'accruals': [{'accrual': 1152128.21,
     'period': '08.2025'}],
   'payments': [],
   'additionals': [],
   'total_amount_of_accruals': 1152128.21,
   'total_amount_of_payments': 0,
   'debt': 1152128.21},
  'adjustment': {'accruals': [],
   'payments': [],
   'additionals': [],
   'total_amount_of_accruals': None,
   'total_amount_of_payments': None,
   'debt': None}}},

   {'Август 2025': {'accrual': {'accruals': [{'accrual': 770705.87,
     'period': '08.2025'}],
   'payments': [{'payment': 32145.12,
     'date': '11.04.2023',
     'contract_type': 8903},
    {'payment': 148269.8, 'date': '22.05.2023', 'contract_type': 8903}],
   'additionals': [],
   'total_amount_of_accruals': 770705.87,
   'total_amount_of_payments': 180414.92,
   'debt': 590290.95},
  'adjustment': {'accruals': [],
   'payments': [{'payment': 73383.5,
     'date': '06.05.2025',
     'contract_type': 8905},
    {'payment': 105589.6, 'date': '06.05.2025', 'contract_type': 8905}],
   'additionals': [{'accrual': 178973.1, 'period': '12.2024'}],
   'total_amount_of_accruals': 178973.1,
   'total_amount_of_payments': 178973.1,
   'debt': 0}}},

    {'Август 2025': {'accrual': {'accruals': [{'accrual': 348619.16,
     'period': '08.2025'}],
   'payments': [],
   'additionals': [],
   'total_amount_of_accruals': 348619.16,
   'total_amount_of_payments': 0,
   'debt': 348619.16},
  'adjustment': {'accruals': [],
   'payments': [{'payment': 18349.97,
     'date': '09.04.2025',
     'contract_type': None}],
   'additionals': [{'accrual': 18349.97, 'period': '12.2024'}],
   'total_amount_of_accruals': 18349.97,
   'total_amount_of_payments': 18349.97,
   'debt': 0}}},

   {'Август 2025': {'accrual': {'accruals': [{'accrual': 1940264.39,
     'period': '08.2025'}],
   'payments': [{'payment': 99790.81,
     'date': '14.11.2025',
     'contract_type': 8907},
    {'payment': 200000, 'date': '26.11.2025', 'contract_type': 8907}],
   'additionals': [],
   'total_amount_of_accruals': 1940264.39,
   'total_amount_of_payments': 299790.81,
   'debt': 1640473.58},
  'adjustment': {'accruals': [],
   'payments': [{'payment': 133631.8,
     'date': '24.04.2025',
     'contract_type': 8907},
    {'payment': 16556.12, 'date': '25.04.2025', 'contract_type': 8907}],
   'additionals': [{'accrual': 150187.92, 'period': '12.2024'}],
   'total_amount_of_accruals': 150187.92,
   'total_amount_of_payments': 150187.92,
   'debt': 0}}}

]
def test_parse_table():
    parser = TableParser()
    for test_input, test_output in zip(TEST_CASES, TEST_RESULTS):
        parser.open(test_input)
        result = parser.parse()
        assert result == test_output
        parser.close()