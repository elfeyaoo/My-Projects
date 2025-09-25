# app.py
import os
import shutil
import uuid
import datetime
import tempfile
from pathlib import Path
from threading import Thread
import time

from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, abort
)
from werkzeug.utils import secure_filename
from pymongo import MongoClient, ASCENDING
import pandas as pd
import bcrypt
import numpy as np

# ------------------------------
# Configuration
# ------------------------------
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "supersecretkey")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "anonymizer_db")
TEMP_ROOT = os.environ.get("TEMP_ROOT", os.path.join(tempfile.gettempdir(), "anonymizer_uploads"))
ANON_FILE_LIFETIME_SECONDS = int(os.environ.get("ANON_FILE_LIFETIME_SECONDS", 3600))  # 1 hour
ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}
CLEANUP_INTERVAL = 300  # seconds, every 5 min

# Ensure temp directory exists
Path(TEMP_ROOT).mkdir(parents=True, exist_ok=True)

# ------------------------------
# App & DB init
# ------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = APP_SECRET_KEY

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_col = db["users"]
sessions_col = db["sessions"]
logs_col = db["logs"]
temp_files_col = db["temp_files"]

# TTL index for temp_files
try:
    temp_files_col.create_index([("expireAt", ASCENDING)], expireAfterSeconds=0)
except Exception:
    app.logger.debug("TTL index on temp_files may already exist")

# ------------------------------
# Utility helpers
# ------------------------------
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def check_password(password: str, hashed_str: str) -> bool:
    try:
        hashed_bytes = hashed_str.encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), hashed_bytes)
    except Exception:
        return False

def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS

def create_default_user_if_missing(username="sharayu", password="123456"):
    if users_col.find_one({"username": username}):
        return
    users_col.insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.datetime.utcnow()
    })
    app.logger.info(f"Default user created: {username}")

def cleanup_expired_files():
    """Remove expired files from disk and MongoDB."""
    while True:
        now = datetime.datetime.utcnow()
        expired_files = list(temp_files_col.find({"expireAt": {"$lte": now}}))
        for rec in expired_files:
            path = rec.get("path")
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    parent = os.path.dirname(path)
                    if os.path.isdir(parent) and not os.listdir(parent):
                        os.rmdir(parent)
            except Exception:
                app.logger.debug(f"Failed to delete expired file: {path}")
            finally:
                temp_files_col.delete_one({"_id": rec["_id"]})
        time.sleep(CLEANUP_INTERVAL)

# Run initial DB setup actions
create_default_user_if_missing()

# Start background cleanup thread
cleanup_thread = Thread(target=cleanup_expired_files, daemon=True)
cleanup_thread.start()

# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", raw_preview="", anon_preview="")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = users_col.find_one({"username": username})

        # Safely check password_hash
        password_hash = user.get("password_hash") if user else None
        if user and password_hash and check_password(password, password_hash):
            session["username"] = username
            sessions_col.insert_one({
                "username": username,
                "action": "login",
                "timestamp": datetime.datetime.utcnow()
            })
            logs_col.insert_one({
                "username": username,
                "action": "login",
                "timestamp": datetime.datetime.utcnow(),
                "status": "success"
            })
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            logs_col.insert_one({
                "username": username or "unknown",
                "action": "login_attempt",
                "timestamp": datetime.datetime.utcnow(),
                "status": "failed"
            })
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not username or not password or not confirm_password:
        flash("All fields are required.", "danger")
        return redirect(url_for("login"))

    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("login"))

    if users_col.find_one({"username": username}):
        flash("Username already exists. Choose another.", "danger")
        return redirect(url_for("login"))

    users_col.insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.datetime.utcnow()
    })
    flash("Account created successfully! Please login.", "success")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    if "username" in session:
        sessions_col.insert_one({
            "username": session["username"],
            "action": "logout",
            "timestamp": datetime.datetime.utcnow()
        })
        logs_col.insert_one({
            "username": session["username"],
            "action": "logout",
            "timestamp": datetime.datetime.utcnow(),
            "status": "success"
        })
        session.pop("username", None)
    return redirect(url_for("login"))

# ------------------------------
# Preview
# ------------------------------
@app.route("/preview", methods=["POST"])
def preview():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Unsupported file extension"}), 400

        tmp_dir = tempfile.mkdtemp(dir=TEMP_ROOT)
        filename = secure_filename(file.filename)
        saved_path = os.path.join(tmp_dir, filename)
        file.save(saved_path)

        # Load dataframe
        df = pd.read_csv(saved_path) if filename.lower().endswith(".csv") else pd.read_excel(saved_path)
        raw_preview_html = df.head(10).to_html(classes="table table-bordered table-sm", index=False)

        # Generate quick anonymized preview (temporary, 50% by default)
        anon_df = df.copy()
        nrows = len(anon_df)
        for col in anon_df.select_dtypes(include=["object", "string"]).columns:
            k = max(1, nrows // 2)  # 50%
            idxs = np.random.choice(nrows, k, replace=False)
            anon_df.loc[idxs, col] = "XXX"
        anon_preview_html = anon_df.head(10).to_html(classes="table table-bordered table-sm", index=False)

        shutil.rmtree(tmp_dir, ignore_errors=True)

        return jsonify({"success": True, "raw_html": raw_preview_html, "anon_html": anon_preview_html})

    except Exception as e:
        app.logger.exception("Preview failed")
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------
# Anonymize
# ------------------------------
@app.route("/anonymize", methods=["POST"])
def anonymize():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Unsupported file extension"}), 400

        tmp_dir = tempfile.mkdtemp(dir=TEMP_ROOT)
        filename = secure_filename(file.filename)
        saved_path = os.path.join(tmp_dir, filename)
        file.save(saved_path)

        df = pd.read_csv(saved_path) if filename.lower().endswith(".csv") else pd.read_excel(saved_path)

        mode = request.form.get("mode", "all-rows")
        try:
            percentage = int(request.form.get("percentage", 50))
        except Exception:
            percentage = 50

        dp_enabled = request.form.get("dp_enabled") in ("on", "true", "1")
        try:
            epsilon_val = float(request.form.get("epsilon")) if request.form.get("epsilon") else None
        except Exception:
            epsilon_val = None

        # Anonymization logic
        anon_df = df.copy()
        for col in anon_df.columns:
            if anon_df[col].dtype == "object" or str(anon_df[col].dtype).startswith("string"):
                nrows = len(anon_df)
                if nrows == 0:
                    continue
                k = max(1, int((percentage / 100.0) * nrows))
                idxs = np.random.choice(nrows, k, replace=False)
                anon_df.loc[idxs, col] = "XXX"

        if dp_enabled and epsilon_val and epsilon_val > 0:
            sensitivity = 1.0
            for col in anon_df.select_dtypes(include=["number"]).columns:
                scale = sensitivity / epsilon_val
                noise = np.random.laplace(loc=0.0, scale=scale, size=len(anon_df))
                try:
                    anon_df[col] = anon_df[col].astype(float) + noise
                except Exception:
                    pass

        anon_fname = f"anonymized_{uuid.uuid4().hex}.csv"
        anon_path = os.path.join(tmp_dir, anon_fname)
        anon_df.to_csv(anon_path, index=False)

        token = uuid.uuid4().hex
        expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=ANON_FILE_LIFETIME_SECONDS)
        temp_files_col.insert_one({
            "token": token,
            "username": session.get("username", "anonymous"),
            "path": anon_path,
            "original_filename": filename,
            "createdAt": datetime.datetime.utcnow(),
            "expireAt": expire_at
        })

        logs_col.insert_one({
            "username": session.get("username", "anonymous"),
            "filename": filename,
            "action": "anonymize",
            "mode": mode,
            "percentage": percentage,
            "dp_enabled": dp_enabled,
            "epsilon": epsilon_val,
            "timestamp": datetime.datetime.utcnow(),
            "status": "success"
        })

        raw_preview_html = df.head(10).to_html(classes="table table-bordered table-sm", index=False)
        anon_preview_html = anon_df.head(10).to_html(classes="table table-bordered table-sm", index=False)
        download_url = url_for("download_file", token=token, _external=True)

        return jsonify({
            "success": True,
            "raw_html": raw_preview_html,
            "anon_html": anon_preview_html,
            "download_url": download_url,
            "expires_at": expire_at.isoformat()
        })

    except Exception as e:
        app.logger.exception("Anonymize error")
        logs_col.insert_one({
            "username": session.get("username", "anonymous"),
            "filename": file.filename if file else "unknown",
            "action": "anonymize",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow(),
            "status": "failed"
        })
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------
# Download
# ------------------------------
@app.route("/download/<token>")
def download_file(token: str):
    rec = temp_files_col.find_one({"token": token})
    if not rec:
        return abort(404, description="File not found or expired")

    expire_at = rec.get("expireAt")
    if expire_at and expire_at <= datetime.datetime.utcnow():
        try:
            if os.path.exists(rec.get("path", "")):
                os.remove(rec.get("path"))
        except Exception:
            pass
        temp_files_col.delete_one({"_id": rec["_id"]})
        return abort(404, description="File expired")

    filepath = rec.get("path")
    if not filepath or not os.path.exists(filepath):
        temp_files_col.delete_one({"_id": rec["_id"]})
        return abort(404, description="File missing")

    requester = session.get("username")
    if rec.get("username") != "anonymous" and requester != rec.get("username"):
        return abort(403, description="Forbidden: you did not create this anonymized file")

    try:
        response = send_file(filepath, as_attachment=True, download_name=rec.get("original_filename", "anonymized.csv"))
        # Delete file and record after sending
        try:
            os.remove(filepath)
        except Exception:
            app.logger.debug("Could not delete temp file from disk after download")
        try:
            temp_files_col.delete_one({"_id": rec["_id"]})
        except Exception:
            app.logger.debug("Could not delete temp file record from DB after download")

        parent = os.path.dirname(filepath)
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except Exception:
            pass

        return response
    except Exception as e:
        app.logger.exception("Failed to send file")
        return abort(500, description="Download failed")

# ------------------------------
# Admin / Status
# ------------------------------
@app.route("/_status")
def status():
    return jsonify({
        "users": users_col.count_documents({}),
        "sessions": sessions_col.count_documents({}),
        "logs": logs_col.count_documents({}),
        "temp_files": temp_files_col.count_documents({})
    })

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
