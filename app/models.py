from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
TABLES_NU = 20

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(20), default="Available")  # Available, Occupied, Reserved

def init_tables(app):
    with app.app_context():
        db.create_all()
        if Table.query.count() == 0:  # Initialize tables only once
            for i in range(1, TABLES_NU + 1):
                db.session.add(Table(number=i))
            db.session.commit()

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'Food' or 'Drink'
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<MenuItem {self.name} - {self.category} - ${self.price:.2f}>'

def init_menu_items(app):
    with app.app_context():
        existing_items = {item.name: item for item in MenuItem.query.all()}  # Fetch existing items

        items = [
            MenuItem(name='Burger', category='Food', price=10.99),
            MenuItem(name='Pizza', category='Food', price=12.99),
            MenuItem(name='Salad', category='Food', price=7.99),
            MenuItem(name='Soda', category='Drink', price=1.99),
            MenuItem(name='Water', category='Drink', price=0.99),
            MenuItem(name='Coffee', category='Drink', price=2.99),
        ]

        for item in items:
            if item.name not in existing_items:  # Check if the item already exists
                db.session.add(item)  # Add each item individually
        db.session.commit()



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="open")  # 'open' or 'closed'
    items = db.relationship('OrderItem', backref='order', lazy=True)

    def __repr__(self):
        return f'<Order {self.id} for Table {self.table_id} - Status: {self.status}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)

    menu_item = db.relationship('MenuItem', backref='order_items')


# User model for authentication and roles


from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # Add this line

    def __repr__(self):
        return f"<User {self.username}>"

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # These methods are required by Flask-Login
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return self.is_active
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)


# Initialize admin and waiter accounts
def init_users(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', is_active=True)
            admin.set_password('admin_password')
            db.session.add(admin)

        waiter1 = User.query.filter_by(username='waiter1').first()
        if not waiter1:
            waiter1 = User(username='waiter1', role='waiter', is_active=True)
            waiter1.set_password('waiter_password1')
            db.session.add(waiter1)

        waiter2 = User.query.filter_by(username='waiter2').first()
        if not waiter2:
            waiter2 = User(username='waiter2', role='waiter', is_active=True)
            waiter2.set_password('waiter_password2')
            db.session.add(waiter2)

        db.session.commit()







class KitchenOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    items = db.relationship('KitchenOrderItem', backref='order', lazy=True)

class KitchenOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('kitchen_order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
