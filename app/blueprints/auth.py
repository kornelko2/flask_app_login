from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app.db_extension import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            if user.status == 'locked':
                flash('Your account is locked.')
                return redirect(url_for('auth.login'))
            return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                return 'Username already exists'
            else:
                return 'An error occurred'
    return render_template('register.html', users_exist=users_exist)

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))