from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from extensions import db
from models.shipment import Shipment
from models.invoice import Invoice, CLASSIFICATION_RECOVERABLE, CLASSIFICATION_COMPANY_BORNE
from models.approval_note import ApprovalNote
from models.misc import AuditLog

bp = Blueprint("dashboard", __name__, url_prefix="/")


@bp.route("/")
@login_required
def index():
    pending_notes = ApprovalNote.query.filter(
        ApprovalNote.status.in_(["Draft", "Submitted", "Accounts Verification", "Manager Approval", "Finance Approval"])
    ).count()
    approved_notes = ApprovalNote.query.filter(ApprovalNote.status.in_(["Paid", "Completed"])).count()
    paid_bills = Invoice.query.filter_by(status="Paid").count()
    pending_bills = Invoice.query.filter(Invoice.status.in_(["Pending", "Verified"])).count()

    month_start = datetime.utcnow().replace(day=1)
    monthly_expenses = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
        Invoice.created_at >= month_start
    ).scalar()

    recoverable_charges = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
        Invoice.classification == CLASSIFICATION_RECOVERABLE
    ).scalar()
    company_borne_charges = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
        Invoice.classification == CLASSIFICATION_COMPANY_BORNE
    ).scalar()

    recent_shipments = Shipment.query.order_by(Shipment.created_at.desc()).limit(6).all()
    recent_activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    kpis = dict(
        pending_notes=pending_notes,
        approved_notes=approved_notes,
        paid_bills=paid_bills,
        pending_bills=pending_bills,
        monthly_expenses=float(monthly_expenses or 0),
        recoverable_charges=float(recoverable_charges or 0),
        company_borne_charges=float(company_borne_charges or 0),
    )

    return render_template("dashboard/index.html", kpis=kpis,
                            recent_shipments=recent_shipments, recent_activity=recent_activity)


@bp.route("/api/dashboard/monthly-trend")
@login_required
def monthly_trend():
    """Last 6 months of expense totals, for the dashboard line chart."""
    today = datetime.utcnow()
    labels, values = [], []
    for i in range(5, -1, -1):
        month = (today.replace(day=1) - timedelta(days=1)).replace(day=1) if i == 0 else None
    # Build months going back
    months = []
    cursor = today.replace(day=1)
    for _ in range(6):
        months.append(cursor)
        prev_month_end = cursor - timedelta(days=1)
        cursor = prev_month_end.replace(day=1)
    months.reverse()

    for m_start in months:
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)
        total = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
            Invoice.created_at >= m_start, Invoice.created_at < m_end
        ).scalar()
        labels.append(m_start.strftime("%b %Y"))
        values.append(float(total or 0))

    return jsonify({"labels": labels, "values": values})


@bp.route("/api/dashboard/charge-split")
@login_required
def charge_split():
    recoverable = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
        Invoice.classification == CLASSIFICATION_RECOVERABLE
    ).scalar()
    company_borne = db.session.query(func.coalesce(func.sum(Invoice.invoice_amount), 0)).filter(
        Invoice.classification == CLASSIFICATION_COMPANY_BORNE
    ).scalar()
    return jsonify({"labels": ["Recoverable", "Company Borne"], "values": [float(recoverable or 0), float(company_borne or 0)]})
