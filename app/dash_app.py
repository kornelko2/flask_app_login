from dash import Dash, dash_table, html, Input, Output, State, callback_context
from flask import Flask, session
from datetime import datetime
from app.models import db, Todo, User  # Import the db instance, Todo model, and User model

def fetch_up_to_date_data_from_db(server):
    with server.app_context():
        # Fetch data from the database
        todos = db.session.query(Todo, User).join(User, Todo.user_id == User.id).all()
        data = [
            {
                'id': todo.id,
                'title': todo.title,
                'status': todo.status,
                'description': todo.description,
                'version': todo.version,
                'creation_date': todo.creation_date.strftime('%Y-%m-%d %H:%M'),
                'done_date': todo.done_date.strftime('%Y-%m-%d %H:%M') if todo.done_date else '',
                'username': user.username
            } for todo, user in todos
        ]
    return data

def init_dash(server):
    app = Dash(__name__, server=server, url_base_pathname='/dash/')

    # Create the data table layout
    app.layout = html.Div([
        dash_table.DataTable(
            id='todo-table',
            columns=[
                {'name': 'ID', 'id': 'id', 'editable': False, 'hidden': True},
                {'name': 'Title', 'id': 'title', 'editable': True},
                {'name': 'Status', 'id': 'status', 'editable': True, 'presentation': 'dropdown'},
                {'name': 'Description', 'id': 'description', 'editable': True},
                {'name': 'Version', 'id': 'version', 'editable': True},
                {'name': 'Creation Date', 'id': 'creation_date', 'editable': False},
                {'name': 'Done Date', 'id': 'done_date', 'editable': False},
                {'name': 'Username', 'id': 'username', 'editable': False}
            ],
            data=fetch_up_to_date_data_from_db(server),
            editable=True,
            row_deletable=False,
            dropdown={
                'status': {
                    'options': [
                        {'label': 'Idea Only', 'value': 'Idea Only'},
                        {'label': 'Not Started', 'value': 'Not Started'},
                        {'label': 'In Progress', 'value': 'In Progress'},
                        {'label': 'Completed', 'value': 'Completed'}
                    ]
                }
            },
            style_cell={
                'fontFamily': 'Arial, sans-serif',  # Set the font family
                'fontSize': '14px',  # Set the font size
                'textAlign': 'left'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{status} = "Completed"'},
                    'backgroundColor': '#d3d3d3'
                }
            ]
        ),
        html.Button('Create New Line', id='create-button', n_clicks=0),
        html.Button('Refresh Data', id='refresh-button', n_clicks=0)  # Add refresh button
    ])

    @app.callback(
        Output('todo-table', 'data'),
        [Input('todo-table', 'data_timestamp'),
         Input('create-button', 'n_clicks'),
         Input('refresh-button', 'n_clicks')],  # Add refresh button input
        [State('todo-table', 'data')]
    )
    def update_database(timestamp, create_clicks, refresh_clicks, rows):
        ctx = callback_context

        if not ctx.triggered:
            return rows

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'create-button':
            with server.app_context():
                username = session.get('user')
                if not username:
                    print("No user found in session")
                    return rows
                user = User.query.filter_by(username=username).first()
                if not user:
                    print("No user found in database")
                    return rows
                new_todo = Todo(
                    title='New Task',
                    status='Not Started',
                    description='',
                    version='',
                    creation_date=datetime.now(),
                    user_id=user.id
                )
                db.session.add(new_todo)
                db.session.commit()

        elif button_id == 'refresh-button':
            return fetch_up_to_date_data_from_db(server)

        else:
            with server.app_context():
                for row in rows:
                    todo = Todo.query.get(row['id'])
                    if todo:
                        todo.title = row['title']
                        todo.status = row['status']
                        todo.description = row['description']
                        todo.version = row['version']
                        if row['status'] == 'Completed' and not todo.done_date:
                            todo.done_date = datetime.now()
                            row['done_date'] = todo.done_date.strftime('%Y-%m-%d %H:%M')
                        db.session.commit()

        return fetch_up_to_date_data_from_db(server)

    return app

# Example of how to initialize the Dash app with a Flask server
if __name__ == '__main__':
    server = Flask(__name__)
    app = init_dash(server)
    server.run(debug=True)