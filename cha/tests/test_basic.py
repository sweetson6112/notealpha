import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.user import User, Role, ALL_ROLES
from models.shipment import Shipment
from models.invoice import Invoice
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
