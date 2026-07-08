from datetime import date, datetime
from extensions import db

# Standard statutory / compliance documents relevant to a CHA Bond Warehouse operation.
# "Other" allows ad-hoc categories not covered by the fixed list.
STATUTORY_DOC_CATEGORIES = [
    "Customs Bonded Warehouse License",
    "Bond / Bank Guarantee",
    "CHA License",
    "Import Export Code (IEC)",
    "GST Registration Certificate",
    "PAN Card",
    "Company Incorporation Certificate",
    "AEO Certificate",
    "Fire Safety NOC",
    "Pollution Control NOC",
    "Insurance Policy",
    "Statutory Audit Report",
    "Other",
]

DOC_STATUS_ACTIVE = "Active"
DOC_STATUS_EXPIRING_SOON = "Expiring Soon"
DOC_STATUS_EXPIRED = "Expired"

EXPIRING_SOON_WINDOW_DAYS = 30


class StatutoryDocument(db.Model):
    __tablename__ = "statutory_documents"
    id = db.Column(db.Integer, primary_key=True)

    category = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    document_number = db.Column(db.String(100))
    issuing_authority = db.Column(db.String(200))
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)  # nullable: some documents (e.g. PAN, incorporation cert) never expire
    remarks = db.Column(db.Text)

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_by = db.relationship("User")

    def computed_status(self):
        if not self.expiry_date:
            return DOC_STATUS_ACTIVE
        today = date.today()
        if self.expiry_date < today:
            return DOC_STATUS_EXPIRED
        if (self.expiry_date - today).days <= EXPIRING_SOON_WINDOW_DAYS:
            return DOC_STATUS_EXPIRING_SOON
        return DOC_STATUS_ACTIVE

    def __repr__(self):
        return f"<StatutoryDocument {self.category}:{self.title}>"
