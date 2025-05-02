import sys
import json
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QMessageBox, QLineEdit, QDialog, 
                             QScrollArea, QFrame, QStyle, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette
from socketio import Client

class SocketSignals(QObject):
    new_order = pyqtSignal(dict)
    item_completed = pyqtSignal(dict)
    order_completed = pyqtSignal(dict)

class IPConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Configuration")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        self.ip_label = QLabel("Server IP Address:")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.100")
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.save_button)
        
        self.setLayout(layout)
    
    def get_ip(self):
        return self.ip_input.text().strip()

class KitchenScreen(QMainWindow):
    def __init__(self, server_ip):
        super().__init__()
        self.server_ip = server_ip
        self.orders = []
        
        # Socket.IO setup
        self.sio = Client()
        self.socket_signals = SocketSignals()
        self.socket_signals.new_order.connect(self.handle_new_order)
        self.socket_signals.item_completed.connect(self.handle_item_completed)
        self.socket_signals.order_completed.connect(self.handle_order_completed)
        
        # Window setup
        self.setWindowTitle("Kitchen Display System")
        self.setMinimumSize(1024, 768)
        
        # Set dark theme
        self.set_dark_theme()
        
        self.init_ui()
        self.connect_to_socket()
        self.fetch_orders()
        
        # Set up a timer to periodically refresh orders
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.fetch_orders)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(palette)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("Kitchen Display System")
        self.title_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #FF9800;")
        
        self.refresh_btn = QPushButton("Refresh Orders")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.refresh_btn.clicked.connect(self.fetch_orders)
        
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.refresh_btn)
        main_layout.addLayout(header)
        
        # Orders grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.orders_container = QWidget()
        self.orders_grid = QGridLayout()
        self.orders_grid.setAlignment(Qt.AlignTop)
        self.orders_grid.setSpacing(15)
        self.orders_grid.setContentsMargins(15, 15, 15, 15)
        self.orders_container.setLayout(self.orders_grid)
        
        self.scroll_area.setWidget(self.orders_container)
        main_layout.addWidget(self.scroll_area)
        
        # Status bar
        self.statusBar().showMessage(f"Connected to: {self.server_ip}")
    
    def connect_to_socket(self):
        try:
            url = f"http://{self.server_ip}:5000"
            print(f"Connecting to socket at: {url}")
            
            @self.sio.on('connect')
            def on_connect():
                print("Connected to KDS server")
                self.statusBar().showMessage(f"Connected to: {self.server_ip} (Socket active)")
            
            @self.sio.on('disconnect')
            def on_disconnect():
                print("Disconnected from KDS server")
                self.statusBar().showMessage(f"Connected to: {self.server_ip} (Socket disconnected)")
            
            @self.sio.on('new_order')
            def on_new_order(data):
                print("New order received via socket")
                self.socket_signals.new_order.emit(data)
            
            @self.sio.on('item_completed')
            def on_item_completed(data):
                print(f"Item completed: {data}")
                self.socket_signals.item_completed.emit(data)
            
            @self.sio.on('order_completed')
            def on_order_completed(data):
                print(f"Order completed: {data}")
                self.socket_signals.order_completed.emit(data)
            
            self.sio.connect(url)
                
        except Exception as e:
            print(f"Socket connection error: {e}")
            self.statusBar().showMessage(f"Connected to: {self.server_ip} (Socket error)")
    
    def handle_new_order(self, data):
        self.fetch_orders()
    
    def handle_item_completed(self, data):
        # Update the specific item in our local orders list
        for order in self.orders:
            if order['id'] == data['order_id']:
                for item in order['items']:
                    if item['id'] == data['item_id']:
                        item['completed'] = True
                        break
                break
        self.display_orders()
    
    def handle_order_completed(self, data):
        # Remove the completed order from our local list
        self.orders = [order for order in self.orders if order['id'] != data['order_id']]
        self.display_orders()
    
    def fetch_orders(self):
        try:
            url = f"http://{self.server_ip}:5000/api/kds/orders?station=kitchen"
            response = requests.get(url)
            
            if response.status_code == 200:
                self.orders = response.json()
                self.display_orders()
            else:
                raise Exception(f"Failed to load orders: {response.text}")
                
        except Exception as e:
            print(f"Error fetching orders: {e}")
            self.statusBar().showMessage(f"Error loading orders: {str(e)}", 5000)
    
    def display_orders(self):
        # Clear existing orders
        for i in reversed(range(self.orders_grid.count())): 
            widget = self.orders_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.orders:
            no_orders_label = QLabel("No pending orders")
            no_orders_label.setAlignment(Qt.AlignCenter)
            no_orders_label.setStyleSheet("""
                font-size: 24px; 
                color: #888;
                padding: 40px;
            """)
            self.orders_grid.addWidget(no_orders_label, 0, 0, 1, 2)
            return
        
        # Calculate grid position
        row = 0
        col = 0
        max_columns = 2
        
        for order in self.orders:
            order_widget = self.create_order_widget(order)
            self.orders_grid.addWidget(order_widget, row, col)
            
            # Update grid position
            col += 1
            if col >= max_columns:
                col = 0
                row += 1
    
    def create_order_widget(self, order):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLineWidth(1)
        frame.setMinimumWidth(450)
        frame.setMaximumWidth(500)
        frame.setStyleSheet("""
            QFrame {
                background-color: #424242;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #555;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        frame.setLayout(layout)
        
        # Order header
        header = QHBoxLayout()
        
        table_label = QLabel(f"🪑 Table {order['table_id']}")
        table_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 18px;
            color: #FF9800;
        """)
        
        wait_time_label = QLabel(f"⏱ {order['wait_time']}")
        wait_time_label.setStyleSheet("""
            color: #9E9E9E;
            font-size: 14px;
        """)
        
        header.addWidget(table_label)
        header.addStretch()
        header.addWidget(wait_time_label)
        layout.addLayout(header)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("border: 1px solid #555;")
        layout.addWidget(divider)
        
        # Items
        items_container = QWidget()
        items_layout = QVBoxLayout()
        items_layout.setSpacing(6)
        items_container.setLayout(items_layout)
        
        for item in order['items']:
            item_widget = self.create_item_widget(item, order['id'])
            items_layout.addWidget(item_widget)
        
        # Add scroll area for items if there are many
        if len(order['items']) > 4:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(items_container)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #424242;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #757575;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
            layout.addWidget(scroll)
        else:
            layout.addWidget(items_container)
        
        # Complete order button
        all_completed = all(item['completed'] for item in order['items'])
        
        complete_btn = QPushButton("✅ Complete Order" if all_completed else "⚠️ Force Complete")
        complete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#4CAF50' if all_completed else '#FF9800'};
                color: white;
                border: none;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {'#388E3C' if all_completed else '#F57C00'};
            }}
        """)
        complete_btn.clicked.connect(lambda _, oid=order['id']: self.complete_order(oid))
        layout.addWidget(complete_btn)
        
        return frame
    
    def create_item_widget(self, item, order_id):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        widget.setLayout(layout)
        
        # Status indicator
        status_indicator = QFrame()
        status_indicator.setFixedSize(8, 30)
        status_indicator.setStyleSheet(f"""
            background-color: {'#4CAF50' if item['completed'] else '#FF9800'};
            border-radius: 4px;
        """)
        layout.addWidget(status_indicator)
        
        # Item info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(item['name'])
        name_label.setStyleSheet(f"""
            font-size: 16px;
            color: {'#9E9E9E' if item['completed'] else 'white'};
            text-decoration: {'line-through' if item['completed'] else 'none'};
        """)
        
        category_label = QLabel(f"📋 {item['category']}")
        category_label.setStyleSheet("""
            color: #757575;
            font-size: 12px;
        """)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(category_label)
        layout.addLayout(info_layout)
        
        # Complete button
        if not item['completed']:
            complete_btn = QPushButton()
            complete_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            complete_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    color: #4CAF50;
                    padding: 5px;
                    min-width: 30px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    color: #388E3C;
                }
            """)
            complete_btn.clicked.connect(lambda _, oid=order_id, iid=item['id'], iname=item['name']: 
                                        self.complete_item(oid, iid, iname))
            layout.addWidget(complete_btn, alignment=Qt.AlignRight)
        else:
            completed_label = QLabel("✔ Done")
            completed_label.setStyleSheet("""
                color: #4CAF50;
                font-style: italic;
                font-size: 14px;
            """)
            layout.addWidget(completed_label, alignment=Qt.AlignRight)
        
        widget.setStyleSheet("""
            background-color: #353535;
            border-radius: 6px;
        """)
        
        return widget
    
    def complete_item(self, order_id, item_id, item_name):
        try:
            # Optimistic UI update
            for order in self.orders:
                if order['id'] == order_id:
                    for item in order['items']:
                        if item['id'] == item_id:
                            item['completed'] = True
                            break
                    break
            self.display_orders()
            
            # Send request to server
            url = f"http://{self.server_ip}:5000/api/kds/complete_item"
            data = {
                'order_id': order_id,
                'item_id': item_id
            }
            response = requests.post(url, json=data)
            
            if response.status_code != 200:
                # Revert if failed
                for order in self.orders:
                    if order['id'] == order_id:
                        for item in order['items']:
                            if item['id'] == item_id:
                                item['completed'] = False
                                break
                        break
                self.display_orders()
                raise Exception(f"Failed to complete item: {response.text}")
                
        except Exception as e:
            print(f"Error completing item: {e}")
            QMessageBox.warning(self, "Error", f"Failed to complete item: {str(e)}")
    
    def complete_order(self, order_id):
        # Check if there are pending items
        order = next((o for o in self.orders if o['id'] == order_id), None)
        if not order:
            return
            
        pending_items = [i for i in order['items'] if not i['completed']]
        
        if pending_items:
            reply = QMessageBox.question(
                self, 
                "Complete Order?", 
                f"There are {len(pending_items)} items not marked as prepared. Complete the entire order anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        try:
            url = f"http://{self.server_ip}:5000/api/kds/complete"
            data = {
                'order_id': order_id
            }
            response = requests.post(url, json=data)
            
            if response.status_code != 200:
                raise Exception(f"Failed to complete order: {response.text}")
                
        except Exception as e:
            print(f"Error completing order: {e}")
            QMessageBox.warning(self, "Error", f"Failed to complete order: {str(e)}")
    
    def closeEvent(self, event):
        self.sio.disconnect()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    
    # Check for saved server IP
    settings = {}
    try:
        with open('kds_settings.json', 'r') as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    server_ip = settings.get('server_ip', '')
    
    if not server_ip:
        ip_dialog = IPConfigDialog()
        if ip_dialog.exec_() == QDialog.Accepted:
            server_ip = ip_dialog.get_ip()
            if server_ip:
                settings['server_ip'] = server_ip
                with open('kds_settings.json', 'w') as f:
                    json.dump(settings, f)
            else:
                QMessageBox.warning(None, "Error", "Server IP cannot be empty")
                sys.exit(1)
        else:
            sys.exit(0)
    
    window = KitchenScreen(server_ip)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
