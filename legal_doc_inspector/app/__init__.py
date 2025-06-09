from flask import Flask, g
from configs.config import load_yaml_config

def create_app():
    app = Flask(__name__)
    
    with app.app_context():
        # Import parts of our application
        from . import routes
        
        @app.before_request
        def add_configs():
            if "config" not in g:
                g.config = load_yaml_config('configs/debug_config.yaml')
        def add_doc_processors():
            pass

        return app
