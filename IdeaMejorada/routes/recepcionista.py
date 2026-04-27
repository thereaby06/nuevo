import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import ClientePortalAcceso, Moto, MotoEstado, Prioridad, db, log_actividad
from routes.utils import role_required


recepcionista_bp = Blueprint("recepcionista", __name__, url_prefix="/recepcionista")
PLACA_REGEX = re.compile(r"^[A-Z0-9]{2,4}[A-Z0-9-]{2,4}$")


@recepcionista_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("recepcionista", "admin")
def dashboard():
    estado = request.args.get("estado", "").strip()
    query = Moto.query.order_by(Moto.fecha_ingreso.desc())
    if estado:
        query = query.filter(Moto.estado == estado)
    motos = query.all()
    return render_template(
        "recepcionista/dashboard.html",
        motos=motos,
        estados=[s.value for s in MotoEstado],
    )


@recepcionista_bp.route("/motos", methods=["POST"])
@login_required
@role_required("recepcionista", "admin")
def crear_moto():
    placa = request.form.get("placa", "").strip().upper()
    if not PLACA_REGEX.match(placa):
        flash("Placa inválida", "error")
        return redirect(url_for("recepcionista.dashboard"))

    if Moto.query.filter_by(placa=placa).first():
        flash("Ya existe una moto con esa placa", "error")
        return redirect(url_for("recepcionista.dashboard"))

    moto = Moto(
        modelo=request.form.get("modelo", "").strip(),
        placa=placa,
        cliente_nombre=request.form.get("cliente_nombre", "").strip(),
        cliente_telefono=request.form.get("cliente_telefono", "").strip(),
        novedades=request.form.get("novedades", "").strip(),
        prioridad=request.form.get("prioridad", Prioridad.NORMAL.value),
        estado=MotoEstado.DISPONIBLE.value,
        recepcionista_id=current_user.id,
    )
    db.session.add(moto)
    db.session.commit()
    log_actividad(current_user.id, "CREAR_MOTO", f"Moto {moto.placa} registrada")
    flash("Moto ingresada correctamente", "success")
    return redirect(url_for("recepcionista.dashboard"))


@recepcionista_bp.route("/motos/<int:moto_id>/editar", methods=["POST"])
@login_required
@role_required("recepcionista", "admin")
def editar_moto(moto_id: int):
    moto = Moto.query.get_or_404(moto_id)
    if moto.mecanico_asignado_id is not None and current_user.role != "admin":
        flash("No puedes editar una moto asignada", "error")
        return redirect(url_for("recepcionista.dashboard"))

    moto.modelo = request.form.get("modelo", moto.modelo).strip()
    moto.cliente_nombre = request.form.get("cliente_nombre", moto.cliente_nombre).strip()
    moto.cliente_telefono = request.form.get("cliente_telefono", moto.cliente_telefono).strip()
    moto.novedades = request.form.get("novedades", moto.novedades).strip()
    moto.prioridad = request.form.get("prioridad", moto.prioridad)
    db.session.commit()
    log_actividad(current_user.id, "EDITAR_MOTO", f"Moto {moto.placa} actualizada")
    flash("Moto actualizada", "success")
    return redirect(url_for("recepcionista.dashboard"))


@recepcionista_bp.route("/motos/<int:moto_id>/entregar", methods=["POST"])
@login_required
@role_required("recepcionista", "admin")
def entregar_moto(moto_id: int):
    moto = Moto.query.get_or_404(moto_id)
    if moto.estado != MotoEstado.TERMINADA.value:
        flash("Solo se pueden entregar motos terminadas", "error")
        return redirect(url_for("recepcionista.dashboard"))

    moto.estado = MotoEstado.ENTREGADA.value
    moto.fecha_entrega = datetime.utcnow()
    db.session.commit()
    log_actividad(current_user.id, "ENTREGAR_MOTO", f"Moto {moto.placa} entregada")
    flash("Moto entregada al cliente", "success")
    return redirect(url_for("recepcionista.dashboard"))


@recepcionista_bp.route("/motos/<int:moto_id>/crear-acceso-cliente", methods=["POST"])
@login_required
@role_required("recepcionista", "admin")
def crear_acceso_cliente(moto_id: int):
    moto = Moto.query.get_or_404(moto_id)
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if "@" not in email or len(password) < 4:
        flash("Correo inválido o contraseña demasiado corta", "error")
        return redirect(url_for("recepcionista.dashboard"))

    acceso = ClientePortalAcceso.query.filter_by(moto_id=moto.id, email=email).first()
    if acceso:
        acceso.set_password(password)
        acceso.activo = True
        accion = "ACTUALIZAR_ACCESO_CLIENTE"
    else:
        acceso = ClientePortalAcceso(moto_id=moto.id, email=email, activo=True)
        acceso.set_password(password)
        db.session.add(acceso)
        accion = "CREAR_ACCESO_CLIENTE"
    db.session.commit()
    log_actividad(current_user.id, accion, f"Moto {moto.placa} acceso portal para {email}")
    flash("Acceso de cliente creado/actualizado", "success")
    return redirect(url_for("recepcionista.dashboard"))
