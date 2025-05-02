from flask import Flask
from flask_socketio import SocketIO
from datetime import timedelta
from flask_login import LoginManager
from .models import db, init_tables, init_menu_items, init_users, User  # Add init_users here
from .auth import auth
from flask_cors import CORS

socketio = SocketIO(cors_allowed_origins="*")

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, static_folder='static')
    CORS(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
    app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this!
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        db.create_all()  # Create all tables first
        init_tables(app)
        init_menu_items(app)
        init_users(app)  # Add this line to create users

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
