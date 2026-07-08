"""
REST API blueprint.

Auth: session-based (the same Flask-Login session used by the web UI).
POST /api/login accepts JSON {username, password} and creates a session
cookie the client should retain for subsequent calls. For a fully stateless
JWT-based API, swap login_required for a JWT verification decorator here.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_user, login_required, current_user, logout_user
from models.user import User
from models.shipment import Shipment
from models.invoice import Invoice
from models.approval_note import ApprovalNote

bp = Blueprint("api", __name__, url_prefix="/api")


def _shipment_to_dict(s):
    return {
        "id": s.id, "file_number": s.file_number, "grn_number": s.grn_number,
        "boe_number": s.boe_number, "supplier_invoice_ref": s.supplier_invoice_ref,
        "cha_name": s.cha_name, "shipping_line": s.shipping_line,
        "arrival_date": str(s.arrival_date) if s.arrival_date else None,
        "clearance_date": str(s.clearance_date) if s.clearance_date else None,
        "total_amount": float(s.total_amount()),
    }


def _invoice_to_dict(i):
    return {
        "id": i.id, "shipment_id": i.shipment_id, "invoice_type": i.invoice_type,
        "vendor_name": i.vendor_name, "invoice_number": i.invoice_number,
        "invoice_amount": float(i.invoice_amount or 0), "classification": i.classification,
        "status": i.status,
    }


def _note_to_dict(n):
    return {
        "id": n.id, "document_number": n.document_number, "shipment_id": n.shipment_id,
        "status": n.status, "total_amount": float(n.total_amount or 0),
        "recoverable_amount": float(n.recoverable_amount or 0),
        "document_date": str(n.document_date) if n.document_date else None,
    }


@bp.route("/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=data.get("username", "")).first()
    if user and user.is_active_flag and user.check_password(data.get("password", "")):
        login_user(user)
        return jsonify({"success": True, "user": {"id": user.id, "username": user.username, "role": user.role.name}})
    return jsonify({"success": False, "error": "invalid credentials"}), 401


@bp.route("/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})


@bp.route("/users")
@login_required
def api_users():
    if not current_user.has_role("Administrator"):
        return jsonify({"error": "forbidden"}), 403
    users = User.query.all()
    return jsonify([{"id": u.id, "username": u.username, "full_name": u.full_name,
                      "role": u.role.name if u.role else None, "active": u.is_active_flag} for u in users])


@bp.route("/shipments")
@login_required
def api_shipments():
    shipments = Shipment.query.order_by(Shipment.created_at.desc()).all()
    return jsonify([_shipment_to_dict(s) for s in shipments])


@bp.route("/shipments/<int:shipment_id>")
@login_required
def api_shipment_detail(shipment_id):
    s = Shipment.query.get_or_404(shipment_id)
    data = _shipment_to_dict(s)
    data["invoices"] = [_invoice_to_dict(i) for i in s.invoices]
    return jsonify(data)


@bp.route("/invoices")
@login_required
def api_invoices():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(500).all()
    return jsonify([_invoice_to_dict(i) for i in invoices])


@bp.route("/approval-note")
@login_required
def api_approval_notes():
    notes = ApprovalNote.query.order_by(ApprovalNote.created_at.desc()).limit(200).all()
    return jsonify([_note_to_dict(n) for n in notes])


@bp.route("/approval-note/<int:note_id>")
@login_required
def api_approval_note_detail(note_id):
    n = ApprovalNote.query.get_or_404(note_id)
    return jsonify(_note_to_dict(n))


@bp.route("/reports/summary")
@login_required
def api_reports_summary():
    from extensions import db
    from sqlalchemy import func
    total = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).scalar()
    return jsonify({
        "total_shipments": Shipment.query.count(),
        "total_invoices": Invoice.query.count(),
        "total_invoice_amount": float(total or 0),
        "total_approval_notes": ApprovalNote.query.count(),
    })
