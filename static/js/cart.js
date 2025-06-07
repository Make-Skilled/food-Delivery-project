// Cart management functions
function getCartItems() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
}

function saveCartItems(items) {
    localStorage.setItem('cart', JSON.stringify(items));
}

function updateCartDisplay() {
    const cartItems = getCartItems();
    const cartItemsList = document.getElementById('cart-items-list');
    const emptyCart = document.getElementById('empty-cart');
    const cartItemsCount = document.getElementById('cart-items-count');
    const checkoutBtn = document.getElementById('checkout-btn');

    // Update cart count
    cartItemsCount.textContent = `${cartItems.length} item${cartItems.length !== 1 ? 's' : ''}`;

    if (cartItems.length === 0) {
        emptyCart.classList.remove('hidden');
        cartItemsList.classList.add('hidden');
        return;
    }

    // Show cart items and hide empty message
    emptyCart.classList.add('hidden');
    cartItemsList.classList.remove('hidden');

    // Generate cart items HTML
    cartItemsList.innerHTML = cartItems.map((item, index) => `
        <div class="p-6 border-b border-gray-200 last:border-b-0">
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <h3 class="text-lg font-medium text-gray-900">${item.name}</h3>
                    <p class="text-gray-600">₹${item.price.toFixed(2)} × ${item.quantity}</p>
                    <p class="text-sm text-gray-500">Subtotal: ₹${(item.price * item.quantity).toFixed(2)}</p>
                </div>
                <div class="flex items-center space-x-4">
                    <div class="flex items-center border border-gray-300 rounded-lg">
                        <button type="button" onclick="updateItemQuantity(${index}, ${item.quantity - 1})"
                                class="px-3 py-1 text-gray-600 hover:bg-gray-100 transition-colors">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="px-3 py-1 border-x border-gray-300">${item.quantity}</span>
                        <button type="button" onclick="updateItemQuantity(${index}, ${item.quantity + 1})"
                                class="px-3 py-1 text-gray-600 hover:bg-gray-100 transition-colors">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <button type="button" onclick="removeItem(${index})"
                            class="text-red-600 hover:text-red-800 transition-colors">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    updateTotals();
}

function updateItemQuantity(index, newQuantity) {
    if (newQuantity < 1) {
        removeItem(index);
        return;
    }

    const cartItems = getCartItems();
    cartItems[index].quantity = newQuantity;
    saveCartItems(cartItems);
    updateCartDisplay();
    showNotification('Cart updated', 'success');
}

function removeItem(index) {
    const cartItems = getCartItems();
    cartItems.splice(index, 1);
    saveCartItems(cartItems);
    updateCartDisplay();
    showNotification('Item removed from cart', 'success');
}

function clearCart() {
    localStorage.removeItem('cart');
    updateCartDisplay();
    showNotification('Cart cleared', 'success');
}

function updateTotals() {
    const cartItems = getCartItems();
    const subtotal = cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const tax = subtotal * 0.05; // 5% GST
    const total = subtotal + tax;

    document.getElementById('subtotal').textContent = `₹${subtotal.toFixed(2)}`;
    document.getElementById('tax').textContent = `₹${tax.toFixed(2)}`;
    document.getElementById('total').textContent = `₹${total.toFixed(2)}`;
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg text-white ${
        type === 'success' ? 'bg-green-600' :
        type === 'error' ? 'bg-red-600' :
        type === 'warning' ? 'bg-yellow-600' :
        'bg-blue-600'
    }`;
    notification.textContent = message;

    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function addToCart(itemId, name, price, restaurantId) {
    const cartItems = getCartItems();
    
    // Check if item already exists in cart
    const existingItemIndex = cartItems.findIndex(item => item.id === itemId);
    
    if (existingItemIndex !== -1) {
        // Update quantity if item exists
        cartItems[existingItemIndex].quantity += 1;
    } else {
        // Add new item if it doesn't exist
        cartItems.push({
            id: itemId,
            name: name,
            price: parseFloat(price),
            quantity: 1,
            restaurant_id: restaurantId
        });
    }
    
    saveCartItems(cartItems);
    updateCartDisplay();
    showNotification('Item added to cart', 'success');
}

function placeOrder() {
    const deliveryAddress = document.getElementById('delivery-address').value.trim();
    const specialInstructions = document.getElementById('special-instructions').value.trim();
    
    if (!deliveryAddress) {
        showNotification('Please enter a delivery address', 'error');
        return;
    }

    const cartItems = getCartItems();
    if (cartItems.length === 0) {
        showNotification('Your cart is empty', 'error');
        return;
    }

    const subtotal = cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const tax = subtotal * 0.05;
    const total = subtotal + tax;

    const orderData = {
        items: cartItems,
        delivery_address: deliveryAddress,
        special_instructions: specialInstructions,
        subtotal: subtotal,
        tax: tax,
        total: total
    };

    fetch('/place_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.removeItem('cart');
            showNotification('Order placed successfully!', 'success');
            setTimeout(() => {
                window.location.href = `/orders/${data.order_id}`;
            }, 1500);
        } else {
            showNotification(data.message || 'Failed to place order', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to place order', 'error');
    });
}

// Initialize cart display when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateCartDisplay();

    // Add event listeners
    const checkoutBtn = document.getElementById('checkout-btn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', placeOrder);
    }

    // Add to cart buttons in restaurant menu
    document.querySelectorAll('[data-add-to-cart]').forEach(button => {
        button.addEventListener('click', (e) => {
            const { itemId, name, price, restaurantId } = e.target.dataset;
            addToCart(itemId, name, parseFloat(price), restaurantId);
        });
    });
}); 