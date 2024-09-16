from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app.models import Portfolio, Transaction, User
import yfinance as yf
from app.db_extension import db 

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions', methods=['GET', 'POST'])
def transactions():
    if 'user' not in session:
        flash('You need to be logged in to view this page.')
        return redirect(url_for('login'))
    
    username = session['user']
    user = User.query.filter_by(username=username).first()
    user_id = user.id
    
    if request.method == 'POST':
        portfolio_id = request.form['portfolio_id']
        date = request.form['date']
        stock_ticker = request.form['stock_ticker']
        stock_price = float(request.form['stock_price'])
        transaction_type = request.form['transaction_type']
        transaction_cost = float(request.form['transaction_cost'])
        stock_quantity = float(request.form['stock_quantity'])
        currency = request.form['currency']
        
        total_transaction_cost = stock_price * stock_quantity + transaction_cost
        
        new_transaction = Transaction(
            user_id=user_id,
            portfolio_id=portfolio_id,
            date=date,
            stock_ticker=stock_ticker,
            stock_price=stock_price,
            transaction_type=transaction_type,
            transaction_cost=transaction_cost,
            stock_quantity=stock_quantity,
            total_transaction_cost=total_transaction_cost,
            currency=currency
        )
        
        db.session.add(new_transaction)
        db.session.commit()
        
        flash('Transaction added successfully.')
        return redirect(url_for('transactions'))
    
    portfolios = Portfolio.query.filter_by(user_id=user_id).all()
    selected_portfolio_ids = request.args.getlist('portfolio_id')
    if 'all' in selected_portfolio_ids or not selected_portfolio_ids:
        transactions = Transaction.query.filter_by(user_id=user_id).all()
    else:
        transactions = Transaction.query.filter(Transaction.portfolio_id.in_(selected_portfolio_ids), Transaction.user_id == user_id).all()

    # Fetch current prices using yfinance
    current_prices = {}
    positions = []
    for transaction in transactions:
        stock_ticker = transaction.stock_ticker
        if stock_ticker not in current_prices:
            stock_info = yf.Ticker(stock_ticker)
            try:
                current_price = stock_info.history(period='1d')['Close'].iloc[0]
                current_prices[stock_ticker] = current_price
            except Exception as e:
                current_prices[stock_ticker] = None
                flash(f'Error fetching current price for {stock_ticker}: {e}')

    # Calculate positions and unrealized profits
    positions_dict = {}
    for transaction in transactions:
        stock_ticker = transaction.stock_ticker
        if stock_ticker not in positions_dict:
            positions_dict[stock_ticker] = [0, 0, 0, transaction.currency]  # [quantity, total_cost, avg_price, currency]
        if transaction.transaction_type == 'buy':
            positions_dict[stock_ticker][0] += transaction.stock_quantity
            positions_dict[stock_ticker][1] += transaction.total_transaction_cost
        elif transaction.transaction_type == 'sell':
            positions_dict[stock_ticker][0] -= transaction.stock_quantity
            positions_dict[stock_ticker][1] -= transaction.total_transaction_cost
        positions_dict[stock_ticker][2] = positions_dict[stock_ticker][1] / positions_dict[stock_ticker][0] if positions_dict[stock_ticker][0] != 0 else 0

    unrealized_profits = {}
    for stock_ticker, values in positions_dict.items():
        quantity, total_cost, avg_price, currency = values
        current_price = current_prices.get(stock_ticker, None)
        unrealized_profit = (current_price - avg_price) * quantity if current_price is not None else None
        positions.append((stock_ticker, quantity, total_cost, avg_price, current_price, unrealized_profit, currency))
        unrealized_profits[stock_ticker] = unrealized_profit

    # Calculate realized profits
    realized_profits = []
    for stock_ticker in set([t.stock_ticker for t in transactions]):
        buys = [t for t in transactions if t.stock_ticker == stock_ticker and t.transaction_type == 'buy']
        sells = [t for t in transactions if t.stock_ticker == stock_ticker and t.transaction_type == 'sell']
        
        buy_index = 0
        sell_index = 0
        while buy_index < len(buys) and sell_index < len(sells):
            buy = buys[buy_index]
            sell = sells[sell_index]
            
            quantity = min(buy.stock_quantity, sell.stock_quantity)
            profit = (sell.stock_price - buy.stock_price) * quantity - sell.transaction_cost - buy.transaction_cost
            
            realized_profits.append((stock_ticker, quantity, profit, buy.currency))
            
            buys[buy_index].stock_quantity -= quantity
            sells[sell_index].stock_quantity -= quantity
            
            if buys[buy_index].stock_quantity == 0:
                buy_index += 1
            if sells[sell_index].stock_quantity == 0:
                sell_index += 1

    return render_template('transactions.html', portfolios=portfolios, transactions=transactions, selected_portfolio_ids=selected_portfolio_ids, positions=positions, realized_profits=realized_profits, current_prices=current_prices, unrealized_profits=unrealized_profits)


@transactions_bp.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user' not in session:
        flash('You need to be logged in to add a transaction.')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        flash('User not found.')
        return redirect(url_for('login'))
    
    portfolio_id = request.form['portfolio_id']
    date = request.form['date']
    stock_ticker = request.form['stock_ticker']
    stock_price = float(request.form['stock_price'])
    transaction_type = request.form['transaction_type']
    transaction_cost = float(request.form['transaction_cost'])
    stock_quantity = float(request.form['stock_quantity'])
    currency = request.form['currency']
    
    total_transaction_cost = stock_price * stock_quantity + transaction_cost
    
    new_transaction = Transaction(
        user_id=user.id,
        portfolio_id=portfolio_id,
        date=date,
        stock_ticker=stock_ticker,
        stock_price=stock_price,
        transaction_type=transaction_type,
        transaction_cost=transaction_cost,
        stock_quantity=stock_quantity,
        total_transaction_cost=total_transaction_cost,
        currency=currency
    )
    
    db.session.add(new_transaction)
    db.session.commit()
    
    flash('Transaction added successfully.')
    return redirect(url_for('transactions.transactions'))

@transactions_bp.route('/create_portfolio', methods=['GET', 'POST'])
def create_portfolio():
    if 'user' not in session:
        flash('You need to be logged in to create a portfolio.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        portfolio_name = request.form['portfolio_name']
        user = User.query.filter_by(username=session['user']).first()
        
        if user:
            new_portfolio = Portfolio(name=portfolio_name, user_id=user.id)
            db.session.add(new_portfolio)
            db.session.commit()
            flash('Portfolio created successfully.')
        else:
            flash('User not found.')
    
    return redirect(url_for('transactions.transactions'))