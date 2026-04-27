import csv
import os
import shutil
from datetime import datetime
from io import StringIO

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from models import (
    Cita,
    CitaEstado,
    Cotizacion,
    CotizacionEstado,
    CotizacionItem,
    EstadoPago,
    EvidenciaFoto,
    Factura,
    Moto,
    MotoEstado,
    MotoRepuestoUso,
    PuntuacionMecanico,
    Repuesto,
    User,
    UserRole,
    db,
    log_actividad,
)
from routes.utils import role_required


operaciones_bp = Blueprint("operaciones", __name__, url_prefix="/operaciones")


@operaciones_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin", "recepcionista")
def dashboard():
    repuestos = Repuesto.query.order_by(Repuesto.nombre.asc()).all()
    alertas_stock = Repuesto.query.filter(Repuesto.stock_actual <= Repuesto.stock_minimo).all()
    cotizaciones = Cotizacion.query.order_by(Cotizacion.created_at.desc()).limit(20).all()
    facturas = Factura.query.order_by(Factura.fecha_emision.desc()).limit(20).all()
    cotizaciones_facturadas = {f.cotizacion_id for f in facturas if f.cotizacion_id}
    citas = Cita.query.order_by(Cita.fecha_hora.asc()).limit(25).all()
    motos = Moto.query.order_by(Moto.fecha_ingreso.desc()).limit(50).all()
    evidencias = EvidenciaFoto.query.order_by(EvidenciaFoto.created_at.desc()).limit(30).all()

    ranking = (
        db.session.query(User.nombre_completo, func.coalesce(func.sum(PuntuacionMecanico.puntos), 0))
        .join(PuntuacionMecanico, PuntuacionMecanico.mecanico_id == User.id, isouter=True)
        .filter(User.role == UserRole.MECANICO.value)
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(PuntuacionMecanico.puntos), 0).desc())
        .all()
    )
    return render_template(
        "operaciones/dashboard.html",
        repuestos=repuestos,
        alertas_stock=alertas_stock,
        cotizaciones=cotizaciones,
        facturas=facturas,
        cotizaciones_facturadas=cotizaciones_facturadas,
        citas=citas,
        motos=motos,
        evidencias=evidencias,
        ranking=ranking,
        cita_estados=[x.value for x in CitaEstado],
    )


@operaciones_bp.route("/repuestos", methods=["POST"])
@login_required
@role_required("admin", "repuestos")
def crear_repuesto():
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("Nombre de repuesto requerido", "error")
        destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
        return redirect(url_for(destino))
    if Repuesto.query.filter_by(nombre=nombre).first():
        flash("Ese repuesto ya existe", "error")
        destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
        return redirect(url_for(destino))
    repuesto = Repuesto(
        nombre=nombre,
        categoria=request.form.get("categoria", "General").strip() or "General",
        stock_actual=request.form.get("stock_actual", type=int) or 0,
        stock_minimo=request.form.get("stock_minimo", type=int) or 0,
        costo_unitario=request.form.get("costo_unitario", type=float) or 0.0,
    )
    db.session.add(repuesto)
    db.session.commit()
    log_actividad(current_user.id, "CREAR_REPUESTO", f"Repuesto {repuesto.nombre}")
    flash("Repuesto creado", "success")
    destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
    return redirect(url_for(destino))


@operaciones_bp.route("/motos/<int:moto_id>/usar-repuesto", methods=["POST"])
@operaciones_bp.route("/usar-repuesto", methods=["POST"])
@login_required
@role_required("admin", "repuestos")
def usar_repuesto(moto_id: int | None = None):
    if moto_id is None:
        moto_id = request.form.get("moto_id", type=int)
    if not moto_id:
        flash("Debes seleccionar una moto", "error")
        destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
        return redirect(url_for(destino))

    moto = Moto.query.get_or_404(moto_id)
    repuesto = Repuesto.query.get_or_404(request.form.get("repuesto_id", type=int))
    cantidad = max(1, request.form.get("cantidad", type=int) or 1)

    if repuesto.stock_actual < cantidad:
        flash("Stock insuficiente para ese repuesto", "error")
        destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
        return redirect(url_for(destino))

    repuesto.stock_actual -= cantidad
    db.session.add(
        MotoRepuestoUso(
            moto_id=moto.id,
            repuesto_id=repuesto.id,
            cantidad=cantidad,
            costo_unitario=repuesto.costo_unitario,
        )
    )
    db.session.commit()
    log_actividad(
        current_user.id,
        "USAR_REPUESTO",
        f"Moto {moto.placa}: {cantidad} x {repuesto.nombre}",
    )
    flash("Repuesto vinculado a la moto", "success")
    destino = "repuestos.dashboard" if current_user.role == "repuestos" else "operaciones.dashboard"
    return redirect(url_for(destino))


@operaciones_bp.route("/repuestos/<int:repuesto_id>/ajustar-stock", methods=["POST"])
@login_required
@role_required("admin", "repuestos")
def ajustar_stock(repuesto_id: int):
    repuesto = Repuesto.query.get_or_404(repuesto_id)
    ajuste = request.form.get("ajuste", type=int)
    motivo = (request.form.get("motivo") or "").strip()
    if ajuste is None or ajuste == 0:
        flash("El ajuste debe ser distinto de cero", "error")
        return redirect(url_for("repuestos.dashboard"))

    nuevo_stock = repuesto.stock_actual + ajuste
    if nuevo_stock < 0:
        flash("El ajuste deja stock negativo, revisa el valor", "error")
        return redirect(url_for("repuestos.dashboard"))

    repuesto.stock_actual = nuevo_stock
    db.session.commit()
    log_actividad(
        current_user.id,
        "AJUSTE_STOCK",
        f"Repuesto {repuesto.nombre}: ajuste={ajuste}, stock={repuesto.stock_actual}, motivo={motivo or 'N/A'}",
    )
    flash("Stock ajustado correctamente", "success")
    return redirect(url_for("repuestos.dashboard"))


@operaciones_bp.route("/cotizaciones", methods=["POST"])
@login_required
@role_required("admin", "recepcionista")
def crear_cotizacion():
    moto = Moto.query.get_or_404(request.form.get("moto_id", type=int))
    descripcion = request.form.get("descripcion", "").strip()
    cantidad = max(1, request.form.get("cantidad", type=int) or 1)
    precio = max(0.0, request.form.get("precio_unitario", type=float) or 0.0)

    cot = Cotizacion(
        moto_id=moto.id,
        creada_por_id=current_user.id,
        estado=CotizacionEstado.PENDIENTE.value,
        observaciones=request.form.get("observaciones", "").strip(),
    )
    db.session.add(cot)
    db.session.flush()
    subtotal = cantidad * precio
    item = CotizacionItem(
        cotizacion_id=cot.id,
        descripcion=descripcion or "Mano de obra",
        cantidad=cantidad,
        precio_unitario=precio,
        subtotal=subtotal,
    )
    db.session.add(item)
    cot.total = subtotal
    db.session.commit()
    log_actividad(current_user.id, "CREAR_COTIZACION", f"Cotización #{cot.id} para {moto.placa}")
    flash("Cotización creada", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/cotizaciones/<int:cotizacion_id>/estado", methods=["POST"])
@login_required
@role_required("admin", "recepcionista")
def cambiar_estado_cotizacion(cotizacion_id: int):
    cot = Cotizacion.query.get_or_404(cotizacion_id)
    estado = request.form.get("estado")
    if estado not in [CotizacionEstado.APROBADA.value, CotizacionEstado.RECHAZADA.value]:
        flash("Estado inválido", "error")
        return redirect(url_for("operaciones.dashboard"))
    cot.estado = estado
    db.session.commit()
    log_actividad(current_user.id, "ESTADO_COTIZACION", f"Cotización #{cot.id}: {estado}")
    flash("Estado de cotización actualizado", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/cotizaciones/<int:cotizacion_id>/facturar", methods=["POST"])
@login_required
@role_required("admin", "recepcionista")
def facturar_cotizacion(cotizacion_id: int):
    cot = Cotizacion.query.get_or_404(cotizacion_id)
    if cot.estado != CotizacionEstado.APROBADA.value:
        flash("La cotización debe estar aprobada para facturar", "error")
        return redirect(url_for("operaciones.dashboard"))

    factura_existente = Factura.query.filter_by(cotizacion_id=cot.id).first()
    if factura_existente:
        flash("Esa cotización ya tiene factura", "error")
        return redirect(url_for("operaciones.dashboard"))

    factura = Factura(moto_id=cot.moto_id, cotizacion_id=cot.id, total=cot.total)
    db.session.add(factura)
    db.session.commit()
    log_actividad(current_user.id, "FACTURAR", f"Factura #{factura.id} de cotización #{cot.id}")
    flash("Factura generada", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/facturas/<int:factura_id>/pagar", methods=["POST"])
@login_required
@role_required("admin", "recepcionista")
def marcar_pagada(factura_id: int):
    factura = Factura.query.get_or_404(factura_id)
    factura.estado_pago = EstadoPago.PAGADO.value
    factura.fecha_pago = datetime.utcnow()
    db.session.commit()
    log_actividad(current_user.id, "PAGO_FACTURA", f"Factura #{factura.id} pagada")
    flash("Factura marcada como pagada", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/citas", methods=["POST"])
@login_required
@role_required("admin", "recepcionista")
def crear_cita():
    # Regla simple de sobrecupo: máximo 6 citas por hora.
    fecha_hora_raw = request.form.get("fecha_hora")
    try:
        fecha_hora = datetime.strptime(fecha_hora_raw, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        flash("Fecha/hora inválida", "error")
        return redirect(url_for("operaciones.dashboard"))

    citas_hora = Cita.query.filter(
        func.strftime("%Y-%m-%d %H", Cita.fecha_hora) == fecha_hora.strftime("%Y-%m-%d %H"),
        Cita.estado == CitaEstado.AGENDADA.value,
    ).count()
    if citas_hora >= 6:
        flash("Ese horario ya está en cupo máximo", "error")
        return redirect(url_for("operaciones.dashboard"))

    cita = Cita(
        cliente_nombre=request.form.get("cliente_nombre", "").strip(),
        cliente_telefono=request.form.get("cliente_telefono", "").strip(),
        modelo=request.form.get("modelo", "").strip(),
        placa=request.form.get("placa", "").strip().upper(),
        novedad=request.form.get("novedad", "").strip(),
        fecha_hora=fecha_hora,
        created_by_id=current_user.id,
    )
    db.session.add(cita)
    db.session.commit()
    log_actividad(current_user.id, "CREAR_CITA", f"Cita #{cita.id} {cita.placa}")
    flash("Cita agendada", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/evidencias", methods=["POST"])
@login_required
@role_required("admin", "recepcionista", "mecanico")
def subir_evidencia():
    moto = Moto.query.get_or_404(request.form.get("moto_id", type=int))
    evidencia = EvidenciaFoto(
        moto_id=moto.id,
        etapa=request.form.get("etapa", "proceso"),
        descripcion=request.form.get("descripcion", "").strip(),
        url_foto=request.form.get("url_foto", "").strip(),
        subido_por_id=current_user.id,
    )
    if not evidencia.url_foto:
        flash("Debes indicar URL de la foto", "error")
        return redirect(url_for("operaciones.dashboard"))
    db.session.add(evidencia)
    db.session.commit()
    log_actividad(current_user.id, "SUBIR_EVIDENCIA", f"Moto {moto.placa}, etapa={evidencia.etapa}")
    flash("Evidencia agregada", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/backups/crear", methods=["POST"])
@login_required
@role_required("admin")
def crear_backup():
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri.startswith("sqlite:///"):
        flash("Backup automático disponible solo para SQLite en esta versión", "error")
        return redirect(url_for("operaciones.dashboard"))
    db_path = db_uri.replace("sqlite:///", "")
    backups_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backups_dir, exist_ok=True)
    filename = f"taller_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    target = os.path.join(backups_dir, filename)
    shutil.copy2(db_path, target)
    log_actividad(current_user.id, "BACKUP_DB", f"Backup generado: {filename}")
    flash(f"Backup creado: {filename}", "success")
    return redirect(url_for("operaciones.dashboard"))


@operaciones_bp.route("/export/facturas.csv", methods=["GET"])
@login_required
@role_required("admin", "recepcionista")
def exportar_facturas_csv():
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["factura_id", "moto_placa", "total", "estado_pago", "fecha_emision"])
    for fac in Factura.query.order_by(Factura.fecha_emision.desc()).all():
        writer.writerow(
            [
                fac.id,
                fac.moto.placa if fac.moto else "",
                f"{fac.total:.2f}",
                fac.estado_pago,
                fac.fecha_emision.isoformat(timespec="seconds"),
            ]
        )
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=facturas.csv"},
    )

