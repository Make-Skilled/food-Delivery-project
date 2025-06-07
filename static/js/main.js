// Main JavaScript for Food Delivery App

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeNavigation();
    initializeCart();
    initializeAnimations();
    initializeTooltips();
    initializeFormValidation();
});

// Navigation functionality
function initializeNavigation() {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Active navigation highlighting
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const currentPath = window.location.pathname;

    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Cart functionality
function initializeCart() {
    // Cart state management
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    updateCartCount();

    // Add to cart function
    window.addToCart = function(itemId, name, price, restaurantId) {
        const existingItem = cart.find(item => item.id === itemId);

        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({
                id: itemId,
                name: name,
                price: price,
                quantity: 1,
                restaurantId: restaurantId
            });
        }

        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartCount();
        showNotification('Item added to cart!', 'success');
    };

    // Remove from cart function
    window.removeFromCart = function(itemId) {
        cart = cart.filter(item => item.id !== itemId);
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartCount();
        showNotification('Item removed from cart!', 'info');
    };

    // Update cart quantity
    window.updateCartQuantity = function(itemId, quantity) {
        const item = cart.find(item => item.id === itemId);
        if (item) {
            if (quantity <= 0) {
                removeFromCart(itemId);
            } else {
                item.quantity = quantity;
                localStorage.setItem('cart', JSON.stringify(cart));
                updateCartCount();
            }
        }
    };

    // Update cart count display
    function updateCartCount() {
        const cartCountElement = document.getElementById('cart-count');
        if (cartCountElement) {
            const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
            cartCountElement.textContent = totalItems;
            if (totalItems > 0) {
                cartCountElement.classList.remove('hidden');
            } else {
                cartCountElement.classList.add('hidden');
            }
        }
    }

    // Get cart total
    window.getCartTotal = function() {
        return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    };

    // Clear cart
    window.clearCart = function() {
        cart = [];
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartCount();
    };

    // Get cart items
    window.getCartItems = function() {
        return cart;
    };
}

// Animation functionality
function initializeAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    // Observe elements for animation
    document.querySelectorAll('.card, .feature-item').forEach(el => {
        observer.observe(el);
    });

    // Add loading animation to buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
                submitBtn.disabled = true;

                // Re-enable button after 3 seconds (in case of errors)
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 3000);
            }
        });
    });
}

// Initialize tooltips
function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Form validation
function initializeFormValidation() {
    // Custom validation for all forms
    const forms = document.querySelectorAll('.needs-validation');

    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Real-time validation feedback
    document.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('blur', function() {
            if (this.checkValidity()) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        'bg-blue-500'
    } text-white`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            <span class="mr-2">
                ${type === 'success' ? '<i class="fas fa-check-circle"></i>' :
                  type === 'error' ? '<i class="fas fa-exclamation-circle"></i>' :
                  '<i class="fas fa-info-circle"></i>'}
            </span>
            <p>${message}</p>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    if (searchInput) {
        let searchTimeout;

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performSearch(query);
                }, 300);
            } else {
                clearSearchResults();
            }
        });
    }
}

function performSearch(query) {
    // This would typically make an AJAX call to the server
    // For now, we'll implement client-side filtering
    const restaurantCards = document.querySelectorAll('.restaurant-card');
    let hasResults = false;

    restaurantCards.forEach(card => {
        const restaurantName = card.querySelector('.card-title').textContent.toLowerCase();
        const cuisine = card.dataset.cuisine || '';

        if (restaurantName.includes(query.toLowerCase()) || cuisine.includes(query.toLowerCase())) {
            card.style.display = 'block';
            hasResults = true;
        } else {
            card.style.display = 'none';
        }
    });

    // Show no results message if needed
    const noResults = document.getElementById('noResults');
    if (noResults) {
        noResults.style.display = hasResults ? 'none' : 'block';
    }
}

function clearSearchResults() {
    const restaurantCards = document.querySelectorAll('.restaurant-card');
    restaurantCards.forEach(card => {
        card.style.display = 'block';
    });

    const noResults = document.getElementById('noResults');
    if (noResults) {
        noResults.style.display = 'none';
    }
}

// Confirm delivery function
window.confirmDelivery = function(orderId) {
    if (!confirm('Are you sure you want to confirm the delivery?')) {
        return;
    }

    fetch(`/orders/${orderId}/confirm_delivery`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Delivery confirmed successfully!', 'success');
            // Update the UI to reflect the confirmed status
            const orderElement = document.querySelector(`button[onclick="confirmDelivery('${orderId}')"]`)
                .closest('li');
            
            if (orderElement) {
                // Update status badge
                const statusBadge = orderElement.querySelector('.rounded-full');
                statusBadge.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800';
                statusBadge.textContent = 'Delivered';
                
                // Remove confirm button
                const confirmButton = orderElement.querySelector(`button[onclick="confirmDelivery('${orderId}')"]`);
                confirmButton.remove();
            }
        } else {
            showNotification(data.message || 'Failed to confirm delivery', 'error');
        }
    })
    .catch(error => {
        console.error('Error confirming delivery:', error);
        showNotification('Failed to confirm delivery. Please try again.', 'error');
    });
};

// Order Management Functions
window.updateOrderStatus = function(orderId, status) {
    fetch(`/restaurant/order/${orderId}/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'status': status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message using notification system
            showNotification(data.message, 'success');
            
            // Update the status badge
            const statusBadge = document.querySelector(`select[onchange="updateOrderStatus('${orderId}', this.value)"]`)
                .closest('li')
                .querySelector('.rounded-full');
            
            // Update badge color and text
            const displayStatus = status === 'delivered' ? 'awaiting_confirmation' : status;
            statusBadge.className = `px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                displayStatus === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                displayStatus === 'preparing' ? 'bg-blue-100 text-blue-800' :
                displayStatus === 'ready' ? 'bg-purple-100 text-purple-800' :
                displayStatus === 'awaiting_confirmation' ? 'bg-orange-100 text-orange-800' :
                displayStatus === 'delivered' ? 'bg-green-100 text-green-800' :
                'bg-red-100 text-red-800'
            }`;
            statusBadge.textContent = displayStatus === 'awaiting_confirmation' ? 'Awaiting Confirmation' : 
                                    displayStatus.charAt(0).toUpperCase() + displayStatus.slice(1);

            // If status is awaiting_confirmation or cancelled, remove the select element
            if (displayStatus === 'awaiting_confirmation' || status === 'cancelled') {
                const selectContainer = document.querySelector(`select[onchange="updateOrderStatus('${orderId}', this.value)"]`).parentElement;
                selectContainer.remove();
            }
        } else {
            showNotification(data.message || 'Failed to update order status', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update order status', 'error');
    });
};

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatTime(minutes) {
    if (minutes < 60) {
        return `${minutes} min`;
    } else {
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}h ${remainingMinutes}m`;
    }
}

// AJAX helper function
function makeRequest(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: data ? JSON.stringify(data) : null
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .catch(error => {
        console.error('Request failed:', error);
        showNotification('An error occurred. Please try again.', 'danger');
        throw error;
    });
}

// Export functions for global use
window.showNotification = showNotification;
window.formatCurrency = formatCurrency;
window.formatTime = formatTime;
window.makeRequest = makeRequest;
