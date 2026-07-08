import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file_storage):
    """Saves a Werkzeug FileStorage to the upload folder with a random,
    collision-proof name, and returns (original_filename, stored_filename, content_type)."""
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "bin"
    stored = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], stored)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file_storage.save(dest)
    return original, stored, file_storage.content_type
