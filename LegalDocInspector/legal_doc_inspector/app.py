from LegalDocInspector.legal_doc_inspector.utils.calculator_adapter import convert_data
from LegalDocInspector.legal_doc_inspector.calculator.penalty_calculator import calculate_penalty
from LegalDocInspector.legal_doc_inspector.utils.parse_info_by_inn import parse_html # класс
from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser
from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import CalculationClaimGenerator
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator

from .llm_functions import parse_claim, parse_contract

class LegalDocApp():
    def __init__(self):
        self.table_parser = TableParser()
        self.claim_generator = ClaimGenerator()
        self.calculation_claim_generator = CalculationClaimGenerator()

    def parse(self, args):
        pass

    def calculate(self,):
        pass

    def generate(self, ):
        pass