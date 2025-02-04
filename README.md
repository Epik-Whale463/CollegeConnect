# College Connect Application

## Overview
College Connect is a Flask-based web application for managing college registrations and connecting students with organizations. The application uses MongoDB for data storage and provides features for college and student registration, admin dashboard, and organization management.

## Prerequisites
- Python 3.7+
- pip
- MongoDB (local or MongoDB Atlas)
- Virtual Environment (recommended)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. MongoDB Configuration
- For MongoDB Atlas: Create a cluster and obtain connection string
- For local MongoDB: Use `mongodb://localhost:27017/`

### 5. Configuration
1. Update `main.py` with your MongoDB connection string
2. Set a secure secret key for Flask session management
3. Use environment variables for sensitive information

## Running the Application
```bash
python main.py
```
Access the application at: http://127.0.0.1:5000/

## Key Features
- College Registration
- Admin Dashboard
- Student Registration and Login
- Organization Management

## API Endpoints
- `/api/college/register`: Register new college
- `/api/college/list`: List colleges
- `/api/college/approve/<college_id>`: Approve college
- `/api/college/reject/<college_id>`: Reject college
- `/admin/dashboard/stats`: Get dashboard statistics
- `/admin/export/colleges`: Export college data

## Deployment Recommendations
- Use Gunicorn or uWSGI as WSGI server
- Configure Nginx as web server
- Secure MongoDB connection for production

## Future Development
- Implement robust authentication
- Add data validation
- Improve error handling
- Write comprehensive tests
- Enhance frontend user experience

## Contributing
Please read the contribution guidelines before submitting pull requests.

## License
[Specify your license here]