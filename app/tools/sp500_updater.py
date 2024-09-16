import pandas as pd
import sqlite3

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

print("S&P 500 tickers have been successfully updated in the database.")