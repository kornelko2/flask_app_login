from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
# app.secret_key = '182iETyh9V5KZ_fo'

# Configure logging
# logging.basicConfig(level=logging.DEBUG)

# Initialize the database
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT UNIQUE NOT NULL,
                         password TEXT NOT NULL,
                         status TEXT DEFAULT 'active',
                         is_admin INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT NOT NULL,
                         date TEXT NOT NULL,
                         stock_ticker TEXT NOT NULL,
                         stock_price REAL NOT NULL,
                         transaction_type TEXT NOT NULL,
                         transaction_cost REAL NOT NULL,
                         stock_quantity REAL NOT NULL,
                         total_transaction_cost REAL,
                         currency TEXT,
                         FOREIGN KEY (username) REFERENCES users (username))''')  # Added FOREIGN KEY constraint

@app.before_request
def initialize():
    init_db()

def is_admin():
    if 'user' in session:
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_admin FROM users WHERE username = ?', (session['user'],))
            user = cursor.fetchone()
            return user and user[0] == 1
    return False

def user_is_admin(username):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        return user and user[0] == 1

app.jinja_env.globals.update(user_is_admin=user_is_admin)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[2], password):
                session['user'] = username
                if user[3] == 'locked':
                    flash('Your account is locked.')
                    session.pop('user', None)
                    return redirect(url_for('login'))
                return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        is_admin = 1 if 'is_admin' in request.form else 0
        try:
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', (username, password, is_admin))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return 'Username already exists'
    return render_template('register.html')

@app.route('/users')
def users_page():
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, status, is_admin FROM users')
        users = cursor.fetchall()
    return render_template('admin/users.html', users=users)

@app.route('/lock_user/<int:user_id>', methods=['POST'])
def lock_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    new_status = 'locked' if request.form.get('locked') == 'on' else 'active'
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
    return redirect(url_for('users_page'))

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    new_is_admin = 1 if request.form.get('is_admin') == 'on' else 0
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_is_admin, user_id))
        conn.commit()
    return redirect(url_for('users_page'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    return redirect(url_for('users_page'))

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

        # Connect to the SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect('sp500.db')
        cursor = conn.cursor()

        # Create the table for storing S&P 500 tickers if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sp500_tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                company_name TEXT NOT NULL
            )
        ''')

        # Delete existing data from the table
        cursor.execute('DELETE FROM sp500_tickers')

        # Insert the tickers into the database
        for index, row in tickers.iterrows():
            cursor.execute('''
                INSERT INTO sp500_tickers (ticker, company_name)
                VALUES (?, ?)
            ''', (row['Symbol'], row['Security']))

        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'message': 'S&P 500 tickers have been successfully updated.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/transactions', methods=['GET', 'POST'])
def transactions():
    if 'user' not in session:
        flash('You need to be logged in to view this page.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = session['user']
        date = request.form['date']
        stock_ticker = request.form['stock_ticker'].upper()
        stock_price = float(request.form['stock_price'])
        transaction_type = request.form['transaction_type']
        transaction_cost = float(request.form['transaction_cost'])
        stock_quantity = float(request.form['stock_quantity'])
        currency = request.form['currency'].upper()  # Get the currency
        total_transaction_cost = stock_price * stock_quantity + transaction_cost  # Calculate total transaction cost
        
        # Validate stock ticker against sp500.db
        try:
            with sqlite3.connect('sp500.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ticker FROM sp500_tickers WHERE ticker = ?', (stock_ticker,))
                result = cursor.fetchone()
                if result is None:
                    flash('Invalid stock ticker. Please enter a valid S&P 500 stock ticker.')
                    return redirect(url_for('transactions'))
        except sqlite3.Error as e:
            flash(f'Error validating stock ticker: {e}')
            return redirect(url_for('transactions'))
        
        # Insert transaction into users.db
        try:
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO transactions (username, date, stock_ticker, stock_price, transaction_type, transaction_cost, stock_quantity, total_transaction_cost, currency)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (username, date, stock_ticker, stock_price, transaction_type, transaction_cost, stock_quantity, total_transaction_cost, currency))
                conn.commit()
                flash('Transaction added successfully.')
        except sqlite3.Error as e:
            flash(f'Error adding transaction to the database: {e}')
            return redirect(url_for('transactions'))
        
        return redirect(url_for('transactions'))
    
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE username = ?', (session['user'],))
        transactions = cursor.fetchall()
        
        
        cursor.execute('''SELECT stock_ticker, 
                                 SUM(CASE WHEN transaction_type = 'buy' THEN stock_quantity ELSE -stock_quantity END) AS position_size,
                                 SUM(CASE WHEN transaction_type = 'buy' THEN total_transaction_cost ELSE -total_transaction_cost END) AS total_cost,
                                 AVG(stock_price) AS avg_price,
                                 currency
                          FROM transactions
                          WHERE username = ?
                          GROUP BY stock_ticker, currency
                          HAVING position_size != 0''', (session['user'],))
        positions = cursor.fetchall()
        
    
    # Fetch current prices using yfinance
    current_prices = {}
    for position in positions:
        stock_ticker = position[0]
        stock_info = yf.Ticker(stock_ticker)
        try:
            current_price = stock_info.history(period='1d')['Close'].iloc[0]
            current_prices[stock_ticker] = current_price
            
        except Exception as e:
            current_prices[stock_ticker] = None
            flash(f'Error fetching current price for {stock_ticker}: {e}')
            
    
    # Calculate unrealized profits
    unrealized_profits = {}
    for position in positions:
        stock_ticker = position[0]
        avg_price = position[3]
        current_price = current_prices[stock_ticker]
        if current_price is not None:
            quantity = position[1]
            unrealized_profit = (current_price - avg_price) * quantity
            unrealized_profits[stock_ticker] = unrealized_profit
        else:
            unrealized_profits[stock_ticker] = None
    
    # Calculate realized profits
    realized_profits = []
    for stock_ticker in set([t[3] for t in transactions]):
        buys = [t for t in transactions if t[3] == stock_ticker and t[5] == 'buy']
        sells = [t for t in transactions if t[3] == stock_ticker and t[5] == 'sell']
        
        buy_index = 0
        sell_index = 0
        while buy_index < len(buys) and sell_index < len(sells):
            buy = buys[buy_index]
            sell = sells[sell_index]
            
            quantity = min(buy[7], sell[7])
            profit = (sell[4] - buy[4]) * quantity - sell[6] - buy[6]
            
            realized_profits.append((stock_ticker, quantity, profit, buy[9]))
            
            
            buys[buy_index] = (buy[0], buy[1], buy[2], buy[3], buy[4], buy[5], buy[6], buy[7] - quantity, buy[8], buy[9])
            sells[sell_index] = (sell[0], sell[1], sell[2], sell[3], sell[4], sell[5], sell[6], sell[7] - quantity, sell[8], sell[9])
            
            if buys[buy_index][7] == 0:
                buy_index += 1
            if sells[sell_index][7] == 0:
                sell_index += 1
    
    return render_template('transactions.html', transactions=transactions, positions=positions, current_prices=current_prices, unrealized_profits=unrealized_profits, realized_profits=realized_profits)


@app.route('/admin/edit_transactions', methods=['GET', 'POST'])
def edit_transactions():
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        transaction_id = request.form['transaction_id']
        date = request.form['date']
        stock_ticker = request.form['stock_ticker'].upper()
        stock_price = float(request.form['stock_price'])
        transaction_type = request.form['transaction_type']
        transaction_cost = float(request.form['transaction_cost'])
        stock_quantity = int(request.form['stock_quantity'])
        
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''UPDATE transactions
                              SET date = ?, stock_ticker = ?, stock_price = ?, transaction_type = ?, transaction_cost = ?, stock_quantity = ?
                              WHERE id = ?''', (date, stock_ticker, stock_price, transaction_type, transaction_cost, stock_quantity, transaction_id))
            conn.commit()
        flash('Transaction updated successfully.')
        return redirect(url_for('edit_transactions'))
    
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions')
        transactions = cursor.fetchall()
    
    return render_template('admin/edit_transactions.html', transactions=transactions)


if __name__ == '__main__':
    app.run(debug=True)