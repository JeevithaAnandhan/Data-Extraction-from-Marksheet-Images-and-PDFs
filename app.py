import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify, redirect, url_for, session, render_template, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_dance.contrib.google import make_google_blueprint, google

# ------------------------------------------------------------------------------
# Setup & Config
# ------------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
CORS(app)

# Secret Key
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SECRET_KEY"] = SECRET_KEY

# Database (prefer Postgres via DATABASE_URL, fallback to SQLite)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'marksheetpro.db'}"
    # Allow SQLite threading for small setups
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Uploads
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "output"
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    folder.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

# ------------------------------------------------------------------------------
# Processor Import (graceful)
# ------------------------------------------------------------------------------

PROCESSOR_AVAILABLE = False
try:
    from processor import process_marksheet
    PROCESSOR_AVAILABLE = True
    logger.info("✅ Processor module imported successfully")
except Exception as e:
    PROCESSOR_AVAILABLE = False
    logger.exception("⚠️ processor import failed — processing endpoints will return 503")

# ------------------------------------------------------------------------------
# OAuth Config (Google)
# ------------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google_bp = make_google_blueprint(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scope=["profile", "email"],
        redirect_url="/auth/google/callback"
    )
    app.register_blueprint(google_bp, url_prefix="/login")

# ------------------------------------------------------------------------------
# Database Models
# ------------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def password(self):
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Marksheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    type = db.Column(db.String(50))
    status = db.Column(db.String(50), default="uploaded")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------------------------------------------------------------
# Utility: Create Tables + Default Admin (optional)
# ------------------------------------------------------------------------------

def create_tables():
    with app.app_context():
        db.create_all()
        if os.environ.get("CREATE_DEFAULT_ADMIN", "false").lower() == "true":
            if not User.query.filter_by(username="admin").first():
                admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
                admin = User(username="admin", email="admin@marksheetpro.com")
                admin.password = admin_pw
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Default admin created")

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/auth/google/callback")
def google_auth_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({"success": False, "message": "Failed to fetch user info"}), 400
    info = resp.json()
    email = info.get("email")
    username = info.get("name")

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username=username, email=email)
        db.session.add(user)
        db.session.commit()
    session["user_id"] = user.id
    return jsonify({"success": True, "message": "Logged in with Google", "user": {"username": username, "email": email}})

@app.route("/process/<marksheet_type>", methods=["POST"])
def process_marksheet_route(marksheet_type):
    if not PROCESSOR_AVAILABLE:
        return jsonify({"success": False, "message": "Processing unavailable on this server"}), 503

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "Empty file"}), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        df = process_marksheet(str(filepath), marksheet_type)
        if not hasattr(df, "__len__"):
            return jsonify({"success": False, "message": "Invalid processor result"}), 500

        output_filename = f"{filepath.stem}_{marksheet_type}_processed.xlsx"
        output_path = OUTPUT_FOLDER / output_filename
        df.to_excel(output_path, index=False)

        ms = Marksheet(filename=filename, type=marksheet_type, status="processed")
        db.session.add(ms)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Processed {len(df)} records",
            "output_file": f"/output/{output_filename}"
        })
    except Exception as e:
        logger.exception("Processing error")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

# ------------------------------------------------------------------------------
# Debug Routes (DEV only, don’t expose in prod)
# ------------------------------------------------------------------------------

@app.route("/api/debug/users")
def debug_users():
    if os.environ.get("FLASK_DEBUG", "false").lower() != "true":
        return jsonify({"error": "Debug routes disabled"}), 403
    users = User.query.all()
    return jsonify([{"id": u.id, "username": u.username, "email": u.email} for u in users])

@app.route("/debug/database-info")
def debug_db_info():
    if os.environ.get("FLASK_DEBUG", "false").lower() != "true":
        return jsonify({"error": "Debug routes disabled"}), 403
    return jsonify({
        "database_uri": app.config["SQLALCHEMY_DATABASE_URI"],
        "upload_folder": str(UPLOAD_FOLDER),
        "output_folder": str(OUTPUT_FOLDER),
        "processor_available": PROCESSOR_AVAILABLE
    })

# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    create_tables()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Starting Flask server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
