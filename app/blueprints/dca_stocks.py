from flask import Blueprint, render_template, request, flash, send_file, redirect, url_for, json, make_response
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
import io
import ast

dca_stocks_bp = Blueprint('dca_stocks', __name__)

@dca_stocks_bp.route('/dca_stocks', methods=['GET', 'POST'])
def dca_stocks():
    if request.method == 'POST':
        try:
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            stocks = request.form.getlist('stocks')
            investment_amount = float(request.form['investment_amount'])
            frequency = request.form['frequency']
        except (ValueError, KeyError):
            flash("All input fields are required and must be valid.")
            return render_template('dca_stocks.html')

        if not stocks or len(stocks) < 1 or len(stocks) > 12:
            flash("Please select between 1 and 12 stocks.")
            return render_template('dca_stocks.html')

        try:
            total_investment, final_amount, values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates = calculate_dca_stocks(
                start_date, end_date, stocks, investment_amount, frequency
            )
        except Exception as e:
            flash(f"Error fetching stock data: {e}")
            return render_template('dca_stocks.html')

        plot_json = generate_plot(values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates)

        return render_template('dca_stocks.html', total_investment=total_investment, final_amount=final_amount, 
                               plot_json=plot_json, start_date=start_date, end_date=end_date, 
                               stocks=stocks, investment_amount=investment_amount, frequency=frequency,
                               weeks=list(range(len(values))), contribution_dates=contribution_dates,
                               values=values, contributions=contributions, profit_percentages=profit_percentages,
                               purchased_stocks=purchased_stocks, total_stocks_owned=total_stocks_owned,
                               stock_prices_list=stock_prices_list)
    return render_template('dca_stocks.html')

@dca_stocks_bp.route('/export_table', methods=['POST'])
def export_table():
    if request.method == 'POST':
        try:
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            stocks = request.form.getlist('stocks')
            investment_amount = float(request.form['investment_amount'])
            frequency = request.form['frequency']
        except (ValueError, KeyError):
            flash("All input fields are required and must be valid.")
            return redirect(url_for('dca_stocks.dca_stocks'))

        try:
            total_investment, final_amount, values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates = calculate_dca_stocks(
                start_date, end_date, stocks, investment_amount, frequency
            )
        except Exception as e:
            flash(f"Error fetching stock data: {e}")
            return redirect(url_for('dca_stocks.dca_stocks'))

        _, _, df = generate_table_data(values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='DCA Data')
            writer.save()
        output.seek(0)

    return send_file(output, attachment_filename='dca_data.xlsx', as_attachment=True)

def calculate_dca_stocks(start_date, end_date, stocks, investment_amount, frequency):
    frequency_map = {
        'monthly': 1,
        'quarterly': 3

    }
    interval_map = {
        'monthly': '1mo',
        'quarterly': '3mo'
    }
    interval = interval_map[frequency]
    # periods_per_interval = frequency_map[frequency] // 3 if frequency in ['semiannually', 'annually'] else 1
    
    total_investment = 0
    portfolio = {stock: 0 for stock in stocks}
    values = []
    contributions = []
    profit_percentages = []
    purchased_stocks = {stock: [] for stock in stocks}
    total_stocks_owned = {stock: [] for stock in stocks}
    stock_prices_list = {stock: [] for stock in stocks}
    contribution_dates = []

    current_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    while current_date < end_date:
        next_date = current_date + pd.DateOffset(months=3)
        if next_date > end_date:
            next_date = end_date
        
        stock_data = yf.download(stocks, start=current_date, end=next_date, interval=interval)
        stock_prices = stock_data['Adj Close']
        
        # Interpolate missing data
        stock_prices = stock_prices.interpolate(method='linear', limit_direction='forward', axis=0)
        
        for date, prices in stock_prices.iterrows():
            if prices.isnull().any():
                continue  # Skip dates with missing data after interpolation
            
            total_investment += investment_amount
            investment_per_stock = investment_amount / len(stocks)
            
            for stock in stocks:
                shares_purchased = investment_per_stock / prices[stock]
                portfolio[stock] += shares_purchased
                purchased_stocks[stock].append(round(shares_purchased, 4))
                total_stocks_owned[stock].append(round(portfolio[stock], 4))
                stock_prices_list[stock].append(round(prices[stock], 2))
            
            total_value = sum(portfolio[stock] * prices[stock] for stock in stocks)
            values.append(total_value)
            contributions.append(total_investment)
            profit_percentage = ((total_value - total_investment) / total_investment) * 100
            profit_percentages.append(round(profit_percentage, 2))
            contribution_dates.append(date.strftime('%Y-%m-%d'))
        
        current_date = next_date

    return total_investment, total_value, values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates

def generate_plot(values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates):
    weeks = list(range(len(values)))
    
    # Create a subplot layout with 2 rows
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.45, 0.45],  # Adjust the heights of the rows
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Dollar Cost Averaging (DCA) Portfolio Value Over Time", "DCA Data Table"),
        specs=[[{"secondary_y": True}], [{"type": "table"}]]  # Specify subplot types and secondary y-axis
    )
    
    # Add the line chart to the first row
    fig.add_trace(go.Scatter(
        x=weeks, y=values, mode='lines', name='Account Status',
        hovertemplate='Week: %{x}<br>Account Status: $%{y:.0f}<extra></extra>'
    ), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(
        x=weeks, y=contributions, mode='lines', name='Contributions',
        hovertemplate='Week: %{x}<br>Contributions: $%{y:.0f}<extra></extra>'
    ), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(
        x=weeks, y=profit_percentages, mode='lines', name='Profit Percentage',
        hovertemplate='Week: %{x}<br>Profit Percentage: %{y:.0f}%<extra></extra>'
    ), row=1, col=1, secondary_y=True)
    
    # Prepare data for the table
    table_header, table_cells, _ = generate_table_data(values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates)
    
    df = pd.DataFrame(table_header)
    # print(df)
    df2 = pd.DataFrame(table_cells)
    # print(df2.head())
    combined_df = pd.concat([df.T, df2.T], ignore_index=True)
    
    # Save the DataFrame to a CSV file
    combined_df.to_excel('./dca_data.xlsx', index=False, sheet_name='DCA Data')
    
    # print(combined_df.head())
  
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        combined_df.to_excel(writer, index=False, sheet_name='DCA Data')
        # writer.close()
    output.seek(0)
     
    # Add the table to the second row
    fig.add_trace(go.Table(
        header=dict(
            values=table_header,
            fill_color='lightgrey',
            line_color='black',
            align='left',
            font=dict(color='black', size=12)
        ),
        cells=dict(
            values=table_cells,
            fill_color='white',
            line_color='black',
            align='left',
            font=dict(color='black', size=12)
        )
    ), row=2, col=1)
    
    # Update layout with size
    fig.update_layout(
        template='plotly_white',
        hovermode='x',  # Unified hover label
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Rockwell"
        ),
        yaxis=dict(
            title='Value ($)',
            side='left'
        ),
        yaxis2=dict(
            title='Profit Percentage (%)',
            side='right'
        ),
        width=1000,  # Set the width of the plot
        height=800   # Set the height of the plot
    )
    
    plot_json = pio.to_json(fig)
    return plot_json

def generate_table_data(values, contributions, profit_percentages, purchased_stocks, total_stocks_owned, stock_prices_list, contribution_dates):
    weeks = list(range(len(values)))
    
    table_header = ['Week', 'Contribution Date', 'Account Status', 'Contributions', 'Profit Percentage']
    table_cells = [weeks, contribution_dates, values, contributions, profit_percentages]
    
    for stock in purchased_stocks.keys():
        table_header.append(f'{stock} Purchased')
        table_cells.append(purchased_stocks[stock])
        table_header.append(f'{stock} Total Owned')
        table_cells.append(total_stocks_owned[stock])
        table_header.append(f'{stock} Price')
        table_cells.append(stock_prices_list[stock])
    
    # Create a DataFrame from the table header and table cells
    data = {header: cells for header, cells in zip(table_header, table_cells)}
    df = pd.DataFrame(data)
    
    return table_header, table_cells, df