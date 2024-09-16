from flask import Blueprint, render_template, current_app

todo_bp = Blueprint('todo', __name__)

@todo_bp.route('/todo')
def todo():
        return render_template('todos.html')