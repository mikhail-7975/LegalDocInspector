from flask import Flask, g
from ___legal_doc_inspector.doc_parser.table_parser_new import TableParser

def create_app():
    app = Flask(__name__)

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
            pass

        return app
