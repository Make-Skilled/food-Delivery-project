from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# MongoDB configuration
MONGO_URI = 'mongodb://127.0.0.1:27017/'
client = MongoClient(MONGO_URI)
db = client['food__delivery']

# Collections
users = db.users
restaurants = db.restaurants
orders = db.orders

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        # Check if user already exists
        if users.find_one({'email': email}):
            flash('Email already registered!', 'error')
            return render_template('register.html')

        # Create new user
        new_user = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'password': generate_password_hash(password),
            'user_type': user_type,
            'created_at': datetime.datetime.now()
        }

        # Insert user into database
        result = users.insert_one(new_user)
        user_id = result.inserted_id

        # Add restaurant-specific fields and create restaurant document
        if user_type == 'restaurant':
            restaurant_name = request.form.get('restaurant_name')
            cuisine_type = request.form.get('cuisine_type')
            address = request.form.get('address')
            
            # Create restaurant document
            new_restaurant = {
                'user_id': user_id,
                'name': restaurant_name,
                'cuisine_type': cuisine_type,
                'address': address,
                'rating': 0,
                'menu_items': [],
                'created_at': datetime.datetime.now()
            }
            restaurants.insert_one(new_restaurant)

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_type'] = user['user_type']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            flash('Login successful!', 'success')
            
            # Redirect based on user type
            if user['user_type'] == 'restaurant':
                # Get the restaurant details for this user
                restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
                if restaurant:
                    return redirect(url_for('view_restaurant', restaurant_id=str(restaurant['_id'])))
                else:
                    flash('Restaurant profile not found.', 'error')
                    return redirect(url_for('home'))
            else:
                return redirect(url_for('home'))

        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Customer routes
@app.route('/')
def home():
    if 'user_id' in session and session.get('user_type') == 'restaurant':
        # Get restaurant data
        restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
        if restaurant:
            return redirect(url_for('view_restaurant', restaurant_id=str(restaurant['_id'])))
        else:
            flash('Restaurant profile not found.', 'error')
            return redirect(url_for('logout'))

    # For customers and non-logged in users, show the restaurant list
    restaurant_list = list(restaurants.find())
    return render_template('home.html', restaurants=restaurant_list)

@app.route('/restaurant/<restaurant_id>')
def view_restaurant(restaurant_id):
    restaurant = restaurants.find_one({'_id': ObjectId(restaurant_id)})
    if not restaurant:
        flash('Restaurant not found!', 'error')
        return redirect(url_for('home'))
    
    # Convert ObjectId to string for JSON serialization
    if restaurant.get('menu_items'):
        for item in restaurant['menu_items']:
            item['_id'] = str(item['_id'])
    restaurant['_id'] = str(restaurant['_id'])
    
    return render_template('restaurant.html', restaurant=restaurant)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to place an order'})

    try:
        data = request.get_json()
        
        if not data['items']:
            return jsonify({'success': False, 'message': 'Cart is empty'})

        # Get restaurant details from the first item (all items should be from same restaurant)
        restaurant_id = data['items'][0]['restaurant_id']
        restaurant = restaurants.find_one({'_id': ObjectId(restaurant_id)})
        
        if not restaurant:
            return jsonify({'success': False, 'message': 'Restaurant not found'})

        # Create order
        order = {
            'user_id': ObjectId(session['user_id']),
            'restaurant_id': ObjectId(restaurant_id),
            'restaurant_name': restaurant['name'],
            'items': [
                {
                    'id': item['id'],
                    'name': item['name'],
                    'price': float(item['price']),
                    'quantity': int(item['quantity'])
                } for item in data['items']
            ],
            'delivery_address': data['delivery_address'],
            'special_instructions': data.get('special_instructions', ''),
            'subtotal': float(data['subtotal']),
            'tax': float(data['tax']),
            'total': float(data['total']),
            'status': 'pending',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Insert order into database
        result = orders.insert_one(order)
        
        # Return success response with order ID
        return jsonify({
            'success': True, 
            'message': 'Order placed successfully',
            'order_id': str(result.inserted_id)
        })

    except Exception as e:
        print('Error placing order:', str(e))
        return jsonify({'success': False, 'message': f'Failed to place order: {str(e)}'})

# Restaurant owner routes
@app.route('/restaurant/dashboard')
def restaurant_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        flash('Access denied. Restaurant owners only.', 'error')
        return redirect(url_for('login'))

    # Get restaurant data
    restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
    if not restaurant:
        flash('Restaurant not found.', 'error')
        return redirect(url_for('home'))

    # Get restaurant orders
    restaurant_orders = list(orders.find({'restaurant_id': restaurant['_id']}).sort('created_at', -1))

    # Calculate dashboard data
    dashboard_data = {
        'total_orders': len(restaurant_orders),
        'pending_orders': sum(1 for order in restaurant_orders if order['status'] == 'pending'),
        'total_revenue': sum(order['total'] for order in restaurant_orders),
        'avg_rating': restaurant.get('rating', 0)
    }

    return render_template('restaurant_dashboard.html', data=dashboard_data)

@app.route('/restaurant/orders')
def view_orders():
    if 'user_id' not in session:
        flash('Please login to view orders', 'error')
        return redirect(url_for('login'))

    try:
        if session.get('user_type') == 'restaurant':
            # Get restaurant data
            restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
            if not restaurant:
                flash('Restaurant not found.', 'error')
                return redirect(url_for('home'))

            # Get all orders for this restaurant
            restaurant_orders = list(orders.find({
                'restaurant_id': restaurant['_id']
            }).sort('created_at', -1))

            # Get customer details for each order
            for order in restaurant_orders:
                # Get customer details
                customer = users.find_one({'_id': order['user_id']})
                if customer:
                    order['customer_name'] = f"{customer['first_name']} {customer['last_name']}"
                    order['customer_phone'] = customer['phone']
                else:
                    order['customer_name'] = 'Unknown Customer'
                    order['customer_phone'] = 'N/A'

                # Ensure all required fields exist with default values
                order['subtotal'] = float(order.get('subtotal', 0))
                order['tax'] = float(order.get('tax', 0))
                order['total'] = float(order.get('total', 0))
                order['status'] = order.get('status', 'pending')
                order['delivery_address'] = order.get('delivery_address', 'No address provided')
                order['special_instructions'] = order.get('special_instructions', '')
                order['created_at'] = order.get('created_at', datetime.datetime.now())
                order['updated_at'] = order.get('updated_at', datetime.datetime.now())

            return render_template('view_orders.html', 
                                orders=restaurant_orders, 
                                restaurant=restaurant,
                                user_type='restaurant')
        else:
            # Get customer orders
            customer_orders = list(orders.find({
                'user_id': ObjectId(session['user_id'])
            }).sort('created_at', -1))

            # Get restaurant details for each order
            for order in customer_orders:
                restaurant = restaurants.find_one({'_id': order['restaurant_id']})
                if restaurant:
                    order['restaurant_name'] = restaurant['name']
                    order['restaurant_address'] = restaurant['address']
                else:
                    order['restaurant_name'] = 'Unknown Restaurant'
                    order['restaurant_address'] = 'N/A'

                # Format dates
                order['created_at'] = order['created_at'].strftime('%B %d, %Y %I:%M %p')
                order['updated_at'] = order['updated_at'].strftime('%B %d, %Y %I:%M %p')

                # Ensure all required fields exist with default values
                order['subtotal'] = float(order.get('subtotal', 0))
                order['tax'] = float(order.get('tax', 0))
                order['total'] = float(order.get('total', 0))
                order['status'] = order.get('status', 'pending')

            return render_template('view_orders.html', 
                                orders=customer_orders,
                                user_type='customer')

    except Exception as e:
        flash(f'Error retrieving orders: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile.', 'error')
        return redirect(url_for('login'))

    user = users.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('logout'))

    if request.method == 'POST':
        # Update user profile
        update_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'phone': request.form.get('phone')
        }

        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            update_data['password'] = generate_password_hash(new_password)

        users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': update_data}
        )

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    cuisine = request.args.get('cuisine', '')

    # Build MongoDB query
    search_query = {}
    if query:
        search_query['$or'] = [
            {'name': {'$regex': query, '$options': 'i'}},
            {'cuisine_type': {'$regex': query, '$options': 'i'}}
        ]
    if cuisine:
        search_query['cuisine_type'] = cuisine

    restaurant_list = list(restaurants.find(search_query))
    return render_template('search_results.html',
                         restaurants=restaurant_list,
                         query=query,
                         cuisine=cuisine)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart.', 'error')
        return redirect(url_for('login'))
    
    # Get cart data from session or initialize empty cart
    cart_items = session.get('cart', [])
    
    # Calculate totals
    subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart_items)
    tax = round(subtotal * 0.08, 2)  # 8% tax
    total = subtotal + tax
    
    return render_template('cart.html', 
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         total=total)

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to add items to cart'})
    
    try:
        data = request.get_json()
        item = {
            'id': data.get('id'),
            'name': data.get('name'),
            'price': float(data.get('price', 0)),
            'quantity': int(data.get('quantity', 1)),
            'restaurant_id': data.get('restaurant_id')
        }
        
        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = []
            
        # Check if item is from same restaurant
        if session['cart'] and session['cart'][0]['restaurant_id'] != item['restaurant_id']:
            return jsonify({
                'success': False,
                'message': 'Items must be from the same restaurant'
            })
            
        # Check if item already exists in cart
        for cart_item in session['cart']:
            if cart_item['id'] == item['id']:
                cart_item['quantity'] += item['quantity']
                session.modified = True
                return jsonify({'success': True, 'message': 'Item quantity updated'})
        
        # Add new item to cart
        session['cart'].append(item)
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Item added to cart'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/cart/update', methods=['POST'])
def update_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to update cart'})
    
    try:
        data = request.get_json()
        item_id = data.get('id')
        quantity = int(data.get('quantity', 0))
        
        if 'cart' not in session:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Update item quantity or remove if quantity is 0
        for item in session['cart']:
            if item['id'] == item_id:
                if quantity > 0:
                    item['quantity'] = quantity
                else:
                    session['cart'].remove(item)
                session.modified = True
                break
        
        return jsonify({'success': True, 'message': 'Cart updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    if 'cart' in session:
        session.pop('cart')
    return jsonify({'success': True, 'message': 'Cart cleared'})

@app.route('/restaurant/menu/manage', methods=['GET', 'POST'])
def manage_menu():
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        flash('Access denied. Restaurant owners only.', 'error')
        return redirect(url_for('login'))

    # Get restaurant data
    restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
    if not restaurant:
        flash('Restaurant not found.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # Add new menu item
            new_item = {
                '_id': ObjectId(),
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'price': float(request.form.get('price', 0)),
                'category': request.form.get('category'),
                'is_available': True
            }
            
            restaurants.update_one(
                {'_id': restaurant['_id']},
                {'$push': {'menu_items': new_item}}
            )
            flash('Menu item added successfully!', 'success')
            
        elif action == 'update':
            # Update existing menu item
            item_id = request.form.get('item_id')
            
            restaurants.update_one(
                {
                    '_id': restaurant['_id'],
                    'menu_items._id': ObjectId(item_id)
                },
                {'$set': {
                    'menu_items.$.name': request.form.get('name'),
                    'menu_items.$.description': request.form.get('description'),
                    'menu_items.$.price': float(request.form.get('price', 0)),
                    'menu_items.$.category': request.form.get('category'),
                    'menu_items.$.is_available': request.form.get('is_available') == 'true'
                }}
            )
            flash('Menu item updated successfully!', 'success')
            
        elif action == 'delete':
            # Delete menu item
            item_id = request.form.get('item_id')
            
            restaurants.update_one(
                {'_id': restaurant['_id']},
                {'$pull': {'menu_items': {'_id': ObjectId(item_id)}}}
            )
            flash('Menu item deleted successfully!', 'success')

        return redirect(url_for('manage_menu'))

    # Get updated restaurant data with menu items
    restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
    return render_template('manage_menu.html', restaurant=restaurant)

@app.route('/restaurant/order/<order_id>/update', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        return jsonify({'success': False, 'message': 'Access denied'})

    try:
        data = request.form
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = ['pending', 'preparing', 'ready', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'})

        # Get restaurant data to verify ownership
        restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
        if not restaurant:
            return jsonify({'success': False, 'message': 'Restaurant not found'})

        # Get order and verify it belongs to this restaurant
        order = orders.find_one({'_id': ObjectId(order_id)})
        if not order or order['restaurant_id'] != restaurant['_id']:
            return jsonify({'success': False, 'message': 'Order not found'})

        # Update order status
        result = orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {
                'status': new_status,
                'updated_at': datetime.datetime.now()
            }}
        )

        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Order status updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update order status'})

    except Exception as e:
        print('Error updating order status:', str(e))
        return jsonify({'success': False, 'message': f'Error updating order status: {str(e)}'})

@app.route('/restaurant/menu/add', methods=['POST'])
def add_menu_item():
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        return jsonify({'success': False, 'message': 'Access denied. Restaurant owners only.'})

    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'category', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'})

        # Create new menu item
        new_item = {
            '_id': ObjectId(),  # Use ObjectId directly for consistency
            'name': data['name'],
            'description': data['description'],
            'category': data['category'],
            'price': float(data['price']),
            'image_url': data.get('image_url', ''),
            'is_available': data.get('is_available', True)
        }

        # Add item to restaurant's menu
        result = restaurants.update_one(
            {'user_id': ObjectId(session['user_id'])},
            {'$push': {'menu_items': new_item}}
        )

        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Menu item added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add menu item'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/restaurant/menu/update/<item_id>', methods=['POST'])
def update_menu_item(item_id):
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        return jsonify({'success': False, 'message': 'Access denied. Restaurant owners only.'})

    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'category', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'})

        # Update menu item
        result = restaurants.update_one(
            {
                'user_id': ObjectId(session['user_id']),
                'menu_items._id': ObjectId(item_id)
            },
            {'$set': {
                'menu_items.$.name': data['name'],
                'menu_items.$.description': data['description'],
                'menu_items.$.category': data['category'],
                'menu_items.$.price': float(data['price']),
                'menu_items.$.image_url': data.get('image_url', ''),
                'menu_items.$.is_available': data.get('is_available', True)
            }}
        )

        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Menu item updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update menu item'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/restaurant/menu/delete/<item_id>', methods=['POST'])
def delete_menu_item(item_id):
    if 'user_id' not in session or session.get('user_type') != 'restaurant':
        return jsonify({'success': False, 'message': 'Access denied. Restaurant owners only.'})

    try:
        # Remove menu item
        result = restaurants.update_one(
            {'user_id': ObjectId(session['user_id'])},
            {'$pull': {'menu_items': {'_id': ObjectId(item_id)}}}
        )

        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Menu item deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete menu item'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/orders/<order_id>')
def view_order(order_id):
    if 'user_id' not in session:
        flash('Please login to view order details', 'error')
        return redirect(url_for('login'))

    try:
        # Get order details
        order = orders.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('view_orders'))

        # Check if user has permission to view this order
        if str(order['user_id']) != session['user_id'] and session.get('user_type') != 'restaurant':
            flash('You do not have permission to view this order', 'error')
            return redirect(url_for('view_orders'))

        # Get restaurant details
        restaurant = restaurants.find_one({'_id': order['restaurant_id']})
        
        # Format dates
        order['created_at'] = order['created_at'].strftime('%B %d, %Y %I:%M %p')
        order['updated_at'] = order['updated_at'].strftime('%B %d, %Y %I:%M %p')

        return render_template('order_details.html', order=order, restaurant=restaurant)

    except Exception as e:
        flash(f'Error retrieving order details: {str(e)}', 'error')
        return redirect(url_for('view_orders'))

@app.route('/orders/<order_id>/details')
def get_order_details(order_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to view order details'})

    try:
        # Get order details
        order = orders.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})

        # Check if user has permission to view this order
        if str(order['user_id']) != session['user_id'] and session.get('user_type') != 'restaurant':
            return jsonify({'success': False, 'message': 'You do not have permission to view this order'})

        # If restaurant user, verify the order belongs to their restaurant
        if session.get('user_type') == 'restaurant':
            restaurant = restaurants.find_one({'user_id': ObjectId(session['user_id'])})
            if not restaurant or order['restaurant_id'] != restaurant['_id']:
                return jsonify({'success': False, 'message': 'Order not found'})

        # Format dates
        order['created_at'] = order['created_at'].strftime('%B %d, %Y %I:%M %p')
        order['updated_at'] = order['updated_at'].strftime('%B %d, %Y %I:%M %p')
        
        # Convert ObjectId to string for JSON serialization
        order['_id'] = str(order['_id'])
        order['user_id'] = str(order['user_id'])
        order['restaurant_id'] = str(order['restaurant_id'])

        return jsonify({
            'success': True,
            'order': order
        })

    except Exception as e:
        print('Error fetching order details:', str(e))
        return jsonify({'success': False, 'message': f'Error fetching order details: {str(e)}'})

@app.route('/orders/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to cancel the order'})

    try:
        # Get order details
        order = orders.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})

        # Check if user has permission to cancel this order
        if str(order['user_id']) != session['user_id']:
            return jsonify({'success': False, 'message': 'You do not have permission to cancel this order'})

        # Check if order can be cancelled (only pending orders can be cancelled)
        if order['status'] != 'pending':
            return jsonify({'success': False, 'message': 'Only pending orders can be cancelled'})

        # Update order status
        orders.update_one(
            {'_id': ObjectId(order_id)},
            {
                '$set': {
                    'status': 'cancelled',
                    'updated_at': datetime.datetime.now()
                }
            }
        )

        return jsonify({'success': True, 'message': 'Order cancelled successfully'})

    except Exception as e:
        print('Error cancelling order:', str(e))
        return jsonify({'success': False, 'message': f'Failed to cancel order: {str(e)}'})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create indexes
    users.create_index('email', unique=True)
    restaurants.create_index([('name', 'text'), ('cuisine_type', 'text')])
    
    print("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
