from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import ClientePortalAcceso, Moto


cliente_bp = Blueprint("cliente", __name__, url_prefix="/cliente")


@cliente_bp.route("/estado", methods=["GET"])
def consultar_estado():
    placa = (request.args.get("placa") or "").strip().upper()
    moto = None
    if placa:
        moto = Moto.query.filter_by(placa=placa).first()
    return render_template("cliente/estado.html", placa=placa, moto=moto)


@cliente_bp.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    if session.get("cliente_email"):
        return redirect(url_for("cliente.portal_dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        acceso = (
            ClientePortalAcceso.query.filter_by(email=email, activo=True)
            .order_by(ClientePortalAcceso.created_at.desc())
            .first()
        )
        if not acceso or not acceso.check_password(password):
            flash("Credenciales de cliente inválidas", "error")
            return render_template("cliente/login.html")
        session["cliente_email"] = email
        return redirect(url_for("cliente.portal_dashboard"))
    return render_template("cliente/login.html")


@cliente_bp.route("/portal/logout", methods=["POST"])
def portal_logout():
    session.pop("cliente_email", None)
    flash("Sesión de cliente cerrada", "success")
    return redirect(url_for("cliente.portal_login"))


@cliente_bp.route("/portal/dashboard", methods=["GET"])
def portal_dashboard():
    email = session.get("cliente_email")
    if not email:
        return redirect(url_for("cliente.portal_login"))

    accesos = (
        ClientePortalAcceso.query.filter_by(email=email, activo=True)
        .order_by(ClientePortalAcceso.created_at.desc())
        .all()
    )
    motos = [a.moto for a in accesos if a.moto]
    return render_template("cliente/dashboard.html", email=email, motos=motos)
