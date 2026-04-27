from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import User, UserRole


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def root():
    if current_user.is_authenticated:
        return redirect(url_for("auth.redirect_dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.redirect_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        user = User.query.filter_by(username=username, activo=True).first()
        if not user or not user.check_password(password):
            flash("Credenciales inválidas", "error")
            return render_template("login.html")
        login_user(user, remember=remember)
        return redirect(url_for("auth.redirect_dashboard"))
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard", methods=["GET"])
@login_required
def redirect_dashboard():
    if current_user.role == UserRole.ADMIN.value:
        return redirect(url_for("admin.dashboard"))
    if current_user.role == UserRole.REPUESTOS.value:
        return redirect(url_for("repuestos.dashboard"))
    if current_user.role == UserRole.RECEPCIONISTA.value:
        return redirect(url_for("recepcionista.dashboard"))
    return redirect(url_for("mecanico.dashboard"))
