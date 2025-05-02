from flask import Blueprint, jsonify, render_template, request
from .models import Table, MenuItem, Order, OrderItem, KitchenOrderItem,KitchenOrder
from . import db, socketio
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import JSON  
from datetime import datetime

main = Blueprint('main', __name__)


@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/tables', methods=['GET'])
@login_required
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
@login_required
def create_order():
    table_id = request.form.get('table_id')
    item_ids = request.form.getlist('items[]')
    
    # Create original order
    new_order = Order(table_id=table_id)
    db.session.add(new_order)
    db.session.flush()

    # Create KitchenOrder with proper relational items
    kds_order = KitchenOrder(table_id=table_id)
    db.session.add(kds_order)
    db.session.flush()  # Get the kds_order.id
    
    # Add items to both Order and KitchenOrder
    for item_id in item_ids:
        menu_item = MenuItem.query.get(item_id)
        if menu_item:
            # Original order items
            db.session.add(OrderItem(
                order_id=new_order.id, 
                menu_item_id=item_id
            ))
            
            # Kitchen display items
            db.session.add(KitchenOrderItem(
                order_id=kds_order.id,
                menu_item_id=menu_item.id,
                name=menu_item.name,
                category=menu_item.category,
                completed=False
            ))

    # Update table status
    table = Table.query.get(table_id)
    if table:
        table.status = "Occupied"

    try:
        db.session.commit()
        socketio.emit('update_tables')
        socketio.emit('new_order', {
            'table_id': table_id,
            'station': 'kitchen' if any(i.category not in ['Drink', 'Dessert',"Drinks"] 
                      for i in kds_order.items) else 'bar'
        })
        return jsonify({"status": "success", "order_id": new_order.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500


@main.route('/free_table', methods=['POST'])
@login_required
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
        socketio.emit('update_tables')
        socketio.emit('table_freed',{'table_id':table_id, 'status':'Available'})
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

@main.route('/check_auth')
def check_auth():
    return jsonify({
        'authenticated': current_user.is_authenticated
    })

#### FLUTTER MOBILE API ######
@main.route('/flutter_api/free_table', methods=['POST'])
def free_table_flutter():
    table_id = request.form.get('table_id')

    orders = Order.query.filter_by(table_id=table_id, status='open').all()
    for order in orders:
        order.status = 'closed'

    table = Table.query.get(table_id)
    if table:
        table.status = 'Available'

    db.session.commit()

    return jsonify({"message": f"Table {table_id} freed."})

@main.route('/flutter_api/order', methods=['POST'])
def create_order_flutter():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        table_id = data.get('table_id')
        item_ids = data.get('items', [])
        
        if not table_id or not item_ids:
            return jsonify({"status": "error", "message": "Missing table_id or items"}), 400

        # Create original order
        new_order = Order(table_id=table_id)
        db.session.add(new_order)
        db.session.flush()

        # Create KitchenOrder
        kds_order = KitchenOrder(table_id=table_id)
        db.session.add(kds_order)
        db.session.flush()

        # Add items to both Order and KitchenOrder
        for item_id in item_ids:
            menu_item = MenuItem.query.get(item_id)
            if menu_item:
                # Original order items
                db.session.add(OrderItem(
                    order_id=new_order.id, 
                    menu_item_id=item_id
                ))
                
                # Kitchen display items
                db.session.add(KitchenOrderItem(
                    order_id=kds_order.id,
                    menu_item_id=menu_item.id,
                    name=menu_item.name,
                    category=menu_item.category,
                    completed=False
                ))

        # Update table status
        table = Table.query.get(table_id)
        if table:
            table.status = "Occupied"

        db.session.commit()

        # Determine station
        has_kitchen_items = any(i.category not in ['Drink', 'Dessert', "Drinks"] 
                              for i in kds_order.items)
        station = 'kitchen' if has_kitchen_items else 'bar'

        socketio.emit('update_tables')
        socketio.emit('new_order', {
            'table_id': table_id,
            'station': station
        }, namespace='/')

        return jsonify({
            "status": "success", 
            "order_id": new_order.id,
            "kds_order_id": kds_order.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error", 
            "error": str(e),
            "message": "Failed to create order"
        }), 500

@main.route('/flutter_api/menu', methods=['GET'])
def get_menu_flutter():
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

@main.route('/flutter_api/get_orders/<int:table_id>', methods=['GET'])
def get_orders_flutter(table_id):
    orders = Order.query.filter_by(table_id=table_id, status='open').all()
    order_items = []

    for order in orders:
        for item in order.items:
            if item.menu_item:
                order_items.append(item.menu_item.name)

    return jsonify({"orders": order_items})

@main.route('/flutter_api/tables', methods=['GET'])
def get_tables_flutter():
    tables = Table.query.all()
    return jsonify([{"id": t.id, "number": t.number, "status": t.status} for t in tables])









##### BILL RECEIPTS ##########
import pdfkit
import os
from flask import send_file
from io import BytesIO
@main.route('/receipt/<int:table_id>')
def generate_receipt(table_id):
    table = Table.query.get_or_404(table_id)
    orders = Order.query.filter_by(table_id=table_id, status='open').all()

    items = []
    total = 0
    for order in orders:
        for item in order.items:
            if item.menu_item:
                items.append(item.menu_item)
                total += item.menu_item.price

    rendered_html = render_template('bill_template.html', table=table, items=items, total=round(total, 2))

    try:
        config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
        pdfkit.from_string(rendered_html, False, configuration=config)
        # Generate PDF in memory
        pdf = pdfkit.from_string(rendered_html, False)
        
        # Wrap in BytesIO for sending directly without saving to disk
        pdf_io = BytesIO(pdf)

        return send_file(
            pdf_io,
            as_attachment=True,
            download_name=f'receipt_table_{table_id}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500




@main.route('/receipt_preview/<int:table_id>', methods=['GET'])
def generate_receipt_preview(table_id):
    table = Table.query.get_or_404(table_id)
    orders = Order.query.filter_by(table_id=table_id, status='open').all()

    items = []
    total = 0
    for order in orders:
        for item in order.items:
            if item.menu_item:
                items.append({
                    'name': item.menu_item.name,
                    'price': item.menu_item.price
                })
                total += item.menu_item.price

    # Return a JSON response for the preview
    return jsonify({
        'table_number': table.number,
        'items': items,
        'total': round(total, 2)
    })






@socketio.on('connect')
def handle_connect():
    print('KDS Client connected')

@socketio.on('new_order')
def handle_new_order(data):
    emit('new_order', data, broadcast=True)

@socketio.on('order_update')
def handle_order_update(data):
    emit('order_update', data, broadcast=True)



###routes for the kitchen display system ###############
@main.route('/api/kds/complete_item', methods=['POST'])
def complete_kds_item():
    data = request.get_json()
    order_id = data['order_id']
    item_id = data['item_id']
    
    item = KitchenOrderItem.query.filter_by(
        order_id=order_id,
        menu_item_id=item_id,
        completed=False
    ).first()
    
    if not item:
        return jsonify({"status": "error", "message": "Item not found or already completed"}), 404
    
    item.completed = True
    item.completed_at = datetime.utcnow()
    
    # Check if all items are now completed
    order = KitchenOrder.query.get(order_id)
    if all(i.completed for i in order.items):
        order.status = 'completed'
        order.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    socketio.emit('item_completed', {
        'order_id': order_id,
        'item_id': item_id
    }, namespace='/')
    
    return jsonify({"status": "success"})

@main.route('/api/kds/complete', methods=['POST'])
def complete_kds_order():
    data = request.get_json()
    order_id = data['order_id']
    
    order = KitchenOrder.query.get(order_id)
    if not order:
        return jsonify({"status": "error", "message": "Order not found"}), 404
    
    # Mark all items as completed
    for item in order.items:
        if not item.completed:
            item.completed = True
            item.completed_at = datetime.utcnow()
    
    order.status = 'completed'
    order.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    socketio.emit('order_completed', {
        'order_id': order_id
    }, namespace='/')
    
    return jsonify({"status": "success"})

@main.route('/api/kds/orders')
def get_kds_orders():
    station = request.args.get('station', 'kitchen')
    query = KitchenOrder.query.filter_by(status='pending')

    result = []
    for order in query:
        # Filter items by station
        items = [{
            'id': item.menu_item_id,
            'name': item.name,
            'category': item.category,
            'completed': item.completed,
            'completed_at': item.completed_at.isoformat() if item.completed_at else None
        } for item in order.items if (
            station == 'all' or
            (station == 'kitchen' and item.category not in ['Drink', 'Dessert', "Drinks"])
            or (station == 'bar' and item.category in ['Drink', 'Dessert', "Drinks"])
        )]

        if items:
            wait_time = (datetime.utcnow() - order.created_at).seconds // 60
            result.append({
                'id': order.id,
                'table_id': order.table_id,
                'items': items,
                'wait_time': f"{wait_time}m",
                'station': station
            })

    return jsonify(result)
