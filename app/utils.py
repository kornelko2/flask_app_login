from datetime import datetime, timedelta
from flask import session
from app.models import User
from datetime import timedelta
import numpy as np

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

def calculate_average_correlation(correlation_matrix):
    # Flatten the matrix and exclude NaN values
    valid_correlations = correlation_matrix.values.flatten()
    valid_correlations = valid_correlations[~np.isnan(valid_correlations)]
    # Calculate the average
    if len(valid_correlations) == 0:
        return 0
    return np.mean(valid_correlations)

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