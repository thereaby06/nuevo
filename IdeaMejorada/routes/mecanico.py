from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Moto, MotoEstado, PuntuacionMecanico, db, log_actividad
from routes.utils import role_required


mecanico_bp = Blueprint("mecanico", __name__, url_prefix="/mecanico")


@mecanico_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("mecanico", "admin")
def dashboard():
    disponibles = Moto.query.filter(
        Moto.estado.in_([MotoEstado.DISPONIBLE.value, MotoEstado.LIBERADA.value]),
        Moto.mecanico_asignado_id.is_(None),
    ).order_by(Moto.prioridad.desc(), Moto.fecha_ingreso.asc())

    mi_moto = Moto.query.filter(
        Moto.mecanico_asignado_id == current_user.id,
        Moto.estado.in_(
            [
                MotoEstado.ASIGNADA.value,
                MotoEstado.EN_PROCESO.value,
                MotoEstado.PENDIENTE_REPUESTOS.value,
            ]
        ),
    ).first()
    historial = Moto.query.filter_by(
        mecanico_asignado_id=current_user.id, estado=MotoEstado.TERMINADA.value
    ).order_by(Moto.fecha_terminacion.desc())
    return render_template(
        "mecanico/dashboard.html",
        disponibles=disponibles.all(),
        mi_moto=mi_moto,
        historial=historial.all(),
    )


@mecanico_bp.route("/motos/<int:moto_id>/elegir", methods=["POST"])
@login_required
@role_required("mecanico", "admin")
def elegir_moto(moto_id: int):
    moto_activa = Moto.query.filter(
        Moto.mecanico_asignado_id == current_user.id,
        Moto.estado.in_(
            [
                MotoEstado.ASIGNADA.value,
                MotoEstado.EN_PROCESO.value,
                MotoEstado.PENDIENTE_REPUESTOS.value,
            ]
        ),
    ).first()
    if moto_activa:
        flash("Ya tienes una moto asignada. Debes liberarla o terminarla primero.", "error")
        return redirect(url_for("mecanico.dashboard"))

    moto = Moto.query.get_or_404(moto_id)
    if moto.mecanico_asignado_id is not None or moto.estado not in [
        MotoEstado.DISPONIBLE.value,
        MotoEstado.LIBERADA.value,
    ]:
        flash("La moto ya fue tomada por otro mecánico", "error")
        return redirect(url_for("mecanico.dashboard"))

    moto.mecanico_asignado_id = current_user.id
    moto.estado = MotoEstado.ASIGNADA.value
    moto.fecha_asignacion = datetime.utcnow()
    db.session.commit()
    log_actividad(current_user.id, "ASIGNAR_MOTO", f"Moto {moto.placa} asignada")
    flash("Moto asignada correctamente", "success")
    return redirect(url_for("mecanico.dashboard"))


@mecanico_bp.route("/motos/<int:moto_id>/liberar", methods=["POST"])
@login_required
@role_required("mecanico", "admin")
def liberar_moto(moto_id: int):
    moto = Moto.query.get_or_404(moto_id)
    if moto.mecanico_asignado_id != current_user.id and current_user.role != "admin":
        flash("No puedes liberar una moto que no tienes asignada", "error")
        return redirect(url_for("mecanico.dashboard"))

    moto.mecanico_asignado_id = None
    moto.estado = MotoEstado.LIBERADA.value
    db.session.commit()
    log_actividad(current_user.id, "LIBERAR_MOTO", f"Moto {moto.placa} liberada")
    flash("Moto liberada y disponible para otros mecánicos", "success")
    return redirect(url_for("mecanico.dashboard"))


@mecanico_bp.route("/motos/<int:moto_id>/estado", methods=["POST"])
@login_required
@role_required("mecanico", "admin")
def actualizar_estado(moto_id: int):
    moto = Moto.query.get_or_404(moto_id)
    if moto.mecanico_asignado_id != current_user.id and current_user.role != "admin":
        flash("No puedes modificar esta moto", "error")
        return redirect(url_for("mecanico.dashboard"))

    nuevo_estado = request.form.get("estado")
    notas = request.form.get("notas_trabajo", "").strip()
    permitidos = {
        MotoEstado.EN_PROCESO.value,
        MotoEstado.PENDIENTE_REPUESTOS.value,
        MotoEstado.TERMINADA.value,
    }
    if nuevo_estado not in permitidos:
        flash("Estado inválido", "error")
        return redirect(url_for("mecanico.dashboard"))

    moto.estado = nuevo_estado
    if notas:
        moto.notas_trabajo = notas
    if nuevo_estado == MotoEstado.TERMINADA.value:
        moto.fecha_terminacion = datetime.utcnow()
        db.session.add(
            PuntuacionMecanico(
                mecanico_id=current_user.id,
                puntos=10,
                motivo=f"Moto {moto.placa} terminada",
            )
        )
    db.session.commit()
    log_actividad(
        current_user.id, "CAMBIAR_ESTADO_MOTO", f"Moto {moto.placa} -> {nuevo_estado}"
    )
    flash("Estado actualizado", "success")
    return redirect(url_for("mecanico.dashboard"))
