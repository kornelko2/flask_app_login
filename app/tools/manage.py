from flask import Flask
from flask_migrate import Migrate
from db_extension import db
from models import User, Transaction, SP500Ticker, Portfolio
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    from flask.cli import main
    main()