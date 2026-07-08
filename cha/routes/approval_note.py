import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from extensions import db
from models.shipment import Shipment
from models.approval_note import ApprovalNote, ApprovalHistory, WORKFLOW_STATES
from utils.decorators import roles_required
from services.approval_note_generator import generate_approval_note, regenerate_paragraphs
from services.export_docx import render_approval_note_docx
from services.export_other import docx_to_pdf, export_approval_note_excel
from services.audit import log_action

bp = Blueprint("approval_note", __name__, url_prefix="/approval-notes")

# Who is allowed to push the workflow forward at each stage
STAGE_ROLES = {
    "Draft": ["Administrator", "Accounts Officer", "Bond Superintendent"],
    "Submitted": ["Administrator", "Accounts Officer"],
    "Accounts Verification": ["Administrator", "Accounts Officer"],
    "Manager Approval": ["Administrator", "Manager"],
    "Finance Approval": ["Administrator", "Finance"],
    "Paid": ["Administrator", "Finance"],
}


@bp.route("/shipment/<int:shipment_id>/generate", methods=["POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def generate(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    if shipment.invoices.count() == 0:
        flash("Add at least one invoice before generating an Approval Note.", "warning")
        return redirect(url_for("shipments.view_shipment", shipment_id=shipment.id))

    note = generate_approval_note(shipment, current_user)
    db.session.add(ApprovalHistory(approval_note_id=note.id, from_status=None, to_status="Draft",
                                    action_by_id=current_user.id, remarks="Approval Note generated"))
    db.session.commit()
    log_action("GENERATE_APPROVAL_NOTE", "ApprovalNote", note.id, note.document_number)
    flash(f"Approval Note {note.document_number} generated.", "success")
    return redirect(url_for("approval_note.view_note", note_id=note.id))


@bp.route("/<int:note_id>")
@login_required
def view_note(note_id):
    note = ApprovalNote.query.get_or_404(note_id)
    shipment = note.shipment
    invoices = shipment.invoices.all()
    return render_template("approval/view.html", note=note, shipment=shipment, invoices=invoices,
                            states=WORKFLOW_STATES)


@bp.route("/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def edit_note(note_id):
    note = ApprovalNote.query.get_or_404(note_id)
    if note.status != "Draft":
        flash("Only Draft notes can be edited. Recall the workflow to Draft first if needed.", "warning")
        return redirect(url_for("approval_note.view_note", note_id=note.id))

    if request.method == "POST":
        note.subject_text = request.form.get("subject_text")
        note.paragraph_1 = request.form.get("paragraph_1")
        note.paragraph_2 = request.form.get("paragraph_2")
        note.paragraph_3 = request.form.get("paragraph_3")
        note.paragraph_4 = request.form.get("paragraph_4")
        db.session.commit()
        log_action("EDIT_APPROVAL_NOTE", "ApprovalNote", note.id)
        flash("Approval Note updated.", "success")
        return redirect(url_for("approval_note.view_note", note_id=note.id))

    return render_template("approval/edit.html", note=note)


@bp.route("/<int:note_id>/regenerate", methods=["POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def regenerate(note_id):
    note = ApprovalNote.query.get_or_404(note_id)
    regenerate_paragraphs(note)
    log_action("REGENERATE_APPROVAL_NOTE", "ApprovalNote", note.id)
    flash("Paragraphs and totals recalculated from current invoice data.", "info")
    return redirect(url_for("approval_note.edit_note", note_id=note.id))


@bp.route("/<int:note_id>/transition", methods=["POST"])
@login_required
def transition(note_id):
    note = ApprovalNote.query.get_or_404(note_id)
    current_idx = WORKFLOW_STATES.index(note.status) if note.status in WORKFLOW_STATES else 0
    action = request.form.get("action")  # "advance" or "reject"
    remarks = request.form.get("remarks", "")

    allowed_roles = STAGE_ROLES.get(note.status, ["Administrator"])
    if not current_user.has_role(*allowed_roles):
        flash("You do not have permission to act on this stage.", "danger")
        return redirect(url_for("approval_note.view_note", note_id=note.id))

    old_status = note.status
    if action == "advance" and current_idx < len(WORKFLOW_STATES) - 1:
        note.status = WORKFLOW_STATES[current_idx + 1]
    elif action == "reject":
        note.status = "Draft"
    db.session.add(ApprovalHistory(approval_note_id=note.id, from_status=old_status, to_status=note.status,
                                    action_by_id=current_user.id, remarks=remarks))
    db.session.commit()
    log_action("TRANSITION_APPROVAL_NOTE", "ApprovalNote", note.id, f"{old_status} -> {note.status}")
    flash(f"Approval Note moved to '{note.status}'.", "success")
    return redirect(url_for("approval_note.view_note", note_id=note.id))


@bp.route("/<int:note_id>/export/<fmt>")
@login_required
def export(note_id, fmt):
    note = ApprovalNote.query.get_or_404(note_id)
    shipment = note.shipment
    invoices = shipment.invoices.all()

    export_dir = current_app.config["EXPORT_FOLDER"]
    base_name = note.document_number.replace("/", "_")
    docx_path = os.path.join(export_dir, base_name + ".docx")
    render_approval_note_docx(note, shipment, invoices, docx_path)

    if fmt == "docx":
        log_action("EXPORT_APPROVAL_NOTE", "ApprovalNote", note.id, "docx")
        return send_file(docx_path, as_attachment=True, download_name=base_name + ".docx")

    if fmt == "pdf":
        pdf_path = docx_to_pdf(docx_path, export_dir)
        if not pdf_path:
            flash("PDF conversion engine (LibreOffice) is not available on this server. Downloading Word file instead.", "warning")
            return send_file(docx_path, as_attachment=True, download_name=base_name + ".docx")
        log_action("EXPORT_APPROVAL_NOTE", "ApprovalNote", note.id, "pdf")
        return send_file(pdf_path, as_attachment=True, download_name=base_name + ".pdf")

    if fmt == "excel":
        xlsx_path = os.path.join(export_dir, base_name + ".xlsx")
        export_approval_note_excel(note, shipment, invoices, xlsx_path)
        log_action("EXPORT_APPROVAL_NOTE", "ApprovalNote", note.id, "excel")
        return send_file(xlsx_path, as_attachment=True, download_name=base_name + ".xlsx")

    flash("Unknown export format.", "danger")
    return redirect(url_for("approval_note.view_note", note_id=note.id))


@bp.route("/<int:note_id>/print")
@login_required
def print_view(note_id):
    note = ApprovalNote.query.get_or_404(note_id)
    shipment = note.shipment
    invoices = shipment.invoices.all()
    return render_template("approval/print.html", note=note, shipment=shipment, invoices=invoices)
