from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models.shipment import Shipment
from models.invoice import Invoice, DEFAULT_INVOICE_TYPES
from utils.decorators import roles_required
from services.audit import log_action

bp = Blueprint("shipments", __name__, url_prefix="/shipments")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.route("/")
@login_required
def list_shipments():
    q = request.args.get("q", "").strip()
    query = Shipment.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Shipment.file_number.ilike(like),
            Shipment.grn_number.ilike(like),
            Shipment.boe_number.ilike(like),
            Shipment.cha_name.ilike(like),
            Shipment.supplier_name.ilike(like),
        ))
    shipments = query.order_by(Shipment.created_at.desc()).all()
    return render_template("shipments/list.html", shipments=shipments, q=q)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def new_shipment():
    if request.method == "POST":
        file_number = request.form.get("file_number", "").strip()
        if Shipment.query.filter_by(file_number=file_number).first():
            flash("A shipment with this File Number already exists.", "danger")
            return render_template("shipments/form.html", shipment=None, form=request.form)

        shipment = Shipment(
            file_number=file_number,
            grn_number=request.form.get("grn_number"),
            boe_number=request.form.get("boe_number"),
            supplier_invoice_ref=request.form.get("supplier_invoice_ref"),
            bill_of_supply_number=request.form.get("bill_of_supply_number"),
            supplier_name=request.form.get("supplier_name"),
            cha_name=request.form.get("cha_name"),
            shipping_line=request.form.get("shipping_line"),
            container_number=request.form.get("container_number"),
            port=request.form.get("port"),
            arrival_date=_parse_date(request.form.get("arrival_date")),
            clearance_date=_parse_date(request.form.get("clearance_date")),
            remarks=request.form.get("remarks"),
            created_by_id=current_user.id,
        )
        db.session.add(shipment)
        db.session.flush()

        # Auto-create default invoices
        for inv_type in DEFAULT_INVOICE_TYPES:
            db.session.add(Invoice(shipment_id=shipment.id, invoice_type=inv_type, status="Pending"))

        db.session.commit()
        log_action("CREATE_SHIPMENT", "Shipment", shipment.id, f"File Number {shipment.file_number}")
        flash("Shipment created with default invoices (Shipping Line + CHA Service Charge).", "success")
        return redirect(url_for("shipments.view_shipment", shipment_id=shipment.id))

    return render_template("shipments/form.html", shipment=None, form=None)


@bp.route("/<int:shipment_id>")
@login_required
def view_shipment(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    invoices = shipment.invoices.all()
    notes = shipment.approval_notes.order_by(db.text("id desc")).all()
    return render_template("shipments/view.html", shipment=shipment, invoices=invoices, notes=notes)


@bp.route("/<int:shipment_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("Administrator", "Accounts Officer", "Bond Superintendent")
def edit_shipment(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    if request.method == "POST":
        shipment.grn_number = request.form.get("grn_number")
        shipment.boe_number = request.form.get("boe_number")
        shipment.supplier_invoice_ref = request.form.get("supplier_invoice_ref")
        shipment.bill_of_supply_number = request.form.get("bill_of_supply_number")
        shipment.supplier_name = request.form.get("supplier_name")
        shipment.cha_name = request.form.get("cha_name")
        shipment.shipping_line = request.form.get("shipping_line")
        shipment.container_number = request.form.get("container_number")
        shipment.port = request.form.get("port")
        shipment.arrival_date = _parse_date(request.form.get("arrival_date"))
        shipment.clearance_date = _parse_date(request.form.get("clearance_date"))
        shipment.remarks = request.form.get("remarks")
        db.session.commit()
        log_action("UPDATE_SHIPMENT", "Shipment", shipment.id)
        flash("Shipment updated.", "success")
        return redirect(url_for("shipments.view_shipment", shipment_id=shipment.id))

    return render_template("shipments/form.html", shipment=shipment, form=None)
