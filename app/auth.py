from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from . import db

auth_bp = Blueprint("auth", __name__)


class User(UserMixin):
    def __init__(self, row: dict):
        self.id        = row["user_id"]
        self.username  = row["username"]
        self.full_name = row["full_name"]
        self.email     = row["email"]
        self.role      = row["role_name"]

    @staticmethod
    def get(user_id: int):
        row = db.execute(
            """SELECT u.user_id, u.username, u.full_name, u.email, r.role_name
                 FROM users u JOIN roles r ON r.role_id = u.role_id
                WHERE u.user_id = %s AND u.is_active = TRUE""",
            (user_id,), fetch="one")
        return User(row) if row else None

    @staticmethod
    def by_username(username: str):
        return db.execute(
            """SELECT u.user_id, u.username, u.full_name, u.email,
                      u.password_hash, r.role_name
                 FROM users u JOIN roles r ON r.role_id = u.role_id
                WHERE u.username = %s""",
            (username,), fetch="one")


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard.index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = User.by_username(username)
        if row and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            flash(f"Welcome, {row['full_name']}!", "success")
            return redirect(url_for("dashboard.index"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
