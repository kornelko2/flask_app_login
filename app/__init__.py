from flask import Flask
from app.db_extension import db
from app.models import Todo  # Import the Todo model
from app.blueprints.auth import auth_bp
from app.blueprints.correlation import correlation_bp
from app.blueprints.games import games_bp
from app.blueprints.admin import admin_bp
from app.blueprints.main import main_bp
from app.blueprints.transactions import transactions_bp
from app.blueprints.todo import todo_bp
from app.utils import user_is_admin

__version__ = '0.0.8'

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(correlation_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(todo_bp)
    
    @app.context_processor
    def inject_user_is_admin():
        return dict(user_is_admin=user_is_admin)

    # Import and initialize the Dash app
    from app.dash_app import init_dash
    dash_app = init_dash(app)
    
    @app.context_processor
    def inject_version():
        return dict(version=__version__)

    return app