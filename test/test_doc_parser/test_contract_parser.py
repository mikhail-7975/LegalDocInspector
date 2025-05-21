from legal_doc_inspector.doc_parser.contract_parser import contract_parser

def test_contract_parser():
    test_contract_parser = contract_parser()
    question = "До какого числа пользователь должен внести оплату"
    chunks = test_contract_parser.pdf_to_text("path")
    response = test_contract_parser.parse(chunks, question)
    return response
