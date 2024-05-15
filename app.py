import re                                                                                                                                                                               │
import logging                                                                                                                                                                          │
from datetime import datetime                                                                                                                                                           │
from typing import Optional, Dict, List, Tuple                                                                                                                                          │
                                                                                                                                                                                        │
import sqlalchemy as db                                                                                                                                                                 │
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime                                                                                                             │
from sqlalchemy.orm import relationship, Session                                                                                                                                        │
from sqlalchemy.ext.declarative import declarative_base                                                                                                                                 │
                                                                                                                                                                                        │
from flask import Flask, request, jsonify                                                                                                                                               │
from flask_jwt_extended import JWTManager, jwt_required, create_access_token                                                                                                            │
                                                                                                                                                                                        │
# Set up logging                                                                                                                                                                        │
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')                                                                                             │
                                                                                                                                                                                        │
# Database setup                                                                                                                                                                        │
engine = db.create_engine('sqlite:///receipts.db')                                                                                                                                      │
Base = declarative_base()                                                                                                                                                               │
                                                                                                                                                                                        │
# Define database models                                                                                                                                                                │
class User(Base):                                                                                                                                                                       │
    __tablename__ = 'users'                                                                                                                                                             │
                                                                                                                                                                                        │
    id = Column(Integer, primary_key=True)                                                                                                                                              │
    username = Column(String, nullable=False, unique=True)                                                                                                                              │
    password = Column(String, nullable=False)                                                                                                                                           │
                                                                                                                                                                                        │
    receipts = relationship('Receipt', back_populates='user')                                                                                                                           │
                                                                                                                                                                                        │
class Receipt(Base):                                                                                                                                                                    │
    __tablename__ = 'receipts'                                                                                                                                                          │
                                                                                                                                                                                        │
    id = Column(Integer, primary_key=True)                                                                                                                                              │
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)                                                                                                                   │
    merchant = Column(String, nullable=False)                                                                                                                                           │
    date = Column(DateTime, nullable=False)                                                                                                                                             │
    total = Column(Float, nullable=False)                                                                                                                                               │
                                                                                                                                                                                        │
    user = relationship('User', back_populates='receipts')                                                                                                                              │
    items = relationship('Item', back_populates='receipt')                                                                                                                              │
                                                                                                                                                                                        │
class Item(Base):                                                                                                                                                                       │
    __tablename__ = 'items'                                                                                                                                                             │
                                                                                                                                                                                        │
    id = Column(Integer, primary_key=True)                                                                                                                                              │
    receipt_id = Column(Integer, ForeignKey('receipts.id'), nullable=False)                                                                                                             │
    name = Column(String, nullable=False)                                                                                                                                               │
    quantity = Column(String, nullable=True)                                                                                                                                            │
    price = Column(Float, nullable=False)                                                                                                                                               │
                                                                                                                                                                                        │
    receipt = relationship('Receipt', back_populates='items')                                                                                                                           │
                                                                                                                                                                                        │
Base.metadata.create_all(engine)                                                                                                                                                        │
                                                                                                                                                                                        │
# Data validation and normalization                                                                                                                                                     │
def validate_receipt_data(data: Dict) -> Optional[Dict]:                                                                                                                                │
    errors = []                                                                                                                                                                         │
                                                                                                                                                                                        │
    # Validate merchant                                                                                                                                                                 │
    merchant = data.get('merchant')                                                                                                                                                     │
    if not merchant or not isinstance(merchant, str):                                                                                                                                   │
        errors.append('Invalid merchant name')                                                                                                                                          │
    else:                                                                                                                                                                               │
        data['merchant'] = merchant.strip().title()                                                                                                                                     │
                                                                                                                                                                                        │
    # Validate date                                                                                                                                                                     │
    date_str = data.get('date')                                                                                                                                                         │
    if not date_str or not isinstance(date_str, str):                                                                                                                                   │
        errors.append('Invalid date format')                                                                                                                                            │
    else:                                                                                                                                                                               │
        try:                                                                                                                                                                            │
            data['date'] = datetime.strptime(date_str, '%Y-%m-%d').date()                                                                                                               │
        except ValueError:                                                                                                                                                              │
            errors.append('Invalid date format')                                                                                                                                        │
                                                                                                                                                                                        │
    # Validate total                                                                                                                                                                    │
    total = data.get('total')                                                                                                                                                           │
    if not total or not isinstance(total, (int, float)):                                                                                                                                │
        errors.append('Invalid total amount')                                                                                                                                           │
                                                                                                                                                                                        │
    # Validate items                                                                                                                                                                    │
    items = data.get('items', [])                                                                                                                                                       │
    for item in items:                                                                                                                                                                  │
        name = item.get('name')                                                                                                                                                         │
        if not name or not isinstance(name, str):                                                                                                                                       │
            errors.append('Invalid item name')                                                                                                                                          │
        else:                                                                                                                                                                           │
            item['name'] = name.strip()                                                                                                                                                 │
                                                                                                                                                                                        │
        quantity = item.get('quantity')                                                                                                                                                 │
        if quantity and not isinstance(quantity, str):                                                                                                                                  │
            errors.append('Invalid item quantity')                                                                                                                                      │
        else:                                                                                                                                                                           │
            item['quantity'] = quantity.strip() if quantity else None                                                                                                                   │
                                                                                                                                                                                        │
        price = item.get('price')                                                                                                                                                       │
        if not price or not isinstance(price, (int, float)):                                                                                                                            │
            errors.append('Invalid item price')                                                                                                                                         │
                                                                                                                                                                                        │
    if errors:                                                                                                                                                                          │
        logging.error(f'Validation errors: {errors}')                                                                                                                                   │
        return None                                                                                                                                                                     │
                                                                                                                                                                                        │
    return data                                                                                                                                                                         │
                                                                                                                                                                                        │
# Database operations                                                                                                                                                                   │
def save_receipt_data(data: Dict, user_id: int) -> Optional[Receipt]:                                                                                                                   │
    session = Session(bind=engine)                                                                                                                                                      │
                                                                                                                                                                                        │
    try:                                                                                                                                                                                │
        merchant = data['merchant']                                                                                                                                                     │
        date = data['date']                                                                                                                                                             │
        total = data['total']                                                                                                                                                           │
        items = data.get('items', [])                                                                                                                                                   │
                                                                                                                                                                                        │
        receipt = Receipt(user_id=user_id, merchant=merchant, date=date, total=total)                                                                                                   │
        session.add(receipt)                                                                                                                                                            │
        session.flush()  # Get the receipt ID                                                                                                                                           │
                                                                                                                                                                                        │
        for item in items:                                                                                                                                                              │
            name = item['name']                                                                                                                                                         │
            quantity = item.get('quantity')                                                                                                                                             │
            price = item['price']                                                                                                                                                       │
            item_obj = Item(receipt_id=receipt.id, name=name, quantity=quantity, price=price)                                                                                           │
            session.add(item_obj)                                                                                                                                                       │
                                                                                                                                                                                        │
        session.commit()                                                                                                                                                                │
        return receipt                                                                                                                                                                  │
    except Exception as e:                                                                                                                                                              │
        logging.error(f'Error saving receipt data: {e}')                                                                                                                                │
        session.rollback()                                                                                                                                                              │
    finally:                                                                                                                                                                            │
        session.close()                                                                                                                                                                 │
                                                                                                                                                                                        │
    return None                                                                                                                                                                         │
                                                                                                                                                                                        │
# API setup                                                                                                                                                                             │
app = Flask(__name__)                                                                                                                                                                   │
app.config['JWT_SECRET_KEY'] = 'your-secret-key'                                                                                                                                        │
jwt = JWTManager(app)                                                                                                                                                                   │
                                                                                                                                                                                        │
@app.route('/register', methods=['POST'])                                                                                                                                               │
def register():                                                                                                                                                                         │
    data = request.get_json()                                                                                                                                                           │
    username = data.get('username')                                                                                                                                                     │
    password = data.get('password')                                                                                                                                                     │
                                                                                                                                                                                        │
    if not username or not password:                                                                                                                                                    │
        return jsonify({'error': 'Username and password are required'}), 400                                                                                                            │
                                                                                                                                                                                        │
    session = Session(bind=engine)                                                                                                                                                      │
    try:                                                                                                                                                                                │
        existing_user = session.query(User).filter_by(username=username).first()                                                                                                        │
        if existing_user:                                                                                                                                                               │
            return jsonify({'error': 'Username already exists'}), 400                                                                                                                   │
                                                                                                                                                                                        │
        user = User(username=username, password=password)                                                                                                                               │
        session.add(user)                                                                                                                                                               │
        session.commit()                                                                                                                                                                │
        return jsonify({'message': 'User registered successfully'}), 201                                                                                                                │
    except Exception as e:                                                                                                                                                              │
        logging.error(f'Error registering user: {e}')                                                                                                                                   │
        session.rollback()                                                                                                                                                              │
        return jsonify({'error': 'Internal server error'}), 500                                                                                                                         │
    finally:                                                                                                                                                                            │
        session.close()                                                                                                                                                                 │
                                                                                                                                                                                        │
@app.route('/login', methods=['POST'])                                                                                                                                                  │
def login():                                                                                                                                                                            │
    data = request.get_json()                                                                                                                                                           │
    username = data.get('username')                                                                                                                                                     │
    password = data.get('password')                                                                                                                                                     │
                                                                                                                                                                                        │
    if not username or not password:                                                                                                                                                    │
        return jsonify({'error': 'Username and password are required'}), 400                                                                                                            │
                                                                                                                                                                                        │
    session = Session(bind=engine)                                                                                                                                                      │
    try:                                                                                                                                                                                │
        user = session.query(User).filter_by(username=username, password=password).first()                                                                                              │
        if not user:                                                                                                                                                                    │
            return jsonify({'error': 'Invalid username or password'}), 401                                                                                                              │
                                                                                                                                                                                        │
        access_token = create_access_token(identity=user.id)                                                                                                                            │
        return jsonify({'access_token': access_token}), 200                                                                                                                             │
    except Exception as e:                                                                                                                                                              │
        logging.error(f'Error logging in user: {e}')                                                                                                                                    │
        return jsonify({'error': 'Internal server error'}), 500                                                                                                                         │
    finally:                                                                                                                                                                            │
        session.close()                                                                                                                                                                 │
                                                                                                                                                                                        │
@app.route('/receipts', methods=['POST'])                                                                                                                                               │
@jwt_required()                                                                                                                                                                         │
def upload_receipt():                                                                                                                                                                   │
    user_id = get_jwt_identity()                                                                                                                                                        │
    data = request.get_json()                                                                                                                                                           │
                                                                                                                                                                                        │
    validated_data = validate_receipt_data(data)                                                                                                                                        │
    if not validated_data:                                                                                                                                                              │
        return jsonify({'error': 'Invalid receipt data'}), 400                                                                                                                          │
                                                                                                                                                                                        │
    receipt = save_receipt_data(validated_data, user_id)                                                                                                                                │
    if not receipt:                                                                                                                                                                     │
        return jsonify({'error': 'Failed to save receipt data'}), 500                                                                                                                   │
                                                                                                                                                                                        │
    return jsonify({'message': 'Receipt uploaded successfully', 'receipt_id': receipt.id}), 201                                                                                         │
                                                                                                                                                                                        │
@app.route('/receipts/<int:receipt_id>', methods=['GET'])                                                                                                                               │
@jwt_required()                                                                                                                                                                         │
def get_receipt(receipt_id):                                                                                                                                                            │
    user_id = get_jwt_identity()                                                                                                                                                        │
    session = Session(bind=engine)                                                                                                                                                      │
                                                                                                                                                                                        │
    try:                                                                                                                                                                                │
        receipt = session.query(Receipt).filter_by(id=receipt_id, user_id=user_id).first()                                                                                              │
        if not receipt:                                                                                                                                                                 │
            return jsonify({'error': 'Receipt not found'}), 404                                                                                                                         │
                                                                                                                                                                                        │
        receipt_data = {                                                                                                                                                                │
            'merchant': receipt.merchant,                                                                                                                                               │
            'date': receipt.date.isoformat(),                                                                                                                                           │
            'total': float(receipt.total),                                                                                                                                              │
            'items': [                                                                                                                                                                  │
                {                                                                                                                                                                       │
                    'name': item.name,                                                                                                                                                  │
                    'quantity': item.quantity,                                                                                                                                          │
                    'price': float(item.price)                                                                                                                                          │
                }                                                                                                                                                                       │
                for item in receipt.items                                                                                                                                               │
            ]                                                                                                                                                                           │
        }                                                                                                                                                                               │
        return jsonify(receipt_data), 200                                                                                                                                               │
    except Exception as e:                                                                                                                                                              │
        logging.error(f'Error retrieving receipt data: {e}')                                                                                                                            │
        return jsonify({'error': 'Internal server error'}), 500                                                                                                                         │
    finally:                                                                                                                                                                            │
        session.close()                                                                                                                                                                 │
                                                                                                                                                                                        │
# Helper function to get JWT identity                                                                                                                                                   │
def get_jwt_identity():                                                                                                                                                                 │
    return jwt.get_jwt_identity()                                                                                                                                                       │
                                                                                                                                                                                        │
@app.route('/receipts', methods=['GET'])
@jwt_required()
def get_receipts():
    user_id = get_jwt_identity()
    session = Session(bind=engine)
    receipts = session.query(Receipt).filter(Receipt.user_id == user_id).all()
    session.close()
    return jsonify([receipt.serialize() for receipt in receipts])

@app.route('/receipts/<int:receipt_id>', methods=['GET'])
@jwt_required()
def get_receipt_details(receipt_id):
    user_id = get_jwt_identity()
    session = Session(bind=engine)
    receipt = session.query(Receipt).filter(Receipt.id == receipt_id, Receipt.user_id == user_id).first()
    session.close()
    if receipt:
        return jsonify(receipt.serialize())
    else:
        return jsonify({'message': 'Receipt not found'}), 404
    

from datetime import datetime

@app.route('/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    user_id = get_jwt_identity()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'message': 'Start date and end date are required'}), 400
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid date format, use YYYY-MM-DD'}), 400

    session = Session(bind=engine)
    expenses = session.query(Receipt).filter(
        Receipt.user_id == user_id,
        Receipt.date >= start_date,
        Receipt.date <= end_date
    ).all()
    session.close()

    # Summarize expenses by category
    summary = {}
    for receipt in expenses:
        category = receipt.category
        summary[category] = summary.get(category, 0) + receipt.total

    return jsonify(summary)

@app.route('/charts/expenses', methods=['GET'])
@jwt_required()
def get_expense_chart_data():
    user_id = get_jwt_identity()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'message': 'Start date and end date are required'}), 400
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid date format, use YYYY-MM-DD'}), 400

    session = Session(bind=engine)
    expenses = session.query(Receipt).filter(
        Receipt.user_id == user_id,
        Receipt.date >= start_date,
        Receipt.date <= end_date
    ).all()
    session.close()

    # Prepare data for chart
    chart_data = {}
    for receipt in expenses:
        category = receipt.category
        chart_data[category] = chart_data.get(category, 0) + receipt.total

    # Format data for chart rendering
    categories = list(chart_data.keys())
    values = [chart_data[category] for category in categories]

    return jsonify({'categories': categories, 'values': values})

if __name__ == '__main__':                                                                                                                                                              │
    app.run(debug=True)
