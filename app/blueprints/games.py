from flask import Blueprint, render_template, request, jsonify
import subprocess
import json

games_bp = Blueprint('games', __name__)

@games_bp.route('/tetris')
def tetris():
    return render_template('games/tetris/index.html')

@games_bp.route('/start_tetris', methods=['POST'])
def start_tetris():
    try:
        data = json.loads(request.data)
        game_speed = data.get('gameSpeed', 500)  # Default to normal speed if not provided
        subprocess.Popen(['python', 'tools/tetris_game.py', str(game_speed)])
        return jsonify({'status': 'success', 'message': 'Tetris game started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@games_bp.route('/tic_tac_toe')
def tic_tac_toe():
    return render_template('games/tic-tac-toe/index.html')

@games_bp.route('/start_tic_tac_toe', methods=['POST'])
def start_tic_tac_toe():
    try:
        subprocess.Popen(['python', 'tools/tic_tac_toe_game.py'])
        return jsonify({'status': 'success', 'message': 'Tic-Tac-Toe game started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})