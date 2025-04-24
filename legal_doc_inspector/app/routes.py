from flask import Response
from flask import current_app as app
from flask import g, render_template, request



@app.route("/")
def home():
    return "main page"


@app.route("/parse")
def parse():
    return "parse endpoint"


@app.route("/create_doc")
def create_doc():
    return "create_doc endpoint"
