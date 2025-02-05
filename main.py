import jwt
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
import validators

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
bcrypt = Bcrypt(app)

# JWT Secret Key
JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"

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
        uri = "mongodb+srv://gcloudsignup:pass@collegeconnect.u4kry.mongodb.net/?retryWrites=true&w=majority&appName=CollegeConnect"
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client['collegeconnect']
    except Exception as e:
        logger.error(f"Database Connection Error: {e}")
        return None

db = get_db_connection()

# Generate JWT Token
def generate_jwt(user_id):
    payload = {
        "user_id": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# Middleware to Protect Routes
def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            payload = jwt.decode(token.split(" ")[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(*args, **kwargs)
    
    return decorated

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


# User Registration Route
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    required_fields = [
        "firstName", "lastName", "mobileNumber", 
        "rollNumber", "branch", "year", 
        "collegeEmail", "password", "githubLink", "collegeName"
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if not re.match(r"[^@]+@[^@]+\\.[^@]+", data["collegeEmail"]):
        return jsonify({"error": "Invalid email format"}), 400

    if not re.match(r"^\\d{10}$", data["mobileNumber"]):
        return jsonify({"error": "Invalid mobile number"}), 400

    if not validators.url(data["githubLink"]):
        return jsonify({"error": "Invalid GitHub URL"}), 400

    college = db.colleges.find_one({"collegeName": data["collegeName"]})
    if not college:
        return jsonify({"error": "College not found. Please register your college first."}), 404

    existing_user = db.users.find_one({"collegeEmail": data["collegeEmail"]})
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409

    hashed_password = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
    user = {
        "firstName": data["firstName"],
        "lastName": data["lastName"],
        "fullName": f"{data['firstName']} {data['lastName']}",
        "mobileNumber": data["mobileNumber"],
        "rollNumber": data["rollNumber"],
        "branch": data["branch"],
        "year": data["year"],
        "collegeEmail": data["collegeEmail"],
        "password": hashed_password,
        "githubLink": data["githubLink"],
        "collegeId": college["_id"],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "isActive": True,
        "lastLogin": None
    }
    try:
        user_id = db.users.insert_one(user).inserted_id
        token = generate_jwt(user_id)
        logger.info(f"New user registered: {data['collegeEmail']}")
        return jsonify({
            "message": "Registration successful",
            "token": token,
            "user": {
                "id": str(user_id),
                "fullName": user["fullName"],
                "email": user["collegeEmail"],
                "college": data["collegeName"]
            }
        }), 201
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.json
    required_fields = ["email", "password"]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing email or password"}), 400

    user = db.users.find_one({"collegeEmail": data["email"]})
    if not user or not bcrypt.check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_jwt(user["_id"])
    return render_template("student_dashboard.html", user=user), 200

# Get User Profile
@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile():
    user = db.users.find_one({"_id": ObjectId(request.user_id)}, {"password": 0})  # Exclude password field
    if not user:
        return jsonify({"error": "User not found"}), 404

    user["_id"] = str(user["_id"])
    return jsonify(user), 200

# Update User Profile
@app.route('/api/user/profile/update', methods=['PUT'])
@token_required
def update_profile():
    data = request.json
    update_fields = {key: value for key, value in data.items() if key in ["fullName", "skills", "bio", "socialLinks"]}

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    db.users.update_one({"_id": ObjectId(request.user_id)}, {"$set": update_fields})
    return jsonify({"message": "Profile updated successfully"}), 200

# Protected Route Example
@app.route('/api/protected', methods=['GET'])
@token_required
def protected_route():
    return jsonify({"message": "This is a protected route!"}), 200

# Frontend Routes
@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/register_college')
def register_college_page():
    return render_template('register_college.html')

@app.route('/register_student')
def register_student_page():
    return render_template('register_student.html')

@app.route('/login')
def login_page():
    return render_template('student_login.html')

if __name__ == '__main__':
    app.run(debug=True)