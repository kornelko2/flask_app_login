from flask import Blueprint, render_template, session, request, redirect, url_for
from app.models import Portfolio, Transaction, User
from app.utils import get_time_delta, calculate_average_correlation
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
from datetime import datetime
from app.db_extension import db 

correlation_bp = Blueprint('correlation', __name__)

@correlation_bp.route('/correlation', methods=['GET', 'POST'])
def correlation():
    username = session.get('user')  # Get the logged-in user's username
    if not username:
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('auth.login'))
    
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