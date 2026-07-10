from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from functools import wraps
from database.database import get_user_by_username
from werkzeug.security import check_password_hash

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to ensure route is only accessed by logged in users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login authentication."""
    # If already logged in, go to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("All fields are required.", "danger")
            return render_template('login.html')
            
        user = get_user_by_username(username)
        
        if user and check_password_hash(user['password'], password):
            # Establish session parameters
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Clear session data and redirect to login page."""
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('auth.login'))
