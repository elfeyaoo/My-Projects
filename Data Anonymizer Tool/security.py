
# security.py
import os
import tempfile
import shutil

# Allowed file types
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

def allowed_file(filename):
    """Check if uploaded file is CSV/XLSX."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_temp_file(uploaded_file):
    """
    Save uploaded file to a temporary directory (NOT encrypted).
    Returns: file_path, temp_dir
    """
    temp_dir = tempfile.mkdtemp(prefix="fbl_upload_")
    raw_path = os.path.join(temp_dir, uploaded_file.filename)
    uploaded_file.save(raw_path)
    return raw_path, temp_dir

def decrypt_to_temp(enc_path):
    """
    Dummy function kept for compatibility.
    Since encryption is removed, this just returns the path.
    """
    return enc_path

def cleanup_dir(path):
    """Remove directory and its contents (best effort)."""
    try:
        shutil.rmtree(path)
    except Exception:
        pass

