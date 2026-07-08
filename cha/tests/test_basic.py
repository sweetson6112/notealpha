import os
import sys
import io
from datetime import date, timedelta
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.user import User, Role, ALL_ROLES
from models.shipment import Shipment
from models.invoice import Invoice
from models.statutory_document import StatutoryDocument
from services.approval_note_generator import generate_approval_note


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        for r in ALL_ROLES:
            db.session.add(Role(name=r))
        db.session.commit()

        admin_role = Role.query.filter_by(name="Administrator").first()
        viewer_role = Role.query.filter_by(name="Viewer").first()

        admin = User(username="admin", full_name="Admin", email="admin@test.com", role_id=admin_role.id)
        admin.set_password("pass123")
        viewer = User(username="viewer", full_name="Viewer", email="viewer@test.com", role_id=viewer_role.id)
        viewer.set_password("pass123")
        db.session.add_all([admin, viewer])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)


def test_login_success(client):
    resp = login(client, "admin", "pass123")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_login_failure(client):
    resp = login(client, "admin", "wrongpass")
    assert b"Invalid username or password" in resp.data


def test_viewer_cannot_create_shipment(client):
    login(client, "viewer", "pass123")
    resp = client.get("/shipments/new")
    assert resp.status_code == 403


def test_admin_can_create_shipment(client):
    login(client, "admin", "pass123")
    resp = client.post("/shipments/new", data={
        "file_number": "9999", "cha_name": "Test CHA",
    }, follow_redirects=True)
    assert resp.status_code == 200
    shipment = Shipment.query.filter_by(file_number="9999").first()
    assert shipment is not None
    # Default invoices auto-created
    assert shipment.invoices.count() == 2


def test_approval_note_generation_and_doc_number_format(app):
    with app.app_context():
        role = Role.query.filter_by(name="Administrator").first()
        user = User.query.filter_by(username="admin").first()
        shipment = Shipment(file_number="1849", cha_name="Chakiat Agencies", created_by_id=user.id)
        db.session.add(shipment)
        db.session.flush()
        db.session.add(Invoice(shipment_id=shipment.id, invoice_type="Shipping Line Invoice Reimbursement",
                                invoice_amount=100.50, classification="Company Borne"))
        db.session.add(Invoice(shipment_id=shipment.id, invoice_type="Demurrage Reimbursement",
                                invoice_amount=50.25, classification="Recoverable", recover_from_party="M/s Test"))
        db.session.commit()

        note = generate_approval_note(shipment, user)
        assert note.document_number.startswith("CDRSL/BOND/1849/")
        assert note.document_number.endswith("/01")
        assert float(note.total_amount) == 150.75
        assert float(note.recoverable_amount) == 50.25
        assert "M/s Chakiat Agencies" in note.subject_text
        assert "Put up for approval" in note.paragraph_4


def test_statutory_document_upload_rejects_non_pdf(client):
    login(client, "admin", "pass123")
    data = {
        "category": "GST Registration Certificate",
        "title": "Test GST Cert",
        "document_file": (io.BytesIO(b"not a real pdf"), "cert.txt"),
    }
    resp = client.post("/statutory-documents/new", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert b"valid PDF" in resp.data
    assert StatutoryDocument.query.count() == 0


def test_statutory_document_upload_accepts_pdf(client):
    login(client, "admin", "pass123")
    data = {
        "category": "GST Registration Certificate",
        "title": "Test GST Cert",
        "document_number": "29AAAAA0000A1Z5",
        "issuing_authority": "GST Department",
        "document_file": (io.BytesIO(b"%PDF-1.4 fake content"), "cert.pdf"),
    }
    resp = client.post("/statutory-documents/new", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    doc = StatutoryDocument.query.filter_by(title="Test GST Cert").first()
    assert doc is not None
    assert doc.stored_filename.endswith(".pdf")
    assert doc.computed_status() == "Active"


def test_statutory_document_expiry_status(app):
    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        expired = StatutoryDocument(
            category="Insurance Policy", title="Expired Policy",
            expiry_date=date(2020, 1, 1),
            original_filename="a.pdf", stored_filename="statutory/a.pdf",
            uploaded_by_id=user.id,
        )
        expiring_soon = StatutoryDocument(
            category="Insurance Policy", title="Soon Policy",
            expiry_date=date.today() + timedelta(days=10),
            original_filename="b.pdf", stored_filename="statutory/b.pdf",
            uploaded_by_id=user.id,
        )
        never_expires = StatutoryDocument(
            category="PAN Card", title="PAN",
            expiry_date=None,
            original_filename="c.pdf", stored_filename="statutory/c.pdf",
            uploaded_by_id=user.id,
        )
        assert expired.computed_status() == "Expired"
        assert expiring_soon.computed_status() == "Expiring Soon"
        assert never_expires.computed_status() == "Active"


def test_viewer_cannot_upload_statutory_document(client):
    login(client, "viewer", "pass123")
    resp = client.get("/statutory-documents/new")
    assert resp.status_code == 403
