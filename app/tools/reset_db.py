from app import app, db
from models import User, Transaction, SP500Ticker, Portfolio

with app.app_context():
    # Drop all tables
    db.drop_all()
    print("All tables dropped.")

    # Recreate all tables
    db.create_all()
    print("All tables recreated.")