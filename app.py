from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# .env laden
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db = SQLAlchemy(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/plan/new")
def plan_new():
    return render_template("plan_new.html")

@app.route("/plan/edit")
def plan_edit():
    return render_template("plan_edit.html")

@app.route("/training")
def training():
    return render_template("training.html")

if __name__ == "__main__":
    app.run(debug=True)
