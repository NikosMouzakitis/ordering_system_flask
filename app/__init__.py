from flask import Flask
from flask_socketio import SocketIO
from .models import db, init_tables, init_menu_items

socketio = SocketIO()

def create_app():
    app = Flask(__name__,static_folder='static')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
    app.config['SECRET_KEY'] = 'your_secret_key'

    db.init_app(app)
    socketio.init_app(app)

    with app.app_context():
        init_tables(app)
        init_menu_items(app)

    from app.routes import main
    app.register_blueprint(main)

    return app

