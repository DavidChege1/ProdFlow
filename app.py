from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = '123'  # Required for Flask-Login

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pts.db'  # Change for SQL Server
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')  # e.g., admin, viewer

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    


# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    specification = db.Column(db.Text, nullable=True)

# Bill of Materials Model
class BillOfMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    component_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# Orders Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="Pending")  # Options: Pending, In Progress, Completed
    order_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    product = db.relationship('Product', backref='orders')


with app.app_context():
    db.create_all()  # make sure all tables are created

    # Check if admin user exists, then create if not
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")



@app.route('/')
@login_required
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add-product', methods=['POST'])
@login_required
def add_product():
    name = request.form['name']
    specification = request.form['specification']
    new_product = Product(name=name, specification=specification)
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete-product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update-product/<int:id>', methods=['GET', 'POST'])
@login_required
def update_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.specification = request.form['specification']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update_product.html', product=product)

@app.route('/product/<int:product_id>/bom', methods=['GET', 'POST'])
@login_required
def manage_bom(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        component_name = request.form['component_name']
        quantity = request.form['quantity']
        bom_item = BillOfMaterial(product_id=product_id, component_name=component_name, quantity=quantity)
        db.session.add(bom_item)
        db.session.commit()
        return redirect(url_for('manage_bom', product_id=product_id))

    bom_items = BillOfMaterial.query.filter_by(product_id=product_id).all()
    return render_template('bom.html', product=product, bom_items=bom_items)

@app.route('/delete-bom/<int:id>', methods=['POST'])
@login_required
def delete_bom(id):
    item = BillOfMaterial.query.get_or_404(id)
    product_id = item.product_id
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('manage_bom', product_id=product_id))

@app.route('/orders')
@login_required
def orders():
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    products = Product.query.all()
    return render_template('orders.html', orders=all_orders, products=products)

@app.route('/add-order', methods=['POST'])
@login_required
def add_order():
    product_id = request.form['product_id']
    quantity = request.form['quantity']
    new_order = Order(product_id=product_id, quantity=quantity)
    db.session.add(new_order)
    db.session.commit()
    return redirect(url_for('orders'))

@app.route('/update-order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form['status']
    db.session.commit()
    return redirect(url_for('orders'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        order.quantity = request.form['quantity']
        order.status = request.form['status']
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template('update_order.html', order=order)

if __name__ == '__main__':
    app.run(debug=True)