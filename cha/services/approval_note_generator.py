"""
Generates the content of an Approval Note (subject line, paragraphs 1-4,
and computed totals) from a Shipment and its Invoices, following the exact
wording patterns of the reference sample.
"""
from datetime import date
from decimal import Decimal
from extensions import db
from models.approval_note import ApprovalNote
from models.invoice import CLASSIFICATION_RECOVERABLE, CLASSIFICATION_COMPANY_BORNE
from services.numbering import get_or_create_financial_year, next_running_number, generate_document_number


def inr(amount) -> str:
    """Format a number the Indian way with a rupee symbol, e.g. ₹84,627.94"""
    amount = Decimal(amount or 0)
    neg = amount < 0
    amount = abs(amount)
    s = f"{amount:,.2f}"
    int_part, dec_part = s.split(".")
    int_part = int_part.replace(",", "")
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups + [last3])
    formatted = f"₹{int_part}.{dec_part}"
    return f"-{formatted}" if neg else formatted


def build_subject(shipment) -> str:
    parts = [f"Payment of Clearance Charges to M/s {shipment.cha_name} \u2013 our CHA. ["]
    system_bits = []
    if shipment.grn_number:
        system_bits.append(f"GRN-{shipment.grn_number}")
    if shipment.boe_number:
        system_bits.append(f"BOE-{shipment.boe_number}")
    if shipment.supplier_invoice_ref:
        system_bits.append(f"Supplier Invoice-{shipment.supplier_invoice_ref}")
    subject = parts[0] + "SYSTEM " + " ".join(system_bits)
    return subject


def build_paragraph_1(shipment) -> str:
    ref = shipment.supplier_invoice_ref or shipment.file_number
    return (
        f"A shipment vide {ref} was cleared and GRN was completed. Our CHA has raised "
        f"the charges incurred for the shipment clearance and the invoice details are "
        f"shown in Table No.1 below."
    )


RECOVERABLE_CHARGE_NOTES = {
    "Detention Reimbursement": "detention charges",
    "Demurrage Reimbursement": "demurrage charges",
    "Delivery Order Revalidation Charges": "DO revalidation charges",
    "Late Filing Charges": "late filing charges",
    "Plugging Charges": "plugging charges",
    "Handling Charges": "handling charges",
}


def build_paragraph_2(shipment, invoices) -> str:
    """Auto-explanatory paragraph for recoverable charges, editable by the user afterwards."""
    recoverable = [i for i in invoices if i.classification == CLASSIFICATION_RECOVERABLE]
    if not recoverable:
        return ""

    charge_names = []
    for inv in recoverable:
        label = RECOVERABLE_CHARGE_NOTES.get(inv.invoice_type, inv.short_label().lower())
        if label not in charge_names:
            charge_names.append(label)
    charges_text = ", ".join(charge_names[:-1]) + (" and " + charge_names[-1] if len(charge_names) > 1 else charge_names[0])

    total_recoverable = sum(Decimal(i.invoice_amount or 0) for i in recoverable)
    parties = sorted(set(i.recover_from_party for i in recoverable if i.recover_from_party))
    party_text = " and ".join(parties) if parties else "the responsible party"

    arrival = shipment.arrival_date.strftime("%d-%m-%Y") if shipment.arrival_date else "the date of arrival"

    return (
        f"Refer Table. The above consignment arrived on {arrival}, {charges_text} amounting to "
        f"{inr(total_recoverable)} were incurred. We had earlier communicated the requirement for a minimum "
        f"free period to complete mandatory clearance procedures and prevent additional charges. In this case "
        f"the free period provided was not sufficient for completing clearance. Hence, this amount will be "
        f"charged to {party_text}'s account, and the same has been communicated to them and a copy of the "
        f"correspondence is attached for your reference."
    )


def build_paragraph_4(shipment, total_amount, recoverable_amount, invoices) -> str:
    parties = sorted(set(i.recover_from_party for i in invoices
                          if i.classification == CLASSIFICATION_RECOVERABLE and i.recover_from_party))
    party_text = " and ".join(parties) if parties else "the responsible party"

    charge_labels = []
    for inv in invoices:
        if inv.classification == CLASSIFICATION_RECOVERABLE:
            label = RECOVERABLE_CHARGE_NOTES.get(inv.invoice_type, inv.short_label().lower())
            if label not in charge_labels:
                charge_labels.append(label)
    charges_desc = " and ".join(charge_labels) if charge_labels else "recoverable charges"

    text = f"Put up for approval to make full payment of {inr(total_amount)} to M/s {shipment.cha_name}"
    if recoverable_amount and recoverable_amount > 0:
        text += f" and recover an amount of {inr(recoverable_amount)} from {party_text} as {charges_desc}."
    else:
        text += "."
    return text


def compute_totals(invoices):
    total = sum(Decimal(i.invoice_amount or 0) for i in invoices)
    recoverable = sum(Decimal(i.invoice_amount or 0) for i in invoices if i.classification == CLASSIFICATION_RECOVERABLE)
    company_borne = sum(Decimal(i.invoice_amount or 0) for i in invoices if i.classification == CLASSIFICATION_COMPANY_BORNE)
    payable_to_cha = total  # full invoice value is paid out to the CHA; recoverable part is later recovered
    return total, recoverable, company_borne, payable_to_cha


def generate_approval_note(shipment, created_by, doc_date: date = None) -> ApprovalNote:
    """Creates (in Draft state) a new ApprovalNote for the shipment, auto-filling
    the document number, subject, paragraphs 1/2/4, and computed totals.
    Paragraph 3 is left blank (optional user remarks)."""
    doc_date = doc_date or date.today()
    invoices = list(shipment.invoices)

    fy = get_or_create_financial_year(doc_date)
    running_number = next_running_number(fy)
    doc_number = generate_document_number(shipment.file_number, fy, running_number)

    total, recoverable, company_borne, payable_to_cha = compute_totals(invoices)

    note = ApprovalNote(
        shipment_id=shipment.id,
        document_number=doc_number,
        financial_year_id=fy.id,
        running_number=running_number,
        document_date=doc_date,
        subject_text=build_subject(shipment),
        paragraph_1=build_paragraph_1(shipment),
        paragraph_2=build_paragraph_2(shipment, invoices),
        paragraph_3="",
        paragraph_4=build_paragraph_4(shipment, total, recoverable, invoices),
        total_amount=total,
        recoverable_amount=recoverable,
        company_borne_amount=company_borne,
        payable_to_cha=payable_to_cha,
        status="Draft",
        created_by_id=created_by.id if created_by else None,
    )
    db.session.add(note)
    db.session.commit()
    return note


def regenerate_paragraphs(note: ApprovalNote):
    """Recompute paragraphs/totals after invoices change, without touching the
    already-assigned document number, or any paragraph the user has manually edited
    (tracked via a simple heuristic: only regenerate if paragraph is empty or matches
    the previous auto-generated text -- for simplicity here we always allow an explicit
    'Regenerate' action from the UI, which calls this directly)."""
    shipment = note.shipment
    invoices = list(shipment.invoices)
    total, recoverable, company_borne, payable_to_cha = compute_totals(invoices)
    note.subject_text = build_subject(shipment)
    note.paragraph_1 = build_paragraph_1(shipment)
    note.paragraph_2 = build_paragraph_2(shipment, invoices)
    note.paragraph_4 = build_paragraph_4(shipment, total, recoverable, invoices)
    note.total_amount = total
    note.recoverable_amount = recoverable
    note.company_borne_amount = company_borne
    note.payable_to_cha = payable_to_cha
    db.session.add(note)
    db.session.commit()
    return note
