from ___legal_doc_inspector.app import create_app

# TODO
# add llm starting and terminating

app = create_app()

if __name__ == "__main__":
    app.run(debug=False, port=5001)
