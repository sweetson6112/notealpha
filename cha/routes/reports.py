import os
from flask import Blueprint, render_template, send_file, current_app
from flask_login import login_required
from models.shipment import Shipment
from models.invoice import Invoice, CLASSIFICATION_RECOVERABLE, CLASSIFICATION_COMPANY_BORNE
from models.approval_note import ApprovalNote
from services.export_other import export_register_excel

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")


@bp.route("/shipment-register")
@login_required
def shipment_register():
    shipments = Shipment.query.order_by(Shipment.created_at.desc()).all()
    return render_template("reports/shipment_register.html", shipments=shipments)


@bp.route("/shipment-register/export")
@login_required
def shipment_register_export():
    shipments = Shipment.query.order_by(Shipment.created_at.desc()).all()
    headers = ["File Number", "GRN", "BOE", "CHA", "Supplier", "Shipping Line", "Arrival", "Clearance", "Total Amount"]
    rows = [[s.file_number, s.grn_number, s.boe_number, s.cha_name, s.supplier_name, s.shipping_line,
             str(s.arrival_date or ""), str(s.clearance_date or ""), float(s.total_amount())] for s in shipments]
    path = os.path.join(current_app.config["EXPORT_FOLDER"], "shipment_register.xlsx")
    export_register_excel(rows, headers, "Shipment Register", path)
    return send_file(path, as_attachment=True, download_name="Shipment_Register.xlsx")


@bp.route("/invoice-register")
@login_required
def invoice_register():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template("reports/invoice_register.html", invoices=invoices)


@bp.route("/invoice-register/export")
@login_required
def invoice_register_export():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    headers = ["Shipment File No", "Invoice Type", "Vendor", "Invoice No", "Amount", "Classification", "Status"]
    rows = [[i.shipment.file_number, i.invoice_type, i.vendor_name, i.invoice_number,
             float(i.invoice_amount or 0), i.classification, i.status] for i in invoices]
    path = os.path.join(current_app.config["EXPORT_FOLDER"], "invoice_register.xlsx")
    export_register_excel(rows, headers, "Invoice Register", path)
    return send_file(path, as_attachment=True, download_name="Invoice_Register.xlsx")


@bp.route("/recoverable-charges")
@login_required
def recoverable_charges():
    invoices = Invoice.query.filter_by(classification=CLASSIFICATION_RECOVERABLE).order_by(Invoice.created_at.desc()).all()
    total = sum(float(i.invoice_amount or 0) for i in invoices)
    return render_template("reports/recoverable_charges.html", invoices=invoices, total=total)


@bp.route("/company-charges")
@login_required
def company_charges():
    invoices = Invoice.query.filter_by(classification=CLASSIFICATION_COMPANY_BORNE).order_by(Invoice.created_at.desc()).all()
    total = sum(float(i.invoice_amount or 0) for i in invoices)
    return render_template("reports/company_charges.html", invoices=invoices, total=total)


@bp.route("/vendor-summary")
@login_required
def vendor_summary():
    invoices = Invoice.query.all()
    summary = {}
    for inv in invoices:
        key = inv.vendor_name or "Unspecified"
        summary.setdefault(key, {"count": 0, "amount": 0.0})
        summary[key]["count"] += 1
        summary[key]["amount"] += float(inv.invoice_amount or 0)
    return render_template("reports/vendor_summary.html", summary=summary)


@bp.route("/approval-register")
@login_required
def approval_register():
    notes = ApprovalNote.query.order_by(ApprovalNote.created_at.desc()).all()
    return render_template("reports/approval_register.html", notes=notes)


@bp.route("/pending-bills")
@login_required
def pending_bills():
    invoices = Invoice.query.filter(Invoice.status.in_(["Pending", "Verified"])).order_by(Invoice.created_at.desc()).all()
    return render_template("reports/pending_bills.html", invoices=invoices)


@bp.route("/paid-bills")
@login_required
def paid_bills():
    invoices = Invoice.query.filter_by(status="Paid").order_by(Invoice.created_at.desc()).all()
    return render_template("reports/paid_bills.html", invoices=invoices)
