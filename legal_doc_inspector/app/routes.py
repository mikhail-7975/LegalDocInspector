from flask import Response
from flask import current_app as app
from flask import g, render_template, request


@app.route("/")
def home():
    return "main page"


@app.route("/parse")
def parse():
    # TODO
    # add pdf, exel and zip file receiving from post request
    # after navigating to endpoint:
    # - create folder with date and time in folder name
    # - save files to the folder
    # path to the folder must be loaded from config. Now it can be global variable
    return "parse endpoint"


@app.route("/create_doc")
def create_doc():
    # TODO
    # add a file download when navigating to the endpoint in the browser
    return "create_doc endpoint"
