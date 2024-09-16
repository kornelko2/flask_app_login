import yfinance as yf
import pandas as pd
import sqlite3

# List of S&P 500 tickers (for demonstration purposes, a few tickers are used)
# Load the tickers from the SP500 database
conn = sqlite3.connect('sp500.db')
cursor = conn.cursor()

# Retrieve the tickers from the database
cursor.execute('SELECT DISTINCT ticker FROM sp500_tickers')
sp500_tickers = [row[0] for row in cursor.fetchall()]

# Close the connection
conn.close()
print(sp500_tickers)
# Define the date range
start_date = '2000-01-01'
end_date = '2024-09-01'

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('sp500_historical_data.db')
cursor = conn.cursor()

# Create the table for storing historical data if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS historical_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        date TEXT NOT NULL,
        close REAL NOT NULL
    )
''')

# Download historical data for each ticker
for ticker in sp500_tickers:
    print(f"Downloading data for {ticker}...")
    data = yf.download(ticker, start=start_date, end=end_date, interval='1wk')
    data.reset_index(inplace=True)
    
    # Insert data into the database
    for index, row in data.iterrows():
        cursor.execute('''
            INSERT INTO historical_prices (ticker, date, close)
            VALUES (?, ?, ?)
        ''', (ticker, row['Date'].strftime('%Y-%m-%d'), row['Close']))

# Commit the transaction and close the connection
conn.commit()
conn.close()

print("Historical data has been successfully downloaded and stored in the database.")