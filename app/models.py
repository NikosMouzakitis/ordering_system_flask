from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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

