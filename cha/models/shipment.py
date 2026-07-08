from datetime import datetime
from extensions import db


class Shipment(db.Model):
    __tablename__ = "shipments"
    id = db.Column(db.Integer, primary_key=True)
    file_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    grn_number = db.Column(db.String(50), index=True)
    boe_number = db.Column(db.String(50), index=True)
    supplier_invoice_ref = db.Column(db.String(100), index=True)
    bill_of_supply_number = db.Column(db.String(100))
    supplier_name = db.Column(db.String(200))
    cha_name = db.Column(db.String(200), nullable=False)
    shipping_line = db.Column(db.String(200))
    container_number = db.Column(db.String(100))
    port = db.Column(db.String(100))
    arrival_date = db.Column(db.Date)
    clearance_date = db.Column(db.Date)
    remarks = db.Column(db.Text)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = db.relationship("Invoice", backref="shipment", lazy="dynamic", cascade="all, delete-orphan")
    approval_notes = db.relationship("ApprovalNote", backref="shipment", lazy="dynamic")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def total_amount(self):
        return sum((inv.invoice_amount or 0) for inv in self.invoices)

    def recoverable_amount(self):
        return sum((inv.invoice_amount or 0) for inv in self.invoices if inv.classification == "Recoverable")

    def company_borne_amount(self):
        return sum((inv.invoice_amount or 0) for inv in self.invoices if inv.classification == "Company Borne")

    def __repr__(self):
        return f"<Shipment {self.file_number}>"
