from datetime import datetime
from extensions import db

INVOICE_TYPES = [
    "Shipping Line Invoice Reimbursement",
    "Detention Reimbursement",
    "Demurrage Reimbursement",
    "Late Filing Charges",
    "Delivery Order Revalidation Charges",
    "CHA Service Charges",
    "Plugging Charges",
    "Handling Charges",
]

# Short label used inside the generated approval note table ("Consignment Charges" column)
INVOICE_TYPE_SHORT_LABEL = {
    "Shipping Line Invoice Reimbursement": "Shipment Line Charges",
    "Detention Reimbursement": "Detention Charges",
    "Demurrage Reimbursement": "Demurrage Charges",
    "Late Filing Charges": "Late Filing Charges",
    "Delivery Order Revalidation Charges": "DO Revalidation Charges",
    "CHA Service Charges": "Service Charges",
    "Plugging Charges": "Plugging Charges",
    "Handling Charges": "Handling Charges",
}

DEFAULT_INVOICE_TYPES = ["Shipping Line Invoice Reimbursement", "CHA Service Charges"]

CLASSIFICATION_COMPANY_BORNE = "Company Borne"
CLASSIFICATION_RECOVERABLE = "Recoverable"

COMPANY_BORNE_REASONS = ["FSSAI", "Public Holiday", "EDI", "Management Approval", "Others"]
RECOVER_FROM_OPTIONS = ["Supplier", "Importer", "CHA", "Shipping Line", "Other"]

INVOICE_STATUSES = ["Pending", "Verified", "Approved", "Paid", "Rejected"]


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=False)

    invoice_type = db.Column(db.String(100), nullable=False)
    vendor_name = db.Column(db.String(200))
    invoice_number = db.Column(db.String(100))
    invoice_date = db.Column(db.Date)
    invoice_amount = db.Column(db.Numeric(14, 2), default=0)
    gst = db.Column(db.Numeric(14, 2), default=0)
    bill_of_supply = db.Column(db.String(100))
    srn = db.Column(db.String(100))  # SRN - system reference no. shown as "SYS Ref" in note
    cha_ref = db.Column(db.String(100))  # CHA reference number shown as "CHA Ref"
    remarks = db.Column(db.Text)
    status = db.Column(db.String(30), default="Pending")

    classification = db.Column(db.String(30))  # Company Borne / Recoverable
    company_borne_reason = db.Column(db.String(50))
    recover_from = db.Column(db.String(50))
    recover_from_party = db.Column(db.String(200))  # free-text name, e.g. "M/s Avolta"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attachments = db.relationship("Attachment", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")

    def short_label(self):
        return INVOICE_TYPE_SHORT_LABEL.get(self.invoice_type, self.invoice_type)

    def __repr__(self):
        return f"<Invoice {self.invoice_number} {self.invoice_amount}>"
