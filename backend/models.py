from datetime import datetime
from . import db

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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    food_saved = db.Column(db.Integer, default=0)
    co2_saved = db.Column(db.Float, default=0.0)