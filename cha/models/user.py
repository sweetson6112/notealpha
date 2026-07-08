from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

ROLE_ADMIN = "Administrator"
ROLE_ACCOUNTS = "Accounts Officer"
ROLE_BOND_SUPT = "Bond Superintendent"
ROLE_MANAGER = "Manager"
ROLE_FINANCE = "Finance"
ROLE_VIEWER = "Viewer"

ALL_ROLES = [ROLE_ADMIN, ROLE_ACCOUNTS, ROLE_BOND_SUPT, ROLE_MANAGER, ROLE_FINANCE, ROLE_VIEWER]


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    designation = db.Column(db.String(150))  # e.g. "Sr. Superintendent Duty Free" - used in signature block
    is_active_flag = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_flag

    def has_role(self, *role_names):
        return self.role and self.role.name in role_names

    def __repr__(self):
        return f"<User {self.username}>"
