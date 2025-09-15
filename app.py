import os
import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, url_for, session, redirect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing processor with proper error handling
try:
    from processor import process_marksheet
    logger.info("✅ Processor module imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import processor: {e}")
    logger.error("Make sure processor.py is in the same directory")
    sys.exit(1)

# Flask setup with proper configuration
app = Flask(__name__)
CORS(app)  # Allow frontend fetch

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist and are writable
for directory in [UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR, TEMPLATES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

logger.info(f"✅ Directories verified/created - Upload: {UPLOAD_DIR}, Output: {OUTPUT_DIR}")

app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BASE_DIR}/marksheetpro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Google OAuth setup - Set to disabled for now
GOOGLE_CLIENT_ID = "disabled"
GOOGLE_CLIENT_SECRET = "disabled"

# Only create Google OAuth if credentials are provided
if GOOGLE_CLIENT_ID != "disabled" and GOOGLE_CLIENT_SECRET != "disabled":
    google_bp = make_google_blueprint(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scope=["profile", "email"],
        redirect_url="/auth/google/callback"
    )
    app.register_blueprint(google_bp, url_prefix="/login")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    profile_pic = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    uploads = db.relationship('UploadHistory', backref='user', lazy=True)

    @property
    def password(self):
        raise AttributeError("Password is not readable")

    @password.setter
    def password(self, password_plain):
        self.password_hash = generate_password_hash(password_plain)

    def verify_password(self, password_plain):
        if self.password_hash:
            return check_password_hash(self.password_hash, password_plain)
        return False

class UploadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    processed_filename = db.Column(db.String(255), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    marksheet_type = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    records_extracted = db.Column(db.Integer, nullable=True)

# Create tables and default admin user (Flask 2.2+ compatible)
def create_tables():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", email="admin@marksheetpro.com")
            admin.password = "admin123"
            db.session.add(admin)
            db.session.commit()
            logger.info("✅ Default admin user created")

# Utility functions
def current_user():
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None

def login_user(user):
    session["user_id"] = user.id
    session["username"] = user.username or user.email

def logout_user():
    session.clear()

# Routes
@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "Backend running"}

@app.route("/api/auth/login", methods=["POST"])
def login():
    """User login endpoint - UPDATED to allow username OR email login."""
    try:
        data = request.get_json() or {}
        username_or_email = data.get("username")  # Can be username or email
        password = data.get("password")
        
        logger.info(f"🔐 Login attempt for: '{username_or_email}'")

        if not username_or_email or not password:
            return jsonify({"success": False, "message": "Missing username/email or password"}), 400

        # UPDATED: Search by username OR email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user:
            logger.info(f"👤 Found user: {user.username} ({user.email})")
            if user.verify_password(password):
                login_user(user)
                logger.info(f"✅ Login successful for: {user.username}")
                return jsonify({
                    "success": True,
                    "status": "ok",
                    "user": {
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name
                    }
                })
            else:
                logger.warning(f"❌ Invalid password for user: {user.username}")
                return jsonify({"success": False, "message": "Invalid password"}), 401
        else:
            logger.warning(f"❌ No user found with username/email: '{username_or_email}'")
            return jsonify({"success": False, "message": "User not found"}), 401

    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return jsonify({"success": False, "message": "Login failed"}), 500

@app.route("/api/auth/register", methods=["POST"])
def register():
    """User registration endpoint - UPDATED with better logging."""
    try:
        data = request.get_json() or {}
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        
        logger.info(f"📝 Registration attempt - Username: '{username}', Email: '{email}'")
        
        # Validate input
        if not username or not email or not password:
            return jsonify({"success": False, "message": "Missing username, email, or password"}), 400
        
        # Check minimum password length
        if len(password) < 4:
            return jsonify({"success": False, "message": "Password must be at least 4 characters long"}), 400
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            logger.warning(f"❌ Username '{username}' already exists")
            return jsonify({"success": False, "message": "Username already taken"}), 409
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            logger.warning(f"❌ Email '{email}' already exists")
            return jsonify({"success": False, "message": "Email already registered"}), 409
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.password = password  # Password gets hashed automatically via the setter
        
        db.session.add(new_user)
        db.session.commit()
        
        # Verify user was saved
        saved_user = User.query.filter_by(username=username).first()
        if saved_user:
            logger.info(f"✅ User registered and verified - ID: {saved_user.id}, Username: '{username}', Email: '{email}'")
        else:
            logger.error(f"❌ User not found after registration!")
            return jsonify({"success": False, "message": "Registration failed - user not saved"}), 500
        
        return jsonify({
            "success": True, 
            "message": "Account created successfully! You can now login with your username or email."
        })
    
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Registration failed. Please try again."}), 500

@app.route("/api/auth/logout")
def logout():
    logout_user()
    return jsonify({"success": True, "status": "ok"})

@app.route("/api/auth/user")
def get_current_user():
    user = current_user()
    if user:
        return jsonify({
            "success": True,
            "user": {
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "profile_pic": user.profile_pic
            }
        })
    return jsonify({"success": False, "message": "Not authenticated"}), 401

# DEBUG ROUTE - Remove in production
@app.route("/api/debug/users")
def debug_users():
    """Debug route to see all users - REMOVE IN PRODUCTION"""
    try:
        users = User.query.all()
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "has_password": bool(user.password_hash),
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
            })
        return jsonify({"users": user_list, "total": len(user_list)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/debug/database-info")
def debug_database_info():
    """Debug route to check database status - REMOVE IN PRODUCTION"""
    try:
        with app.app_context():
            users = User.query.all()
            user_list = []
            for user in users:
                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "has_password_hash": bool(user.password_hash),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "full_name": user.full_name
                })
            
            return f"""
            <h1>Database Info</h1>
            <p><strong>Total Users:</strong> {len(user_list)}</p>
            <h2>All Users:</h2>
            <pre>{json.dumps(user_list, indent=2)}</pre>
            """
    except Exception as e:
        return f"<h1>Database Error</h1><p>{str(e)}</p>"

@app.route("/process/<marksheet_type>", methods=["POST"])
def process_marksheet_route(marksheet_type):
    """Handle file upload + OCR processing"""
    try:
        logger.info(f"Processing {marksheet_type} marksheet request")

        user = current_user()
        if not user:
            return jsonify({'success': False, 'message': 'Authentication required. Please login first.'}), 403

        if marksheet_type not in ['10th', '12th', 'semester']:
            return jsonify({'success': False, 'message': 'Invalid marksheet type specified.'}), 400

        file = request.files.get("uploaded_file")
        if not file or file.filename == '':
            logger.error("No file uploaded or filename empty")
            return jsonify({'success': False, 'message': 'No file uploaded.'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Allowed: pdf, jpg, jpeg, png'}), 400

        upload_id = str(uuid.uuid4())[:8]
        original_filename = secure_filename(file.filename)
        ext = Path(original_filename).suffix.lower()
        stored_filename = f"{upload_id}_{marksheet_type}{ext}"
        saved_path = UPLOAD_DIR / stored_filename

        file.save(saved_path)
        file_size = saved_path.stat().st_size

        df = process_marksheet(marksheet_type, str(saved_path))
        records_count = len(df)
        if records_count == 0:
            saved_path.unlink(missing_ok=True)
            return jsonify({'success': False, 'message': 'No data extracted.'}), 422

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{marksheet_type}_processed_{timestamp}.xlsx"
        output_path = OUTPUT_DIR / output_filename
        df.to_excel(output_path, index=False)

        upload_record = UploadHistory(
            user_id=user.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            processed_filename=output_filename,
            marksheet_type=marksheet_type,
            file_size=file_size,
            records_extracted=records_count
        )
        db.session.add(upload_record)
        db.session.commit()

        saved_path.unlink(missing_ok=True)

        return jsonify({
            'success': True,
            'message': f'{marksheet_type.title()} marksheet processed successfully!',
            'download_url': url_for('download_file', filename=output_filename),
            'filename': output_filename,
            'records_count': records_count,
            'summary': df.to_dict(orient="records")
        })

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({'success': False, 'message': 'Processing failed.'}), 500

@app.route("/download/<filename>")
def download_file(filename):
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    output_file = OUTPUT_DIR / filename
    if not output_file.exists():
        return jsonify({'error': 'File not found'}), 404

    upload_record = UploadHistory.query.filter_by(user_id=user.id, processed_filename=filename).first()
    if not upload_record:
        return jsonify({'error': 'Unauthorized access to file'}), 403

    return send_file(output_file, as_attachment=True)

@app.route("/api/history")
def upload_history():
    user = current_user()
    if not user:
        return jsonify([])

    history = UploadHistory.query.filter_by(user_id=user.id).order_by(UploadHistory.upload_date.desc()).all()

    result = [{
        "id": h.id,
        "filename": h.original_filename,
        "marksheet_type": h.marksheet_type,
        "date": h.upload_date.strftime("%Y-%m-%d %H:%M"),
        "records_extracted": h.records_extracted or 0,
        "file_size": h.file_size or 0,
        "processed_filename": h.processed_filename
    } for h in history]

    return jsonify(result)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'message': 'File too large. Maximum size allowed is 10MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': 'Endpoint not found.'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'success': False, 'message': 'Internal server error.'}), 500

create_tables()

if __name__ == "__main__":
    logger.info("Starting Flask server...")
    logger.info("Server running on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
