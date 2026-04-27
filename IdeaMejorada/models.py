from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class UserRole(str, Enum):
    ADMIN = "admin"
    RECEPCIONISTA = "recepcionista"
    MECANICO = "mecanico"
    REPUESTOS = "repuestos"


class MotoEstado(str, Enum):
    INGRESADA = "Ingresada"
    DISPONIBLE = "Disponible"
    ASIGNADA = "Asignada"
    EN_PROCESO = "En Proceso"
    PENDIENTE_REPUESTOS = "Pendiente de Repuestos"
    TERMINADA = "Terminada"
    ENTREGADA = "Entregada"
    LIBERADA = "Liberada"


class Prioridad(str, Enum):
    NORMAL = "Normal"
    URGENTE = "Urgente"
    CRITICA = "Crítica"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    nombre_completo = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    motos_asignadas = db.relationship(
        "Moto",
        backref="mecanico_asignado",
        foreign_keys="Moto.mecanico_asignado_id",
        lazy=True,
    )
    motos_recepcionadas = db.relationship(
        "Moto",
        backref="recepcionista",
        foreign_keys="Moto.recepcionista_id",
        lazy=True,
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Moto(db.Model):
    __tablename__ = "motos"

    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(30), default="AKT", nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    placa = db.Column(db.String(20), nullable=False, unique=True, index=True)
    cliente_nombre = db.Column(db.String(120), nullable=False)
    cliente_telefono = db.Column(db.String(30), nullable=False)
    novedades = db.Column(db.Text, nullable=False)
    prioridad = db.Column(db.String(20), default=Prioridad.NORMAL.value, nullable=False)
    estado = db.Column(db.String(50), default=MotoEstado.INGRESADA.value, nullable=False, index=True)
    mecanico_asignado_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    recepcionista_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_asignacion = db.Column(db.DateTime, nullable=True)
    fecha_terminacion = db.Column(db.DateTime, nullable=True)
    fecha_entrega = db.Column(db.DateTime, nullable=True)
    notas_trabajo = db.Column(db.Text, nullable=True)
    fotos = db.Column(db.Text, nullable=True)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=True, index=True)
    mensaje = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    leido = db.Column(db.Boolean, default=False, nullable=False)

    remitente = db.relationship("User", foreign_keys=[remitente_id], lazy=True)
    moto = db.relationship("Moto", foreign_keys=[moto_id], lazy=True)


class ActividadLog(db.Model):
    __tablename__ = "actividades_log"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    accion = db.Column(db.String(80), nullable=False)
    detalle = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    usuario = db.relationship("User", lazy=True)


class Configuracion(db.Model):
    __tablename__ = "configuracion"

    clave = db.Column(db.String(80), primary_key=True)
    valor = db.Column(db.Text, nullable=False)


class Repuesto(db.Model):
    __tablename__ = "repuestos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True, index=True)
    categoria = db.Column(db.String(80), nullable=False)
    stock_actual = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=0)
    costo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class MotoRepuestoUso(db.Model):
    __tablename__ = "moto_repuestos_uso"

    id = db.Column(db.Integer, primary_key=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False, index=True)
    repuesto_id = db.Column(db.Integer, db.ForeignKey("repuestos.id"), nullable=False, index=True)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    costo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    moto = db.relationship("Moto", lazy=True)
    repuesto = db.relationship("Repuesto", lazy=True)


class CotizacionEstado(str, Enum):
    PENDIENTE = "Pendiente"
    APROBADA = "Aprobada"
    RECHAZADA = "Rechazada"


class Cotizacion(db.Model):
    __tablename__ = "cotizaciones"

    id = db.Column(db.Integer, primary_key=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False, index=True)
    creada_por_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default=CotizacionEstado.PENDIENTE.value)
    observaciones = db.Column(db.Text, nullable=True)
    total = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    moto = db.relationship("Moto", lazy=True)
    creada_por = db.relationship("User", lazy=True)


class CotizacionItem(db.Model):
    __tablename__ = "cotizacion_items"

    id = db.Column(db.Integer, primary_key=True)
    cotizacion_id = db.Column(
        db.Integer, db.ForeignKey("cotizaciones.id"), nullable=False, index=True
    )
    descripcion = db.Column(db.String(255), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False, default=0.0)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)

    cotizacion = db.relationship("Cotizacion", lazy=True)


class EstadoPago(str, Enum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"


class Factura(db.Model):
    __tablename__ = "facturas"

    id = db.Column(db.Integer, primary_key=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False, index=True)
    cotizacion_id = db.Column(
        db.Integer, db.ForeignKey("cotizaciones.id"), nullable=True, index=True
    )
    total = db.Column(db.Float, nullable=False, default=0.0)
    estado_pago = db.Column(db.String(20), nullable=False, default=EstadoPago.PENDIENTE.value)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=True)

    moto = db.relationship("Moto", lazy=True)
    cotizacion = db.relationship("Cotizacion", lazy=True)


class CitaEstado(str, Enum):
    AGENDADA = "Agendada"
    COMPLETADA = "Completada"
    CANCELADA = "Cancelada"


class Cita(db.Model):
    __tablename__ = "citas"

    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(120), nullable=False)
    cliente_telefono = db.Column(db.String(30), nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    placa = db.Column(db.String(20), nullable=False, index=True)
    novedad = db.Column(db.Text, nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False, index=True)
    estado = db.Column(db.String(20), nullable=False, default=CitaEstado.AGENDADA.value)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship("User", lazy=True)


class EvidenciaFoto(db.Model):
    __tablename__ = "evidencias_fotos"

    id = db.Column(db.Integer, primary_key=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False, index=True)
    etapa = db.Column(db.String(30), nullable=False)  # ingreso, proceso, entrega
    descripcion = db.Column(db.String(255), nullable=True)
    url_foto = db.Column(db.Text, nullable=False)
    subido_por_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    moto = db.relationship("Moto", lazy=True)
    subido_por = db.relationship("User", lazy=True)


class PuntuacionMecanico(db.Model):
    __tablename__ = "puntuacion_mecanico"

    id = db.Column(db.Integer, primary_key=True)
    mecanico_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    puntos = db.Column(db.Integer, nullable=False, default=0)
    motivo = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    mecanico = db.relationship("User", lazy=True)


class ClientePortalAcceso(db.Model):
    __tablename__ = "cliente_portal_acceso"

    id = db.Column(db.Integer, primary_key=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    moto = db.relationship("Moto", lazy=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


def log_actividad(usuario_id: int, accion: str, detalle: str) -> None:
    db.session.add(ActividadLog(usuario_id=usuario_id, accion=accion, detalle=detalle))
    db.session.commit()
