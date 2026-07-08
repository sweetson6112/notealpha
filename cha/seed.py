"""
Seeds the database with:
  - The 6 roles
  - One demo user per role (username = role slug, password = "Password@123")
  - The current financial year
  - A demo shipment + invoices + generated Approval Note that mirrors
    the reference sample document, so the app is immediately explorable.

Run with:  python seed.py
"""
from datetime import date
import os
from app import create_app
from extensions import db
from models.user import User, Role, ALL_ROLES
from models.shipment import Shipment
from models.invoice import Invoice
from models.statutory_document import StatutoryDocument
from services.approval_note_generator import generate_approval_note

DEMO_USERS = [
    ("admin", "Administrator", "System Administrator", None),
    ("accounts", "Accounts Officer", "Accounts Officer", "Sr. Superintendent Duty Free"),
    ("bondsupt", "Bond Superintendent", "Bond Superintendent", "Sr. Superintendent SG Duty Free"),
    ("manager", "Manager", "DGM (CDRSL)", "DGM (CDRSL)"),
    ("finance", "Finance", "AGM Finance", "AGM (FIN)"),
    ("viewer", "Viewer", "Read Only Viewer", None),
]

DEFAULT_PASSWORD = "Password@123"


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Roles
        role_objs = {}
        for r in ALL_ROLES:
            role = Role.query.filter_by(name=r).first()
            if not role:
                role = Role(name=r, description=r)
                db.session.add(role)
                db.session.flush()
            role_objs[r] = role
        db.session.commit()

        # Users
        for username, role_name, full_name, designation in DEMO_USERS:
            if not User.query.filter_by(username=username).first():
                u = User(username=username, full_name=full_name,
                         email=f"{username}@cdrsl.example", role_id=role_objs[role_name].id,
                         designation=designation, is_active_flag=True)
                u.set_password(DEFAULT_PASSWORD)
                db.session.add(u)
        db.session.commit()
        print(f"Seeded {len(DEMO_USERS)} demo users. Password for all: {DEFAULT_PASSWORD}")

        # Demo shipment mirroring the sample Approval Note
        if not Shipment.query.filter_by(file_number="1849").first():
            admin_user = User.query.filter_by(username="admin").first()
            shipment = Shipment(
                file_number="1849",
                grn_number="186",
                boe_number="4153041",
                supplier_invoice_ref="1329026743",
                supplier_name="Avolta",
                cha_name="Chakiat Agencies",
                shipping_line="DHL",
                arrival_date=date(2025, 9, 7),
                clearance_date=date(2025, 9, 10),
                created_by_id=admin_user.id,
            )
            db.session.add(shipment)
            db.session.flush()

            invoices = [
                Invoice(shipment_id=shipment.id, invoice_type="Shipping Line Invoice Reimbursement",
                        vendor_name="DHL", invoice_number="IEOAEH06", invoice_amount=36096.22,
                        cha_ref="25023097 7", srn="PSI-208", status="Verified",
                        classification="Company Borne", company_borne_reason="EDI"),
                Invoice(shipment_id=shipment.id, invoice_type="Demurrage Reimbursement",
                        vendor_name="DHL", invoice_number="IEOAEH24", invoice_amount=34630.16,
                        cha_ref="25023097 7", srn="PSI-209", status="Verified",
                        classification="Recoverable", recover_from="Supplier", recover_from_party="M/s Avolta"),
                Invoice(shipment_id=shipment.id, invoice_type="CHA Service Charges",
                        vendor_name="CHAKIATH", invoice_number="250202743", invoice_amount=13901.56,
                        srn="PSI-210", status="Verified", classification="Company Borne",
                        company_borne_reason="Management Approval"),
            ]
            db.session.add_all(invoices)
            db.session.commit()

            note = generate_approval_note(shipment, admin_user, doc_date=date(2025, 10, 8))
            print(f"Seeded demo shipment 1849 with Approval Note {note.document_number}")
        else:
            print("Demo shipment 1849 already exists, skipping.")

        # Demo statutory documents
        if StatutoryDocument.query.count() == 0:
            admin_user = User.query.filter_by(username="admin").first()
            upload_dir = os.path.join(app.config["UPLOAD_FOLDER"], "statutory")
            os.makedirs(upload_dir, exist_ok=True)

            minimal_pdf = (
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
                b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\n%%EOF"
            )

            demo_docs = [
                dict(category="Customs Bonded Warehouse License", title="CDRSL Bond Warehouse License 2024-2027",
                     document_number="BWL/2024/0417", issuing_authority="Commissioner of Customs",
                     issue_date=date(2024, 4, 1), expiry_date=date(2027, 3, 31),
                     filename="bond_warehouse_license.pdf"),
                dict(category="Import Export Code (IEC)", title="IEC Certificate - CDRSL",
                     document_number="IEC0198765432", issuing_authority="DGFT",
                     issue_date=date(2020, 6, 15), expiry_date=None,
                     filename="iec_certificate.pdf"),
                dict(category="GST Registration Certificate", title="GST Registration - CDRSL Bond Warehouse",
                     document_number="29ABCDE1234F1Z5", issuing_authority="GST Department",
                     issue_date=date(2019, 7, 1), expiry_date=None,
                     filename="gst_certificate.pdf"),
                dict(category="Insurance Policy", title="Warehouse Fire & Burglary Insurance FY25-26",
                     document_number="INS/CDRSL/2025/551", issuing_authority="National Insurance Co.",
                     issue_date=date(2025, 4, 1), expiry_date=date(2026, 3, 31),
                     filename="insurance_policy.pdf"),
            ]

            for d in demo_docs:
                stored_name = f"seed_{d['filename']}"
                stored_rel = os.path.join("statutory", stored_name)
                with open(os.path.join(upload_dir, stored_name), "wb") as f:
                    f.write(minimal_pdf)
                db.session.add(StatutoryDocument(
                    category=d["category"], title=d["title"], document_number=d["document_number"],
                    issuing_authority=d["issuing_authority"], issue_date=d["issue_date"], expiry_date=d["expiry_date"],
                    original_filename=d["filename"], stored_filename=stored_rel,
                    uploaded_by_id=admin_user.id,
                ))
            db.session.commit()
            print(f"Seeded {len(demo_docs)} demo statutory documents.")
        else:
            print("Statutory documents already exist, skipping.")


if __name__ == "__main__":
    run()
