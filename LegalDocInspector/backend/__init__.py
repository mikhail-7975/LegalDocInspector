from flask import Flask, g
from configs.config import load_yaml_config
from LegalDocInspector.legal_doc_inspector.exel_parser import TableParser
from LegalDocInspector.legal_doc_inspector.doc_creator.calculation_claim_generator import CalculationClaimGenerator
from LegalDocInspector.legal_doc_inspector.doc_creator.claim_generator import ClaimGenerator
from LegalDocInspector.legal_doc_inspector.pdf_parser.parser_models import PDFClaimParser, PDFContractParser

def create_app():
    app = Flask(__name__)
    contract_parser = PDFContractParser()
    claim_parser = PDFClaimParser()
    with app.app_context():
        # Import parts of our application
        from . import routes

        @app.before_request
        def add_configs():
            if "config" not in g:
                g.config = load_yaml_config('configs/debug_config.yaml')
        @app.before_request
        def add_doc_processors():
            if "table_parser" not in g:
                g.table_parser = TableParser()
            if 'claim_generator' not in g:
                g.claim_generator = ClaimGenerator()
            if 'calc_claim_generator' not in g:
                g.calc_claim_generator = CalculationClaimGenerator()
            if 'contract_parser' not in g:
                g.contract_parser = contract_parser
            if 'claim_parser' not in g:
                g.claim_parser = claim_parser
            pass

        return app
