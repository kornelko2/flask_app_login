from db_extension import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='locked')

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    stock_ticker = db.Column(db.String(10), nullable=False)
    stock_price = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    transaction_cost = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Float, nullable=False)
    total_transaction_cost = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)

class SP500Ticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)