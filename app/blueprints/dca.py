from flask import Blueprint, render_template, request, send_file, flash
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
import pandas as pd
import io

dca_bp = Blueprint('dca', __name__)

@dca_bp.route('/dca', methods=['GET', 'POST'])
def dca_calculator():
    frequency_map = {
        'monthly': 1,
        'quarterly': 3,
        'semiannually': 6,
        'annually': 12
    }

    if request.method == 'POST':
        try:
            initial_investment = float(request.form['initial_investment'])
            monthly_investment = float(request.form['monthly_investment'])
            annual_return = float(request.form['annual_return'])
            years = int(request.form['years'])
            contribution_frequency = request.form['contribution_frequency']
        except (ValueError, KeyError):
            flash("All input fields are required and must be valid numbers.")
            return render_template('dca.html', frequency_map=frequency_map)

        total_investment, final_amount, values, contributions, profit_percentages = calculate_dca(
            initial_investment, monthly_investment, annual_return, years, contribution_frequency
        )

        if not values or not contributions or not profit_percentages:
            flash("No data available for the given inputs.")
            return render_template('dca.html', frequency_map=frequency_map)

        plot_json = generate_plot(values, contributions, profit_percentages)

        # Create a DataFrame for the table values
        df = pd.DataFrame({
            'Week': list(range(len(values))),
            'Account Status': values,
            'Contributions': contributions,
            'Profit Percentage': profit_percentages
        })

        # Export to Excel
        if 'export' in request.form:
            if df.empty:
                flash("No data available to export.")
                return render_template('dca.html', frequency_map=frequency_map)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='DCA Data')
                writer.close()
            output.seek(0)
            return send_file(output, download_name='dca_data.xlsx', as_attachment=True)

        return render_template('dca.html', total_investment=total_investment, final_amount=final_amount, 
                               plot_json=plot_json, frequency_map=frequency_map, 
                               contribution_frequency=contribution_frequency, initial_investment=initial_investment, 
                               monthly_investment=monthly_investment, annual_return=annual_return, years=years)
    return render_template('dca.html', frequency_map=frequency_map)

def calculate_dca(initial_investment, monthly_investment, annual_return, years, contribution_frequency):
    monthly_return = (1 + annual_return / 100) ** (1 / 12) - 1
    total_investment = initial_investment
    final_amount = initial_investment

    values = [round(initial_investment, 2)]
    contributions = [round(initial_investment, 2)]
    profit_percentages = [0.0]

    frequency_map = {
        'monthly': 1,
        'quarterly': 3,
        'semiannually': 6,
        'annually': 12
    }
    contribution_interval = frequency_map[contribution_frequency]

    for month in range(1, years * 12 + 1):
        if month % contribution_interval == 0:
            final_amount = round((final_amount + monthly_investment) * (1 + monthly_return), 2)
            total_investment += monthly_investment
        else:
            final_amount *= round((1 + monthly_return), 2)
        values.append(round(final_amount, 2))
        contributions.append(round(total_investment, 2))
        profit_percentage = ((final_amount - total_investment) / total_investment) * 100
        profit_percentages.append(round(profit_percentage, 2))

    return total_investment, final_amount, values, contributions, profit_percentages

def generate_plot(values, contributions, profit_percentages):
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
    
    # Add the table to the second row
    fig.add_trace(go.Table(
        header=dict(
            values=['Week', 'Account Status', 'Contributions', 'Profit Percentage'],
            fill_color='lightgrey',
            line_color='black',
            align='left',
            font=dict(color='black', size=12)
        ),
        cells=dict(
            values=[weeks, values, contributions, profit_percentages],
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