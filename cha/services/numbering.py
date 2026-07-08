"""
Handles financial-year detection and generation of the Approval Note
document number in the format:

    CDRSL/BOND/{File Number}/{Financial Year}/{Running Number}

Example: CDRSL/BOND/1849/25-26/01
"""
from datetime import date
from extensions import db
from models.approval_note import FinancialYear


def fy_label_for_date(d: date) -> str:
    """India FY runs Apr 1 - Mar 31. e.g. 2025-09-07 -> '25-26'."""
    if d.month >= 4:
        start_year = d.year
    else:
        start_year = d.year - 1
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"


def get_or_create_financial_year(d: date = None) -> FinancialYear:
    d = d or date.today()
    label = fy_label_for_date(d)
    fy = FinancialYear.query.filter_by(label=label).first()
    if fy:
        return fy

    if d.month >= 4:
        start_year = d.year
    else:
        start_year = d.year - 1
    fy = FinancialYear(
        label=label,
        start_date=date(start_year, 4, 1),
        end_date=date(start_year + 1, 3, 31),
        is_active=True,
        running_number=0,
    )
    db.session.add(fy)
    db.session.commit()
    return fy


def next_running_number(fy: FinancialYear) -> int:
    fy.running_number = (fy.running_number or 0) + 1
    db.session.add(fy)
    db.session.commit()
    return fy.running_number


def generate_document_number(file_number: str, fy: FinancialYear, running_number: int, company_short="CDRSL") -> str:
    return f"{company_short}/BOND/{file_number}/{fy.label}/{running_number:02d}"
