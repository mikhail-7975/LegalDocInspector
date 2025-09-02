from LegalDocInspector.backend import create_app


# TODO
# add llm starting and terminating
print()
app = create_app()

if __name__ == "__main__":
    app.run(debug=False, port=5001)
