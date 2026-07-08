from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Role, ALL_ROLES
from models.approval_note import FinancialYear
from models.misc import ChargeType, AuditLog
from utils.decorators import roles_required
from services.numbering import fy_label_for_date
from services.audit import log_action

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@login_required
def _require_admin():
    if not current_user.has_role("Administrator"):
        from flask import abort
        abort(403)


@bp.route("/")
def index():
    return redirect(url_for("admin.users"))


@bp.route("/users")
def users():
    all_users = User.query.order_by(User.username).all()
    roles = Role.query.all()
    return render_template("admin/users.html", users=all_users, roles=roles)


@bp.route("/users/new", methods=["POST"])
def new_user():
    username = request.form.get("username", "").strip()
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for("admin.users"))
    user = User(
        username=username,
        full_name=request.form.get("full_name"),
        email=request.form.get("email"),
        role_id=request.form.get("role_id"),
        designation=request.form.get("designation"),
        is_active_flag=True,
    )
    user.set_password(request.form.get("password") or "ChangeMe@123")
    db.session.add(user)
    db.session.commit()
    log_action("CREATE_USER", "User", user.id, username)
    flash(f"User {username} created.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_flag = not user.is_active_flag
    db.session.commit()
    log_action("TOGGLE_USER", "User", user.id, str(user.is_active_flag))
    flash(f"User {user.username} is now {'active' if user.is_active_flag else 'inactive'}.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("password") or "ChangeMe@123"
    user.set_password(new_password)
    db.session.commit()
    log_action("RESET_PASSWORD", "User", user.id)
    flash(f"Password reset for {user.username}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/financial-years")
def financial_years():
    fys = FinancialYear.query.order_by(FinancialYear.start_date.desc()).all()
    return render_template("admin/financial_years.html", fys=fys, current_label=fy_label_for_date(date.today()))


@bp.route("/financial-years/<int:fy_id>/set-running", methods=["POST"])
def set_running_number(fy_id):
    fy = FinancialYear.query.get_or_404(fy_id)
    try:
        fy.running_number = int(request.form.get("running_number", fy.running_number))
    except ValueError:
        flash("Invalid number.", "danger")
        return redirect(url_for("admin.financial_years"))
    db.session.commit()
    log_action("SET_RUNNING_NUMBER", "FinancialYear", fy.id, str(fy.running_number))
    flash(f"Running number for FY {fy.label} set to {fy.running_number}.", "success")
    return redirect(url_for("admin.financial_years"))


@bp.route("/charge-types")
def charge_types():
    types = ChargeType.query.order_by(ChargeType.name).all()
    return render_template("admin/charge_types.html", types=types)


@bp.route("/charge-types/new", methods=["POST"])
def new_charge_type():
    name = request.form.get("name", "").strip()
    if name and not ChargeType.query.filter_by(name=name).first():
        db.session.add(ChargeType(name=name, short_label=request.form.get("short_label"), is_active=True))
        db.session.commit()
        flash("Charge type added.", "success")
    return redirect(url_for("admin.charge_types"))


@bp.route("/audit-log")
def audit_log():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template("admin/audit_log.html", logs=logs)
