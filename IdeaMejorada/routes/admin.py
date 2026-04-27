from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from models import ActividadLog, Moto, MotoEstado, User, UserRole, db, log_actividad
from routes.utils import role_required


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    hoy = date.today()
    motos_hoy = Moto.query.filter(func.date(Moto.fecha_ingreso) == hoy).count()
    en_proceso = Moto.query.filter(Moto.estado == MotoEstado.EN_PROCESO.value).count()
    terminadas_hoy = Moto.query.filter(
        func.date(Moto.fecha_terminacion) == hoy,
        Moto.estado == MotoEstado.TERMINADA.value,
    ).count()
    mecanicos_activos = User.query.filter_by(role=UserRole.MECANICO.value, activo=True).count()

    estados_count = (
        db.session.query(Moto.estado, func.count(Moto.id))
        .group_by(Moto.estado)
        .order_by(Moto.estado.asc())
        .all()
    )
    productividad = (
        db.session.query(User.nombre_completo, func.count(Moto.id))
        .join(Moto, Moto.mecanico_asignado_id == User.id, isouter=True)
        .filter(User.role == UserRole.MECANICO.value)
        .group_by(User.id)
        .all()
    )
    usuarios = User.query.order_by(User.created_at.desc()).all()
    motos_recientes = Moto.query.order_by(Moto.fecha_ingreso.desc()).limit(10).all()
    logs = ActividadLog.query.order_by(ActividadLog.timestamp.desc()).limit(20).all()

    return render_template(
        "admin/dashboard.html",
        motos_hoy=motos_hoy,
        en_proceso=en_proceso,
        terminadas_hoy=terminadas_hoy,
        mecanicos_activos=mecanicos_activos,
        estados_count=estados_count,
        productividad=productividad,
        usuarios=usuarios,
        motos_recientes=motos_recientes,
        logs=logs,
    )


@admin_bp.route("/usuarios", methods=["POST"])
@login_required
@role_required("admin")
def crear_usuario():
    username = request.form.get("username", "").strip()
    if User.query.filter_by(username=username).first():
        flash("El usuario ya existe", "error")
        return redirect(url_for("admin.dashboard"))

    user = User(
        username=username,
        role=request.form.get("role", UserRole.MECANICO.value),
        nombre_completo=request.form.get("nombre_completo", "").strip(),
        telefono=request.form.get("telefono", "").strip(),
        activo=True,
    )
    user.set_password(request.form.get("password", "123456"))
    db.session.add(user)
    db.session.commit()
    log_actividad(current_user.id, "CREAR_USUARIO", f"Usuario {user.username} creado")
    flash("Usuario creado", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/usuarios/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_usuario(user_id: int):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("No puedes desactivar tu propio usuario", "error")
        return redirect(url_for("admin.dashboard"))

    user.activo = not user.activo
    db.session.commit()
    accion = "ACTIVAR_USUARIO" if user.activo else "DESACTIVAR_USUARIO"
    log_actividad(current_user.id, accion, f"Usuario {user.username} estado={user.activo}")
    flash("Estado de usuario actualizado", "success")
    return redirect(url_for("admin.dashboard"))
