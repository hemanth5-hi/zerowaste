import random
from flask import Flask, render_template, request, jsonify, redirect, url_for # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from datetime import datetime
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user # type: ignore

# Initialize Flask app
app = Flask(__name__, template_folder='../frontend', static_folder='../frontend')

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    food_saved = db.Column(db.Integer, default=0)
    co2_saved = db.Column(db.Float, default=0.0)

class FoodListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    contact = db.Column(db.String(50), nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_claimed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Helper Functions
def update_statistics():
    stats = {
        'total_listings': FoodListing.query.count(),
        'claimed_listings': FoodListing.query.filter_by(is_claimed=True).count(),
        'active_listings': FoodListing.query.filter_by(is_claimed=False).count(),
        'users_registered': User.query.count(),
        'estimated_food_saved': FoodListing.query.filter_by(is_claimed=True).count() * 5,  # 5kg per listing
        'estimated_co2_saved': FoodListing.query.filter_by(is_claimed=True).count() * 12.5  # 2.5kg CO2 per kg food
    }
    
    # Save to JSON file
    with open('static/data.json', 'w') as f:
        json.dump(stats, f)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
@app.route('/api/claims', methods=['POST'])
@login_required
def create_claim():
    data = request.json
    listing_id = data.get('listing_id')
    
    if not listing_id:
        return jsonify({"error": "Listing ID is required"}), 400
    
    listing = FoodListing.query.get(listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404
    
    if listing.is_claimed:
        return jsonify({"error": "This food has already been claimed"}), 400
    
    # Create claim record
    new_claim = FoodClaim(
        listing_id=listing.id,
        claimant_id=current_user.id,
        claim_date=datetime.utcnow(),
        status='pending'
    )
    
    # Mark listing as claimed
    listing.is_claimed = True
    
    db.session.add(new_claim)
    db.session.commit()
    
    # Update statistics
    update_statistics()
    
    # Notify the donor
    donor = User.query.get(listing.user_id)
    # (In a real app, you would send an email/notification here)
    
    return jsonify({
        "message": "Food claimed successfully",
        "claim": {
            "id": new_claim.id,
            "listing_title": listing.title,
            "donor_contact": listing.contact,
            "status": new_claim.status
        }
    }), 201

@app.route('/api/claims', methods=['GET'])
@login_required
def get_user_claims():
    claims = FoodClaim.query.filter_by(claimant_id=current_user.id).all()
    claims_data = []
    
    for claim in claims:
        listing = FoodListing.query.get(claim.listing_id)
        donor = User.query.get(listing.user_id)
        
        claims_data.append({
            "id": claim.id,
            "listing_id": claim.listing_id,
            "title": listing.title,
            "quantity": listing.quantity,
            "expiry_date": listing.expiry_date,
            "donor_name": donor.username,
            "donor_contact": listing.contact,
            "location": listing.location,
            "claim_date": claim.claim_date.strftime("%Y-%m-%d %H:%M:%S"),
            "status": claim.status,
            "latitude": listing.latitude,
            "longitude": listing.longitude
        })
    
    return jsonify(claims_data)

@app.route('/api/claims/<int:claim_id>/complete', methods=['PUT'])
@login_required
def complete_claim(claim_id):
    claim = FoodClaim.query.get(claim_id)
    
    if not claim:
        return jsonify({"error": "Claim not found"}), 404
    
    if claim.claimant_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    claim.status = 'completed'
    db.session.commit()
    
    return jsonify({"message": "Claim marked as completed"})

# Add to your models
class FoodClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('food_listing.id'), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    claim_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled

@app.route('/api/listings', methods=['GET', 'POST'])
def handle_listings():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
            
        data = request.json
        new_listing = FoodListing(
            title=data['title'],
            description=data['description'],
            quantity=data['quantity'],
            expiry_date=data['expiry_date'],
            location=data['location'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            contact=data['contact'],
            user_id=current_user.id
        )
        db.session.add(new_listing)
        db.session.commit()
        
        update_statistics()
        return jsonify({"message": "Listing created successfully", "id": new_listing.id}), 201
    
    listings = FoodListing.query.filter_by(is_claimed=False).all()
    listings_data = []
    for listing in listings:
        listings_data.append({
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'quantity': listing.quantity,
            'expiry_date': listing.expiry_date,
            'location': listing.location,
            'latitude': listing.latitude,
            'longitude': listing.longitude,
            'contact': listing.contact,
            'posted_date': listing.posted_date.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(listings_data)

@app.route('/api/listings/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def handle_listing(id):
    listing = FoodListing.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'quantity': listing.quantity,
            'expiry_date': listing.expiry_date,
            'location': listing.location,
            'latitude': listing.latitude,
            'longitude': listing.longitude,
            'contact': listing.contact,
            'posted_date': listing.posted_date.strftime("%Y-%m-%d %H:%M:%S"),
            'is_claimed': listing.is_claimed
        })
# Removed duplicate function definition
    
    elif request.method == 'PUT':
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
            
        data = request.json
        listing.is_claimed = data.get('is_claimed', listing.is_claimed)
        db.session.commit()
        
        if listing.is_claimed:
            # Update user stats
            user = User.query.get(listing.user_id)
            if user:
                user.food_saved += 5  # Assuming 5kg per listing
                user.co2_saved += 12.5  # Assuming 2.5kg CO2 per kg food
                db.session.commit()
            
            update_statistics()
        
        return jsonify({"message": "Listing updated successfully"})
    
    elif request.method == 'DELETE':
        if not current_user.is_authenticated or current_user.id != listing.user_id:
            return jsonify({"error": "Unauthorized"}), 403
            
        db.session.delete(listing)
        db.session.commit()
        update_statistics()
        return jsonify({"message": "Listing deleted successfully"})

@app.route('/api/statistics')
def get_statistics():
    try:
        with open('static/data.json') as f:
            stats = json.load(f)
        return jsonify(stats)
    except FileNotFoundError:
        return jsonify({"error": "Statistics not available"}), 404

# Authentication Routes
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password, data['password']):
        login_user(user)
        return jsonify({"message": "Login successful"})
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 400
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=generate_password_hash(data['password'], method='sha256')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "Registration successful"}), 201
# Add these new routes to your existing Flask app

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'address', 'city', 'state', 'zip_code']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 400

    # Geocode address to get coordinates
    try:
        full_address = f"{data['address']}, {data['city']}, {data['state']} {data['zip_code']}"
        geocode_result = geocode_address(full_address)
        
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=generate_password_hash(data['password']),
            address=data['address'],
            city=data['city'],
            state=data['state'],
            zip_code=data['zip_code'],
            latitude=geocode_result['lat'],
            longitude=geocode_result['lng']
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "message": "Registration successful",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def geocode_address(address):
    # Mock function - replace with actual geocoding service
    # In production, use Google Maps Geocoding API or similar
    return {
        "lat": 17.2095462 + (random.random() - 0.5) * 0.01,
        "lng": 78.6186294 + (random.random() - 0.5) * 0.01
    }

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    login_user(user)
    
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "address": user.address,
            "city": user.city,
            "state": user.state,
            "zip_code": user.zip_code
        }
    }), 200

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
