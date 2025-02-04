from flask import Flask, request, jsonify, render_template, session, redirect, send_file
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import pytz
import logging
import secrets
import functools
import re
import csv
import io
import validators  # New import for URL validation

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
bcrypt = Bcrypt(app)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='college_connect.log'
)
logger = logging.getLogger(__name__)

# MongoDB Connection
def get_db_connection():
    try:
        # Consider using environment variables for sensitive credentials
        uri = "mongodb+srv://gcloudsignup:pass@collegeconnect.u4kry.mongodb.net/?retryWrites=true&w=majority&appName=CollegeConnect"
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client['collegeconnect']
    except Exception as e:
        logger.error(f"Database Connection Error: {e}")
        return None

# Enhanced College Registration Validation
def validate_college_registration(data):
    # Validate required fields
    required_fields = ['collegeName', 'emailDomains', 'address', 'contactPerson', 'website']
    if not all(field in data for field in required_fields):
        return False, 'Missing required fields'

    # Validate website URL
    if not validators.url(data['website']):
        return False, 'Invalid website URL'

    # Validate email domains
    for domain in data['emailDomains']:
        if not re.match(r'^@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            return False, 'Invalid email domain format'

    # Additional checks can be added here
    return True, 'Valid registration data'

@app.route('/api/college/register', methods=['POST'])
def register_college():
    db = get_db_connection()
    data = request.json
    
    # Validate input
    is_valid, validation_message = validate_college_registration(data)
    if not is_valid:
        return jsonify({'error': validation_message}), 400

    college = {
        'collegeName': data['collegeName'],
        'emailDomains': data['emailDomains'],
        'address': data['address'],
        'contactPerson': data['contactPerson'],
        'website': data['website'],
        'adminApproved': False,
        'rejected': False,
        'createdAt': datetime.now(pytz.utc),
        'updatedAt': datetime.now(pytz.utc)
    }

    try:
        # Check for existing college
        existing_college = db.colleges.find_one({
            '$or': [
                {'collegeName': data['collegeName']},
                {'website': data['website']}
            ]
        })
        
        if existing_college:
            return jsonify({'error': 'College already registered'}), 409

        college_id = db.colleges.insert_one(college).inserted_id
        logger.info(f"New College Registered: {data['collegeName']}")
        return jsonify({'message': 'College registered successfully', 'collegeId': str(college_id)}), 201
    except Exception as e:
        logger.error(f"College Registration Error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/college/list', methods=['GET'])
def get_colleges():
    db = get_db_connection()
    try:
        colleges = list(db.colleges.find())
        for college in colleges:
            college['_id'] = str(college['_id'])
        return jsonify(colleges), 200
    except Exception as e:
        logger.error(f"College List Retrieval Error: {e}")
        return jsonify({'error': 'Failed to retrieve colleges'}), 500

@app.route('/api/college/approve/<college_id>', methods=['PUT'])
def approve_college(college_id):
    db = get_db_connection()
    try:
        result = db.colleges.update_one(
            {'_id': ObjectId(college_id)},
            {'$set': {
                'adminApproved': True, 
                'rejected': False,
                'updatedAt': datetime.now(pytz.utc)
            }}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'College not found'}), 404
        
        logger.info(f"College Approved: {college_id}")
        return jsonify({'message': 'College approved successfully'}), 200
    except Exception as e:
        logger.error(f"College Approval Error: {e}")
        return jsonify({'error': 'Approval failed'}), 500

@app.route('/api/college/reject/<college_id>', methods=['PUT'])
def reject_college(college_id):
    db = get_db_connection()
    try:
        result = db.colleges.update_one(
            {'_id': ObjectId(college_id)},
            {'$set': {
                'adminApproved': False, 
                'rejected': True,
                'updatedAt': datetime.now(pytz.utc)
            }}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'College not found'}), 404
        
        logger.info(f"College Rejected: {college_id}")
        return jsonify({'message': 'College rejected successfully'}), 200
    except Exception as e:
        logger.error(f"College Rejection Error: {e}")
        return jsonify({'error': 'Rejection failed'}), 500

# Advanced Reporting
@app.route('/admin/export/colleges', methods=['GET'])
def export_colleges():
    db = get_db_connection()
    colleges = list(db.colleges.find())
    
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # CSV Headers
    csv_writer.writerow([
        'College Name', 'Email Domains', 'Address', 
        'Contact Person', 'Website', 'Status', 
        'Registration Date'
    ])
    
    for college in colleges:
        csv_writer.writerow([
            college['collegeName'], 
            ', '.join(college['emailDomains']), 
            college['address'],
            college.get('contactPerson', 'N/A'),
            college['website'],
            'Approved' if college['adminApproved'] else 'Pending' if not college.get('rejected', False) else 'Rejected',
            college['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')), 
        mimetype='text/csv',
        as_attachment=True,
        download_name='colleges_report.csv'
    )

# Dashboard Statistics
@app.route('/admin/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    db = get_db_connection()
    stats = {
        'total_colleges': db.colleges.count_documents({}),
        'approved_colleges': db.colleges.count_documents({'adminApproved': True}),
        'pending_colleges': db.colleges.count_documents({'adminApproved': False, 'rejected': False}),
        'rejected_colleges': db.colleges.count_documents({'rejected': True})
    }
    return jsonify(stats), 200

# Frontend Routes
@app.route('/')
def home():
    return render_template('register_college.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)