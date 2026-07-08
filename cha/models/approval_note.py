from datetime import datetime
from extensions import db

WORKFLOW_STATES = [
    "Draft",
    "Submitted",
    "Accounts Verification",
    "Manager Approval",
    "Finance Approval",
    "Paid",
    "Completed",
]


class ApprovalNote(db.Model):
    __tablename__ = "approval_notes"
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=False)
    document_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    financial_year_id = db.Column(db.Integer, db.ForeignKey("financial_years.id"))
    running_number = db.Column(db.Integer, nullable=False)

    document_date = db.Column(db.Date, default=datetime.utcnow)

    subject_text = db.Column(db.Text)
    paragraph_1 = db.Column(db.Text)
    paragraph_2 = db.Column(db.Text)
    paragraph_3 = db.Column(db.Text)
    paragraph_4 = db.Column(db.Text)

    total_amount = db.Column(db.Numeric(14, 2), default=0)
    recoverable_amount = db.Column(db.Numeric(14, 2), default=0)
    company_borne_amount = db.Column(db.Numeric(14, 2), default=0)
    payable_to_cha = db.Column(db.Numeric(14, 2), default=0)

    status = db.Column(db.String(50), default="Draft")

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    financial_year = db.relationship("FinancialYear")
    history = db.relationship("ApprovalHistory", backref="approval_note", lazy="dynamic",
                               order_by="ApprovalHistory.action_at", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ApprovalNote {self.document_number}>"


class ApprovalHistory(db.Model):
    __tablename__ = "approval_history"
    id = db.Column(db.Integer, primary_key=True)
    approval_note_id = db.Column(db.Integer, db.ForeignKey("approval_notes.id"), nullable=False)
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text)
    action_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action_at = db.Column(db.DateTime, default=datetime.utcnow)

    action_by = db.relationship("User")


class FinancialYear(db.Model):
    __tablename__ = "financial_years"
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(10), unique=True, nullable=False)  # e.g. "25-26"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    running_number = db.Column(db.Integer, default=0)  # last used running number for this FY

    def __repr__(self):
        return f"<FinancialYear {self.label}>"
