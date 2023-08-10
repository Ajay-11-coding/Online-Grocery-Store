from flask import Flask, flash, render_template, request, redirect, url_for
from flask.globals import session
from flask.helpers import make_response
from werkzeug.exceptions import HTTPException
from flask_restful import Resource, Api, reqparse, fields, marshal_with
from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = "Ajay's_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grocery_store.sqlite3'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}  # Disable thread check for SQLite
# app.config['UPLOAD_FOLDER'] = 'static/images/products'


db = SQLAlchemy(app)
api = Api(app)

login_manager = LoginManager(app)
login_manager.login_view = '/'

# Global variable to store the user type (admin or user)
user_type = None

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

 

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)



class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    admin = db.relationship('Admin', backref=db.backref('sections', lazy=True))

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    rate_per_unit = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    section = db.relationship('Section', backref=db.backref('products', lazy=True))



class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    user = db.relationship('User', backref=db.backref('carts', lazy=True))
    product = db.relationship('Product', backref=db.backref('carts', lazy=True))


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='transactions')
    product = db.relationship('Product', backref='transactions')

@login_manager.user_loader
def load_user(user_id):

    global user_type

    # Retrieve the user type (admin or user) from the session
    user_type = session.get('user_type')

    if user_type == 'admin':
        return Admin.query.get(int(user_id))
    else:
        return User.query.get(int(user_id))
        

    # If neither Admin nor User found
    # return None

def create_tables():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['admin_username']
        password = request.form['admin_password']

        admin = Admin.query.filter_by(username=username, password=password).first()

        if admin:
            # Set user_type to 'admin' in the session
            session['user_type'] = 'admin'

            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin/admin_login_signup.html', error='Invalid credentials')

    return render_template('admin/admin_login_signup.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['user_username']
        password = request.form['user_password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # Set user_type to 'user' in the session
            session['user_type'] = 'user'

            login_user(user)
            return redirect(url_for('user_dashboard'))
        else:
            return render_template('user/user_login_signup.html', error='Invalid credentials')

    return render_template('user/user_login_signup.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
      
        admin_username = request.form['admin_signup_username']
        admin_password = request.form['admin_signup_password']

         # Check if the username is already taken
        existing_user = Admin.query.filter_by(username=admin_username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('admin_signup'))

        new_admin = Admin(username=admin_username, password=admin_password)
        db.session.add(new_admin)
        db.session.commit()
        flash('Signed Up Successfully !!')
        return redirect(url_for('admin_login'))

    return render_template('admin/admin_login_signup.html')

@app.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':

        user_username = request.form['user_signup_username']
        user_password = request.form['user_signup_password']
        user_date_of_birth = request.form['user_date_of_birth']
        user_gender = request.form['user_gender']

         # Check if the username is already taken
        existing_user = User.query.filter_by(username=user_username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('user_signup'))

        new_user = User(username=user_username, password=user_password, date_of_birth=user_date_of_birth, gender=user_gender)
        db.session.add(new_user)
        db.session.commit()
        flash('Signed Up Successfully !!')
        return redirect(url_for('user_login'))

    return render_template('user/user_login_signup.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_type', None)
    logout_user()

    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    #sections = Section.query.filter_by(admin_id=current_user.id).all()
    sections = Section.query.all()
    return render_template('admin/admin_dashboard.html', sections=sections)

@app.route('/admin/dashboard/add_section', methods=['GET', 'POST'])
@login_required
def add_section():
    if request.method == 'POST':

        section_name = request.form['section_name']
        new_section = Section(name=section_name, admin=current_user)
        db.session.add(new_section)
        db.session.commit()
        flash(f'Section {section_name} added successfully !!')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_section.html')


@app.route('/admin/dashboard/edit_section/<int:section_id>', methods=['GET', 'POST'])
@login_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)

    if request.method == 'POST':
        section_name = request.form['section_name']
        section.name = section_name
        db.session.commit()
        flash(f'Section {section_name} edited successfully !!')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_section.html', section=section)


@app.route('/admin/dashboard/section/<int:section_id>', methods=['GET', 'POST'])
@login_required
def section_dashboard(section_id):
    section = Section.query.get_or_404(section_id)

    if request.method == 'POST':

        product_name = request.form['product_name']
        unit = request.form['unit']
        rate_per_unit = float(request.form['rate_per_unit'])
        quantity = int(request.form['quantity'])

        new_product = Product(name=product_name, unit=unit, rate_per_unit=rate_per_unit, quantity=quantity, section=section)
        db.session.add(new_product)
        db.session.commit()
        flash(f'Product {product_name} added successfully !!')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/section_dashboard.html', section=section)

@app.route('/admin/dashboard/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':

        product_name = request.form['product_name']
        unit = request.form['unit']
        rate_per_unit = float(request.form['rate_per_unit'])
        quantity = int(request.form['quantity'])

        product.name = product_name
        product.unit = unit
        product.rate_per_unit = rate_per_unit
        product.quantity = quantity
        db.session.commit()
        flash(f'Product {product_name} edited successfully !!')
        return redirect(url_for('section_dashboard', section_id=product.section_id))

    return render_template('admin/edit_product.html', product=product)


@app.route('/admin/dashboard/section/<int:section_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    
    product_count = Product.query.filter_by(section_id=section_id).count()
    if product_count > 0:
        flash("Cannot delete section with associated products.", 'error')
        return redirect(url_for('admin_dashboard'))

    flash(f'Section deleted successfully !!')
    db.session.delete(section)
    reorder_section_ids()
    db.session.commit()
    
    
    return redirect(url_for('admin_dashboard'))

#------------------------------------------------------------------------------------#
#REORDERING SECTION ID'S

def reorder_section_ids():
    # Get all the sections ordered by their IDs
    section = Section.query.order_by(Section.id).all()

    # Update the section IDs based on their order
    for idx, section in enumerate(section, 1):
        section.id = idx

    # Commit the changes to the database
    db.session.commit()


#REORDERING PRODUCT ID'S

def reorder_product_ids():
    # Get all the products ordered by their IDs
    products = Product.query.order_by(Product.id).all()

    # Update the product IDs based on their order
    for idx, product in enumerate(products, 1):
        product.id = idx

    # Commit the changes to the database
    db.session.commit()


#REORDERING CART ID'S

def reorder_transaction_ids():
    # Get all the transactions ordered by their IDs
    transaction_items = Transaction.query.order_by(Transaction.id).all()

    # Update the transaction IDs based on their order
    for idx, item in enumerate(transaction_items, 1):
        item.id = idx

    # Commit the changes to the database
    db.session.commit()


#REORDERING TRANSACTION ID'S

def reorder_cart_ids():
    # Get all the cart items ordered by their IDs
    cart_items = Cart.query.order_by(Cart.id).all()

    # Update the cart IDs based on their order
    for idx, item in enumerate(cart_items, 1):
        item.id = idx

    # Commit the changes to the database
    db.session.commit()

#------------------------------------------------------------------------------------#


@app.route('/admin/dashboard/section/<int:section_id>/product/<int:product_id>/delete', methods=['GET', 'POST'])
@login_required 
def delete_product(section_id, product_id):
    product = Product.query.get_or_404(product_id)
    section = section_id

    # Check if there are associated transactions
    transactions = Transaction.query.filter_by(product_id=product_id).all()
    if transactions:
        for transaction in transactions:
            db.session.delete(transaction)
    
    reorder_transaction_ids()
    

    # Check if there are associated cart items
    cart_items = Cart.query.filter_by(product_id=product_id).all()
    if cart_items:
        for item in cart_items:
            db.session.delete(item)
    
    reorder_cart_ids()
   
    # Remove the product from the database
    db.session.delete(product)
    reorder_product_ids()
    db.session.commit()
    

    flash(f'Product deleted successfully !!')
    return redirect(url_for('admin_dashboard', section_id=section))


# User Dashboard
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    # Handle the search form submission
    if request.method == 'POST':
        category_id = request.form.get('category')
        price_range = request.form.get('price_range')

        # Query products based on the selected category and price range
        products = Product.query
        if category_id:
            products = products.filter(Product.section_id == category_id)
        if price_range:
            min_price, max_price = map(int, price_range.split('-'))
            products = products.filter(Product.rate_per_unit >= min_price, Product.rate_per_unit <= max_price)

        # Fetch the filtered products from the database
        filtered_products = products.all()
        if(products.all()==[]):
            flash("No products in that category/price-range found !!")

        return render_template('user/user_dashboard.html', sections=Section.query.all(), filtered_products=filtered_products)

    # For GET request or when the search form is not submitted, display all sections and products
    return render_template('user/user_dashboard.html', sections=Section.query.all(), filtered_products=None)



@app.route('/user/dashboard/buy_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('user/buy_product.html', product=product)


@app.route('/user/cart', methods=['GET', 'POST'])
@login_required
def cart():
    if request.method == 'POST':
        # Perform checkout and save the cart contents to the database as transactions
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        grand_total = 0

        for item in cart_items:
            # Update product quantity and save the transaction
            product = Product.query.get_or_404(item.product_id)
            if product.quantity < item.quantity:
                flash(f'Not enough stock for {product.name}. Please remove from cart or reduce quantity.', 'error')
                return redirect(url_for('cart'))

            product.quantity -= item.quantity
            grand_total += item.total_price
        
            transaction = Transaction(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity, total_price=item.total_price)
            db.session.add(transaction)
        
        reorder_transaction_ids()

        # Delete all cart items after processing them
        for item in cart_items:
            db.session.delete(item)
        
        reorder_cart_ids()
        

        db.session.commit()
        flash('Checkout successful!', 'success')
        return redirect(url_for('user_dashboard'))

    else:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        grand_total = sum(item.total_price for item in cart_items)
        return render_template('user/cart.html', cart_items=cart_items, grand_total=grand_total)


@app.route('/edit_cart_product/<int:product_id>', methods=['GET', 'POST'])
@login_required 
def edit_cart_product(product_id):
    product=Product.query.get_or_404(product_id)
    item = Cart.query.filter_by(product_id=product_id).first()
    if request.method=='POST':
        item.quantity = int(request.form.get('quantity'))
        item.total_price = round(item.quantity * product.rate_per_unit, 2)
        db.session.commit()
        flash('Product quantity updated successfully!', 'success')
        return redirect(url_for('cart'))
    
    return render_template('user/edit_cart_product.html', product=product, item=item)


@app.route('/delete_cart_product/<int:product_id>', methods=['GET', 'POST'])
def delete_cart_product(product_id):
    cart_product = Cart.query.filter_by(product_id=product_id).first()
    db.session.delete(cart_product)
    reorder_cart_ids()
    db.session.commit()
    flash('Product removed from the cart.', 'success')
    return redirect(url_for('cart'))



@app.route('/user/dashboard/buy_product/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form['quantity'])

    if quantity <= 0 or quantity > product.quantity:
        flash('Invalid quantity selected', 'error')
        return redirect(url_for('buy_product', product_id=product_id))

    total_price = product.rate_per_unit * quantity

    # Add the product to the cart
    cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity, total_price=total_price)
    db.session.add(cart_item)
    db.session.commit()

    flash('Product added to cart', 'success')
    return redirect(url_for('cart'))

#------------------------------------------------------------------------------------------------------#
#API AREA

# Error classes
class NotFoundError(HTTPException):
    def __init__(self,status_code,error_message,error_code):
        message={'error_code':error_code,"error_message":error_message}
        self.response=make_response(json.dumps(message),status_code)


class ValidationError(HTTPException):
    def __init__(self,status_code,error_message,error_code):
        message={'error_code':error_code,"error_message":error_message}
        self.response=make_response(json.dumps(message),status_code)


# Field templates for marshaling
section_template = {
    'id': fields.Integer,
    'name': fields.String,
    'admin_id': fields.Integer,
}

product_template = {
    'id': fields.Integer,
    'name': fields.String,
    'unit': fields.String,
    'rate_per_unit': fields.Float,
    'quantity': fields.Integer,
    'section_id': fields.Integer,
}


# Request parsers
section_parser = reqparse.RequestParser()
section_parser.add_argument('name')
section_parser.add_argument('admin_id')


product_parser = reqparse.RequestParser()
product_parser.add_argument('name')
product_parser.add_argument('unit')
product_parser.add_argument('rate_per_unit')
product_parser.add_argument('quantity')
product_parser.add_argument('section_id')


# Resource for sections
class SectionsResource(Resource):
    @marshal_with(section_template)
    def get(self, section_id):
        section = Section.query.filter_by(id=section_id).first()
        if section:
            return section
        else:
            raise NotFoundError(status_code=404, error_code="SE1001", error_message="Section not found.")

    @marshal_with(section_template)
    def put(self, section_id):
        section = Section.query.filter_by(id=section_id).first()
        if not section:
            raise NotFoundError(status_code=404, error_code="SE1001", error_message="Section not found.")

        args = section_parser.parse_args()

        # Validate fields
        if not args['name']:
            raise ValidationError(status_code=400, error_code="SE1002", error_message="Section name is required and should be a string.")

        section.name = args['name']
        db.session.commit()

        return section

    def delete(self, section_id):
        section = Section.query.filter_by(id=section_id).first()
        if not section:
            raise NotFoundError(status_code=404, error_code="SE1001", error_message="Section not found.")

         # Check if there are associated transactions
        products = Product.query.filter_by(section_id=section_id).all()
        if (len(products)>0):
             raise ValidationError(status_code=400, error_code="SE1003", error_message="Section cannot be deleted with products inside.")

               
        db.session.delete(section)
        db.session.commit()
        return f"Product {section.name} deleted successfully !!"

    @marshal_with(section_template)
    def post(self):
        args = section_parser.parse_args()

        # Validate fields
        if not args['name']:
            raise ValidationError(status_code=400, error_code="SE1002", error_message="Section name is required and should be a string.")

        new_section = Section(name=args['name'], admin_id=args['admin_id'])  
        db.session.add(new_section)
        db.session.commit()

        return new_section


# Resource for products
class ProductsResource(Resource):
    @marshal_with(product_template)
    def get(self, product_id):
        product = Product.query.filter_by(id=product_id).first()
        if product:
            return product
        else:
            raise NotFoundError(status_code=404, error_code="PR1001", error_message="Product not found.")

    @marshal_with(product_template)
    def put(self, product_id):
        product = Product.query.filter_by(id=product_id).first()
        if not product:
            raise NotFoundError(status_code=404, error_code="PR1001", error_message="Product not found.")

        args = product_parser.parse_args()
        product.name = args['name']
        product.unit = args['unit']
        product.rate_per_unit = args['rate_per_unit']
        product.quantity = args['quantity']
        product.section_id = args['section_id']

        # Validate fields
        if not args['name']:
            raise ValidationError(status_code=400, error_code="PR1002", error_message="Product name is required and should be a string.")

        if not args['unit']:
            raise ValidationError(status_code=400, error_code="PR1003", error_message="Product unit is required and should be a string.")

        if not args['rate_per_unit']:
            raise ValidationError(status_code=400, error_code="PR1004", error_message="Product rate per unit is required and should be a number.")

        if not args['quantity']:
            raise ValidationError(status_code=400, error_code="PR1005", error_message="Product quantity is required and should be an integer.")

        if not args['section_id']:
            raise ValidationError(status_code=400, error_code="PR1006", error_message="Product section_id is required and should be an integer.")

        db.session.commit()

        return product

    def delete(self, product_id):
        product = Product.query.filter_by(id=product_id).first()
        if not product:
            raise NotFoundError(status_code=404, error_code="PR1001", error_message="Product not found.")
        
        # Check if there are associated transactions
        transactions = Transaction.query.filter_by(product_id=product_id).all()
        if transactions:
            for transaction in transactions:
                db.session.delete(transaction)

        # Check if there are associated cart items
        cart_items = Cart.query.filter_by(product_id=product_id).all()
        if cart_items:
            for item in cart_items:
                db.session.delete(item)

        db.session.delete(product)
        db.session.commit()
        return f"Product {product.name} deleted successfully !!"

    @marshal_with(product_template)
    def post(self):
        args = product_parser.parse_args()

        # Validate fields
        if not args['name']:
            raise ValidationError(status_code=400, error_code="PR1002", error_message="Product name is required and should be a string.")

        if not args['unit']:
            raise ValidationError(status_code=400, error_code="PR1003", error_message="Product unit is required and should be a string.")

        if not args['rate_per_unit']:
            raise ValidationError(status_code=400, error_code="PR1004", error_message="Product rate per unit is required and should be a number.")

        if not args['quantity']:
            raise ValidationError(status_code=400, error_code="PR1005", error_message="Product quantity is required and should be an integer.")

        if not args['section_id']:
            raise ValidationError(status_code=400, error_code="PR1006", error_message="Product section_id is required and should be an integer.")

        new_product = Product(
            name=args['name'],
            unit=args['unit'],
            rate_per_unit=args['rate_per_unit'],
            quantity=args['quantity'],
            section_id=args['section_id']
        )
        db.session.add(new_product)
        db.session.commit()

        return new_product


# Add API resources
api.add_resource(SectionsResource, '/api/section/<int:section_id>', '/api/section')
api.add_resource(ProductsResource, '/api/product/<int:product_id>', '/api/product')

    
if __name__ == '__main__':
    create_tables()  # Create the necessary tables if they don't exist
    app.run(debug=True)