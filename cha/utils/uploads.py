import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def is_pdf(filename):
    return filename.lower().endswith(".pdf")


def save_upload(file_storage, subfolder=None):
    """Saves a Werkzeug FileStorage to the upload folder (optionally inside a
    subfolder) with a random, collision-proof name, and returns
    (original_filename, stored_filename, content_type). `stored_filename`
    includes the subfolder prefix (e.g. "statutory/abcd1234.pdf") when given."""
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "bin"
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    stored_rel = os.path.join(subfolder, stored_name) if subfolder else stored_name
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    file_storage.save(dest)
    return original, stored_rel, file_storage.content_type


def save_pdf_upload(file_storage, subfolder="statutory"):
    """Like save_upload, but strictly enforces a .pdf extension/content-type.
    Returns None if the uploaded file is not a PDF."""
    if not file_storage or not file_storage.filename:
        return None
    if not is_pdf(file_storage.filename):
        return None
    return save_upload(file_storage, subfolder=subfolder)
