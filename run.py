from app import create_app
from app.models import init_tables, init_menu_items
app = create_app()
init_tables(app)
init_menu_items(app)
if __name__ == '__main__':
    app.run(debug=True)

