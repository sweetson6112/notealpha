from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models.shipment import Shipment
from models.invoice import Invoice, INVOICE_TYPES, COMPANY_BORNE_REASONS, RECOVER_FROM_OPTIONS, INVOICE_STATUSES
from models.misc import Attachment
from utils.decorators import roles_required
from utils.uploads import save_upload, allowed_file
from services.audit import log_action

bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_amount(value):
    try:
        return Decimal(value) if value not in (None, "") else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


@bp.route("/shipment/<int:shipment_id>/new", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def new_invoice(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    if request.method == "POST":
        invoice = Invoice(
            shipment_id=shipment.id,
            invoice_type=request.form.get("invoice_type"),
            vendor_name=request.form.get("vendor_name"),
            invoice_number=request.form.get("invoice_number"),
            invoice_date=_parse_date(request.form.get("invoice_date")),
            invoice_amount=_parse_amount(request.form.get("invoice_amount")),
            gst=_parse_amount(request.form.get("gst")),
            bill_of_supply=request.form.get("bill_of_supply"),
            srn=request.form.get("srn"),
            cha_ref=request.form.get("cha_ref"),
            remarks=request.form.get("remarks"),
            status=request.form.get("status", "Pending"),
            classification=request.form.get("classification"),
            company_borne_reason=request.form.get("company_borne_reason"),
            recover_from=request.form.get("recover_from"),
            recover_from_party=request.form.get("recover_from_party"),
        )
        db.session.add(invoice)
        db.session.flush()

        file = request.files.get("upload")
        if file and file.filename and allowed_file(file.filename):
            original, stored, ctype = save_upload(file)
            db.session.add(Attachment(
                invoice_id=invoice.id, shipment_id=shipment.id,
                category=request.form.get("upload_category", "Supporting Documents"),
                original_filename=original, stored_filename=stored, content_type=ctype,
                uploaded_by_id=current_user.id,
            ))

        db.session.commit()
        log_action("CREATE_INVOICE", "Invoice", invoice.id, f"Shipment {shipment.file_number}")
        flash("Invoice added.", "success")
        return redirect(url_for("shipments.view_shipment", shipment_id=shipment.id))

    return render_template("invoices/form.html", shipment=shipment, invoice=None,
                            invoice_types=INVOICE_TYPES, reasons=COMPANY_BORNE_REASONS,
                            recover_options=RECOVER_FROM_OPTIONS, statuses=INVOICE_STATUSES)


@bp.route("/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    shipment = invoice.shipment
    if request.method == "POST":
        invoice.invoice_type = request.form.get("invoice_type")
        invoice.vendor_name = request.form.get("vendor_name")
        invoice.invoice_number = request.form.get("invoice_number")
        invoice.invoice_date = _parse_date(request.form.get("invoice_date"))
        invoice.invoice_amount = _parse_amount(request.form.get("invoice_amount"))
        invoice.gst = _parse_amount(request.form.get("gst"))
        invoice.bill_of_supply = request.form.get("bill_of_supply")
        invoice.srn = request.form.get("srn")
        invoice.cha_ref = request.form.get("cha_ref")
        invoice.remarks = request.form.get("remarks")
        invoice.status = request.form.get("status", invoice.status)
        invoice.classification = request.form.get("classification")
        invoice.company_borne_reason = request.form.get("company_borne_reason")
        invoice.recover_from = request.form.get("recover_from")
        invoice.recover_from_party = request.form.get("recover_from_party")

        file = request.files.get("upload")
        if file and file.filename and allowed_file(file.filename):
            original, stored, ctype = save_upload(file)
            db.session.add(Attachment(
                invoice_id=invoice.id, shipment_id=shipment.id,
                category=request.form.get("upload_category", "Supporting Documents"),
                original_filename=original, stored_filename=stored, content_type=ctype,
                uploaded_by_id=current_user.id,
            ))

        db.session.commit()
        log_action("UPDATE_INVOICE", "Invoice", invoice.id)
        flash("Invoice updated.", "success")
        return redirect(url_for("shipments.view_shipment", shipment_id=shipment.id))

    return render_template("invoices/form.html", shipment=shipment, invoice=invoice,
                            invoice_types=INVOICE_TYPES, reasons=COMPANY_BORNE_REASONS,
                            recover_options=RECOVER_FROM_OPTIONS, statuses=INVOICE_STATUSES)


@bp.route("/<int:invoice_id>/delete", methods=["POST"])
@login_required
@roles_required("Administrator", "Bond Superintendent")
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    shipment_id = invoice.shipment_id
    db.session.delete(invoice)
    db.session.commit()
    log_action("DELETE_INVOICE", "Invoice", invoice_id)
    flash("Invoice deleted.", "info")
    return redirect(url_for("shipments.view_shipment", shipment_id=shipment_id))
