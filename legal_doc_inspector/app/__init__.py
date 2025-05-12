from flask import Flask, g


def create_app():
    app = Flask(__name__)

    with app.app_context():
        # Import parts of our application
        from . import server

        @app.before_request
        def add_doc_processors():
            pass

        return app
