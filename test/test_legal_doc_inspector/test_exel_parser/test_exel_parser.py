from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser

def test_table_1():
    table_parser = TableParser()
    certificate_file_path = "data/input_examples/claim_3/complect_1/05.413208.XLS"
    table_parser.open(certificate_file_path)
    result = table_parser.parse()
    defendant_inn = table_parser.parse_defendant_inn()
    contract_number = table_parser.parse_contract_number()

    gt_defendant_inn = "7722165445"
    gt_contract_number = "№ 05.413208ГВС от 01.02.2012"
    gt_result = {
                "Февраль 2025": {
                    "accrual": {
                        "accruals": [
                            {
                                "accrual": 202443.58,
                                "period": "02.2025"
                            }
                        ],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": 202443.58,
                        "total_amount_of_payments": 0,
                        "debt": 202443.58
                    },
                    "adjustment": {
                        "accruals": [],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": None,
                        "total_amount_of_payments": None,
                        "debt": None
                    }
                },
                "Март 2025": {
                    "accrual": {
                        "accruals": [
                            {
                                "accrual": 200823.53,
                                "period": "03.2025"
                            }
                        ],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": 200823.53,
                        "total_amount_of_payments": 0,
                        "debt": 200823.53
                    },
                    "adjustment": {
                        "accruals": [],
                        "payments": [],
                        "additionals": [],
                        "total_amount_of_accruals": None,
                        "total_amount_of_payments": None,
                        "debt": None
                    }
                }
            }
    
    assert result == gt_result
    assert defendant_inn == gt_defendant_inn
    assert contract_number == gt_contract_number