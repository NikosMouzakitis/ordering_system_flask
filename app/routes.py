from flask import Blueprint, jsonify, render_template, request
from .models import Table, MenuItem, Order, OrderItem
from . import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/tables', methods=['GET'])
def get_tables():
    tables = Table.query.all()
    return {"tables": [{"id": t.id, "number": t.number, "status": t.status} for t in tables]}

'''
@main.route('/menu', methods=['GET'])
def get_menu_items():
    menu_items = MenuItem.query.all()
    return {"menuItems": [{"id": item.id, "name": item.name, "price": item.price} for item in menu_items]}
'''
##get menu items grouped by category
@main.route('/menu', methods=['GET'])
def get_menu():
    menu_items = MenuItem.query.all()
    categories = {}
    
    for item in menu_items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append({
            "id": item.id,
            "name": item.name,
            "price": item.price
        })
    
    return jsonify(categories)

@main.route('/order', methods=['POST'])
def create_order():
    table_id = request.form.get('table_id')
    item_ids = request.form.getlist('items[]')
    print(f"TableID: {table_id}, Item IDs: {item_ids}")

    # Create the order
    new_order = Order(table_id=table_id)
    db.session.add(new_order)
    db.session.flush() # get new order's id for ordered items.

    # Link menu items to the order
    for item_id in item_ids:
        order_item = OrderItem(order_id=new_order.id, menu_item_id=item_id)
        print(f"adding Orderitem {new_order.id}, menu_item id: {item_id}")
        db.session.add(order_item)

    # Change the table status to "Occupied"
    table = Table.query.get(table_id)
    if table:
        table.status = "Occupied"
    
    try:
        db.session.commit()
        print("commited okay")
    except Exception as e:
        print(f"Error commiting: {e}")

    return jsonify({"status": "success", "order_id": new_order.id})

@main.route('/free_table', methods=['POST'])
def free_table():
    print("Free table pressed")
    table_id = request.form.get('table_id')
    payment_method = request.form.get('payment_method')

    # Fetch all open orders for this table
    orders = Order.query.filter_by(table_id=table_id, status='open').all()
    if orders:
        for order in orders:
            order.status = 'closed'  # Close each open order
        db.session.commit()

    # Update table status to "Available" if it was occupied
    table = Table.query.get(table_id)
    if table and table.status == 'Occupied':
        table.status = 'Available'
        db.session.commit()
        return jsonify({"message": f"Table {table_id} has been freed and is now available."}), 200
    
    return jsonify({"message": "Table not found or already available."}), 400

@main.route('/orders',methods=['GET'])
def view_orders():
    orders=Order.query.all()
    return render_template('orders.html',orders=orders)

@main.route('/current_orders')
def current_orders():
    open_orders = {}  # Dictionary to hold orders by table number
    open_tables = []  # List to hold table numbers with open orders

    # Fetch open orders
    orders = Order.query.filter_by(status='open').all()
    for order in orders:
        table_id = order.table_id
        if table_id not in open_orders:
            open_orders[table_id] = []  # Initialize list for this table
            open_tables.append(table_id)  # Add to the list of open tables
        open_orders[table_id].append(order)  # Append the order to the table's orders

    return render_template('current_orders.html', open_tables=open_tables, open_orders=open_orders)

## hovering on table
@main.route('/get_orders/<int:table_id>')
def get_orders(table_id):
    print(f"hover occurs for table: {table_id} ")
    orders = Order.query.filter_by(table_id=table_id, status='open').all()
    order_items = []
    print(orders)

    for order in orders:
        for item in order.items:
            print("order items: ")
            print(item)
            order_item_id = item.menu_item_id
            print(order_item_id)

            # Fetch the menu item by ID
            menu_item = MenuItem.query.filter_by(id=order_item_id).first()  # Use .first() to get the actual object

            if menu_item:  # Check if the menu item exists
                order_items.append(menu_item.name)  # Append the name of the menu item
                print(menu_item.name)
            else:
                print(f"Menu item with ID {order_item_id} not found.")

    return jsonify({"orders": order_items})
