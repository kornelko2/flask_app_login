from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
import os
import subprocess
import logging
import json
from db_extension import db  # Import db from db_extension
from models import User, Transaction, SP500Ticker, Portfolio  # Import models after db
from datetime import datetime, timedelta
import plotly.express as px
import plotly.io as pio
import numpy as np

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  # Initialize db with the app




# Configure logging
# logging.basicConfig(level=logging.DEBUG)

@app.before_request
def init_db():
    db.create_all()
    
def is_admin():
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        return user and user.is_admin == 1
    return False

def user_is_admin(username):
    user = User.query.filter_by(username=username).first()
    return user and user.is_admin == 1

def get_time_delta(period):
    if period == '1y':
        return timedelta(days=365)
    elif period == '3y':
        return timedelta(days=3*365)
    elif period == '5y':
        return timedelta(days=5*365)
    elif period == '10y':
        return timedelta(days=10*365)
    else:
        return None

app.jinja_env.globals.update(user_is_admin=user_is_admin)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            if user.status == 'locked':
                flash('Your account is locked.')
                return redirect(url_for('login'))
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    users_exist = User.query.first() is not None
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        is_admin = 1 if 'is_admin' in request.form else 0
        status = 'active' if not users_exist else 'locked'
        try:
            new_user = User(username=username, password=password, is_admin=is_admin, status=status)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                return 'Username already exists'
            else:
                return 'An error occurred'
    return render_template('register.html', users_exist=users_exist)

@app.route('/correlation', methods=['GET', 'POST'])
def correlation():
    username = session.get('user')  # Get the logged-in user's username
    if not username:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('login'))
    
    portfolios = Portfolio.query.filter_by(user_id=user.id).all()
    
    # Set default portfolio and time period
    if portfolios:
        default_portfolio_id = min(portfolios, key=lambda p: p.id).id
    else:
        default_portfolio_id = None
    default_time_period = '1y'
    
    selected_portfolio_id = request.form.get('portfolio_id', default_portfolio_id)
    selected_time_period = request.form.get('time_period', default_time_period)
    active_positions_only = request.form.get('active_positions_only') == 'on'
    
    if selected_portfolio_id:
        transactions = Transaction.query.filter_by(portfolio_id=selected_portfolio_id).all()
        selected_portfolio = db.session.get(Portfolio, selected_portfolio_id)
    else:
        transactions = Transaction.query.filter(Transaction.portfolio_id.in_([p.id for p in portfolios])).all()
        selected_portfolio = None
    
    # Filter transactions based on the selected time period
    cutoff_date = None
    if selected_time_period:
        time_delta = get_time_delta(selected_time_period)
        if time_delta:
            cutoff_date = datetime.now() - time_delta
            transactions = [t for t in transactions if datetime.strptime(t.date, '%Y-%m-%d') >= cutoff_date]
    
    # Calculate active positions
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
        positions_dict[stock_ticker][2] = round(positions_dict[stock_ticker][1] / positions_dict[stock_ticker][0], 2) if positions_dict[stock_ticker][0] != 0 else 0
    # Filter active positions where total cost is not zero
    active_positions = {ticker: data for ticker, data in positions_dict.items() if data[1] != 0}
    
    # Apply filtering based on the checkbox
    if active_positions_only:
        transactions = [t for t in transactions if t.stock_ticker in active_positions and positions_dict[t.stock_ticker][0] != 0]
    else:
        transactions = [t for t in transactions if t.stock_ticker in active_positions]
    
    # Fetch close price data from yfinance
    if transactions:
        stock_tickers = list(set(t.stock_ticker for t in transactions))
        interval = '1d'
        if cutoff_date:
            data = yf.download(stock_tickers, start=cutoff_date.strftime('%Y-%m-%d'), interval=interval)
        else:
            data = yf.download(stock_tickers, interval=interval)

        if 'Close' in data:
            close_prices = data['Close']
            
            # Ensure close_prices is a DataFrame
            if isinstance(close_prices, pd.Series):
                close_prices = close_prices.to_frame()
            
            # Check for missing data and align the data
            close_prices = close_prices.dropna(how='all')
            if close_prices.empty:
                correlation_matrix = None
                heatmapJSON = None
                linePlotJSON = None
            elif len(close_prices) < 30:
                correlation_matrix = None
                heatmapJSON = None
                linePlotJSON = None
            else:
                # Calculate correlation using Pearson method and round to 2 decimal places
                correlation_matrix = close_prices.corr(method='pearson').round(2)
                
                # Set the diagonal values to NaN to reduce self-correlation
                np.fill_diagonal(correlation_matrix.values, np.nan)
                
                # Mask the upper triangle of the correlation matrix
                mask = correlation_matrix.where(np.tril(np.ones(correlation_matrix.shape)).astype(bool))
                
                # Calculate average correlation index
                avg_correlation = calculate_average_correlation(correlation_matrix)
                
                # Generate Plotly heatmap
                fig_heatmap = px.imshow(mask, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
                fig_heatmap.update_layout(
                    title=f"Correlation Matrix for {selected_portfolio.name if selected_portfolio else 'All Portfolios'} over {selected_time_period} (Avg Correlation: {avg_correlation:.2f})",
                    template='plotly_white'
                )
                
                # Convert Plotly heatmap figure to JSON
                heatmapJSON = pio.to_json(fig_heatmap)
                
                # Generate Plotly line plot for stock price history
                fig_line = px.line(close_prices, title="Stock Price History", template='plotly_white')
                fig_line.update_layout(
                    title=f"Stock Price History for {selected_portfolio.name if selected_portfolio else 'All Portfolios'} over {selected_time_period}",
                    template='plotly_white'
                )
                
                # Convert Plotly line plot figure to JSON
                linePlotJSON = pio.to_json(fig_line)
                
                return render_template('correlation.html', portfolios=portfolios, graphJSON=heatmapJSON, linePlotJSON=linePlotJSON, selected_portfolio=selected_portfolio, selected_time_period=selected_time_period, active_positions=active_positions, active_positions_only=active_positions_only)
        else:
            correlation_matrix = None
            heatmapJSON = None
            linePlotJSON = None
    else:
        correlation_matrix = None
        heatmapJSON = None
        linePlotJSON = None

    return render_template('correlation.html', portfolios=portfolios, graphJSON=heatmapJSON, linePlotJSON=linePlotJSON, selected_portfolio=selected_portfolio, selected_time_period=selected_time_period, active_positions=active_positions, active_positions_only=active_positions_only)

def calculate_average_correlation(correlation_matrix):
    # Flatten the matrix and exclude NaN values
    valid_correlations = correlation_matrix.values.flatten()
    valid_correlations = valid_correlations[~np.isnan(valid_correlations)]
    # Calculate the average
    if len(valid_correlations) == 0:
        return 0
    return np.mean(valid_correlations)

@app.route('/lock_user/<int:user_id>', methods=['POST'])
def lock_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    new_status = 'locked' if request.form.get('locked') == 'on' else 'active'
    user = User.query.get(user_id)
    if user:
        user.status = new_status
        db.session.commit()
    return redirect(url_for('users_page'))

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    new_is_admin = 1 if request.form.get('is_admin') == 'on' else 0
    user = User.query.get(user_id)
    if user:
        user.is_admin = new_is_admin
        db.session.commit()
    return redirect(url_for('users_page'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('users_page'))

@app.route('/users')
def users_page():
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    users = User.query.with_entities(User.id, User.username, User.status, User.is_admin).all()
    return render_template('admin/users.html', users=users)

@app.route('/update_sp500', methods=['POST'])
def update_sp500():
    try:
        # URL of the Wikipedia page containing the list of S&P 500 companies
        wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        # Read the table from the Wikipedia page
        tables = pd.read_html(wiki_url)
        sp500_table = tables[0]  # The first table contains the S&P 500 companies

        # Extract the ticker symbols and company names
        tickers = sp500_table[['Symbol', 'Security']]

        # Delete existing data from the table
        SP500Ticker.query.delete()

        # Insert the tickers into the database
        for index, row in tickers.iterrows():
            new_ticker = SP500Ticker(ticker=row['Symbol'], company_name=row['Security'])
            db.session.add(new_ticker)

        # Commit the transaction
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'S&P 500 tickers have been successfully updated.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/transactions', methods=['GET', 'POST'])
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


@app.route('/add_transaction', methods=['POST'])
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
    return redirect(url_for('transactions'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/tetris')
def tetris():
    return render_template('games/tetris/index.html')

@app.route('/start_tetris', methods=['POST'])
def start_tetris():
    logging.debug('start_tetris route triggered')
    try:
        data = json.loads(request.data)
        game_speed = data.get('gameSpeed', 500)  # Default to normal speed if not provided
        subprocess.Popen(['python', 'tools/tetris_game.py', str(game_speed)])
        logging.debug('Tetris game started successfully with speed: %d', game_speed)
    except Exception as e:
        logging.error(f'Failed to start Tetris game: {e}')
    return jsonify(success=True)

@app.route('/tic_tac_toe')
def tic_tac_toe():
    return render_template('games/tic-tac-toe/index.html')

@app.route('/create_portfolio', methods=['GET', 'POST'])
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
    
    return redirect(url_for('transactions'))

if __name__ == '__main__':
    app.run(debug=True)