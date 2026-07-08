import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app, abort
from flask_login import login_required, current_user
from extensions import db
from models.statutory_document import (
    StatutoryDocument, STATUTORY_DOC_CATEGORIES,
    DOC_STATUS_ACTIVE, DOC_STATUS_EXPIRING_SOON, DOC_STATUS_EXPIRED,
)
from utils.decorators import roles_required
from utils.uploads import save_pdf_upload
from services.audit import log_action

bp = Blueprint("statutory_docs", __name__, url_prefix="/statutory-documents")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.route("/")
@login_required
def list_documents():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = StatutoryDocument.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            StatutoryDocument.title.ilike(like),
            StatutoryDocument.document_number.ilike(like),
            StatutoryDocument.issuing_authority.ilike(like),
        ))
    if category:
        query = query.filter(StatutoryDocument.category == category)

    documents = query.order_by(StatutoryDocument.category, StatutoryDocument.title).all()

    if status_filter:
        documents = [d for d in documents if d.computed_status() == status_filter]

    expiring_count = sum(1 for d in StatutoryDocument.query.all() if d.computed_status() == DOC_STATUS_EXPIRING_SOON)
    expired_count = sum(1 for d in StatutoryDocument.query.all() if d.computed_status() == DOC_STATUS_EXPIRED)

    return render_template(
        "statutory/list.html", documents=documents, categories=STATUTORY_DOC_CATEGORIES,
        q=q, category=category, status_filter=status_filter,
        expiring_count=expiring_count, expired_count=expired_count,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Bond Superintendent", "Accounts Officer")
def new_document():
    if request.method == "POST":
        file = request.files.get("document_file")
        saved = save_pdf_upload(file)
        if not saved:
            flash("Please upload a valid PDF file. Only .pdf documents are accepted here.", "danger")
            return render_template("statutory/form.html", document=None, categories=STATUTORY_DOC_CATEGORIES, form=request.form)

        original, stored, _ctype = saved
        doc = StatutoryDocument(
            category=request.form.get("category"),
            title=request.form.get("title", "").strip(),
            document_number=request.form.get("document_number"),
            issuing_authority=request.form.get("issuing_authority"),
            issue_date=_parse_date(request.form.get("issue_date")),
            expiry_date=_parse_date(request.form.get("expiry_date")),
            remarks=request.form.get("remarks"),
            original_filename=original,
            stored_filename=stored,
            uploaded_by_id=current_user.id,
        )
        db.session.add(doc)
        db.session.commit()
        log_action("UPLOAD_STATUTORY_DOCUMENT", "StatutoryDocument", doc.id, doc.title)
        flash(f"Statutory document '{doc.title}' uploaded.", "success")
        return redirect(url_for("statutory_docs.list_documents"))

    return render_template("statutory/form.html", document=None, categories=STATUTORY_DOC_CATEGORIES, form=None)


@bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Bond Superintendent", "Accounts Officer")
def edit_document(doc_id):
    doc = StatutoryDocument.query.get_or_404(doc_id)
    if request.method == "POST":
        doc.category = request.form.get("category")
        doc.title = request.form.get("title", "").strip()
        doc.document_number = request.form.get("document_number")
        doc.issuing_authority = request.form.get("issuing_authority")
        doc.issue_date = _parse_date(request.form.get("issue_date"))
        doc.expiry_date = _parse_date(request.form.get("expiry_date"))
        doc.remarks = request.form.get("remarks")

        file = request.files.get("document_file")
        if file and file.filename:
            saved = save_pdf_upload(file)
            if not saved:
                flash("Replacement file must be a valid PDF. Existing file was kept unchanged.", "warning")
            else:
                original, stored, _ctype = saved
                doc.original_filename = original
                doc.stored_filename = stored

        db.session.commit()
        log_action("UPDATE_STATUTORY_DOCUMENT", "StatutoryDocument", doc.id)
        flash("Statutory document updated.", "success")
        return redirect(url_for("statutory_docs.list_documents"))

    return render_template("statutory/form.html", document=doc, categories=STATUTORY_DOC_CATEGORIES, form=None)


@bp.route("/<int:doc_id>/download")
@login_required
def download_document(doc_id):
    doc = StatutoryDocument.query.get_or_404(doc_id)
    directory = current_app.config["UPLOAD_FOLDER"]
    rel_dir = os.path.dirname(doc.stored_filename)
    filename = os.path.basename(doc.stored_filename)
    full_dir = os.path.join(directory, rel_dir) if rel_dir else directory
    log_action("DOWNLOAD_STATUTORY_DOCUMENT", "StatutoryDocument", doc.id)
    return send_from_directory(full_dir, filename, as_attachment=True, download_name=doc.original_filename)


@bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
@roles_required("Administrator")
def delete_document(doc_id):
    doc = StatutoryDocument.query.get_or_404(doc_id)
    directory = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(directory, doc.stored_filename)
    title = doc.title
    db.session.delete(doc)
    db.session.commit()
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    log_action("DELETE_STATUTORY_DOCUMENT", "StatutoryDocument", doc_id, title)
    flash(f"Statutory document '{title}' deleted.", "info")
    return redirect(url_for("statutory_docs.list_documents"))
