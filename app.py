from fitlog import create_app

app = create_app()

if __name__ == "__main__":
    # Debug nur in der Entwicklung aktivieren.
    app.run(debug=True)
