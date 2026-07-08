from datetime import datetime
from extensions import db


class Attachment(db.Model):
    __tablename__ = "attachments"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=True)
    category = db.Column(db.String(50))  # Invoice PDF, Bill of Supply, Management Approval, Email, Supporting, Image, Word, Excel
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship("User")
    shipment = db.relationship("Shipment")


class ChargeType(db.Model):
    __tablename__ = "charge_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    short_label = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100), nullable=False)  # e.g. CREATE_SHIPMENT, APPROVE_NOTE
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
