from flask import Blueprint, render_template, redirect, url_for, request, session, flash, jsonify
from app.models import User, SP500Ticker
from app.db_extension import db
import pandas as pd

admin_bp = Blueprint('admin', __name__)

def is_admin():
    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()
        return user and user.is_admin == 1
    return False

@admin_bp.route('/lock_user/<int:user_id>', methods=['POST'])
def lock_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('main.home'))
    new_status = 'locked' if request.form.get('locked') == 'on' else 'active'
    user = User.query.get(user_id)
    if user:
        user.status = new_status
        db.session.commit()
    return redirect(url_for('admin.users_page'))

@admin_bp.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('main.home'))
    new_is_admin = 1 if request.form.get('is_admin') == 'on' else 0
    user = User.query.get(user_id)
    if user:
        user.is_admin = new_is_admin
        db.session.commit()
    return redirect(url_for('admin.users_page'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('main.home'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin.users_page'))

@admin_bp.route('/users')
def users_page():
    if not is_admin():
        flash('Access denied.')
        return redirect(url_for('main.home'))
    users = User.query.with_entities(User.id, User.username, User.status, User.is_admin).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/update_sp500', methods=['POST'])
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