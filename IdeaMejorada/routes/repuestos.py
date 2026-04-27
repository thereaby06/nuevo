from flask import Blueprint, render_template
from flask_login import login_required

from models import Moto, MotoRepuestoUso, Repuesto
from routes.utils import role_required


repuestos_bp = Blueprint("repuestos", __name__, url_prefix="/repuestos")


@repuestos_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("repuestos", "admin")
def dashboard():
    repuestos = Repuesto.query.order_by(Repuesto.nombre.asc()).all()
    alertas_stock = Repuesto.query.filter(Repuesto.stock_actual <= Repuesto.stock_minimo).all()
    motos = Moto.query.order_by(Moto.fecha_ingreso.desc()).limit(50).all()
    consumos = MotoRepuestoUso.query.order_by(MotoRepuestoUso.created_at.desc()).limit(50).all()
    return render_template(
        "repuestos/dashboard.html",
        repuestos=repuestos,
        alertas_stock=alertas_stock,
        motos=motos,
        consumos=consumos,
    )
