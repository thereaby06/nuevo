import os
import sys

# Monkey patch para eventlet (DEBE ir antes de cualquier otro import)
if os.environ.get("RENDER"):
    import eventlet
    eventlet.monkey_patch()

# Permitir importaciones cuando se ejecuta desde el directorio raíz del repo
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, render_template
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import Moto, User, UserRole, db
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.chat import chat_bp, register_chat_handlers
from routes.cliente import cliente_bp
from routes.mecanico import mecanico_bp
from routes.operaciones import operaciones_bp
from routes.repuestos import repuestos_bp
from routes.recepcionista import recepcionista_bp


socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recepcionista_bp)
    app.register_blueprint(mecanico_bp)
    app.register_blueprint(operaciones_bp)
    app.register_blueprint(repuestos_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(chat_bp)
    csrf.exempt(chat_bp)
    register_chat_handlers(socketio)

    @app.context_processor
    def inject_helpers():
        return {"UserRole": UserRole}

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", title="No autorizado", message="Acceso denegado"), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", title="No encontrado", message="Página no encontrada"), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template("error.html", title="Error", message="Error interno del servidor"), 500

    with app.app_context():
        db.create_all()
        seed_data()
    
    print(">>> Aplicación iniciada con éxito (Modo Concurrente)")
    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def seed_data():
    if User.query.count() == 0:
        users = [
            ("admin", "admin123", "admin", "Administrador General"),
            ("recep1", "recep123", "recepcionista", "Recepcionista 1"),
            ("recep2", "recep123", "recepcionista", "Recepcionista 2"),
            ("mec1", "mec123", "mecanico", "Mecánico 1"),
            ("mec2", "mec123", "mecanico", "Mecánico 2"),
            ("mec3", "mec123", "mecanico", "Mecánico 3"),
            ("mec4", "mec123", "mecanico", "Mecánico 4"),
            ("mec5", "mec123", "mecanico", "Mecánico 5"),
            ("mec6", "mec123", "mecanico", "Mecánico 6"),
            ("repu1", "repu123", "repuestos", "Bodega Repuestos 1"),
        ]
        for username, password, role, nombre in users:
            user = User(username=username, role=role, nombre_completo=nombre, activo=True)
            user.set_password(password)
            db.session.add(user)
        db.session.commit()
    else:
        repuestos_user = User.query.filter_by(username="repu1").first()
        if not repuestos_user:
            repuestos_user = User(
                username="repu1",
                role="repuestos",
                nombre_completo="Bodega Repuestos 1",
                activo=True,
            )
            repuestos_user.set_password("repu123")
            db.session.add(repuestos_user)
            db.session.commit()

    from models import Repuesto
    if Repuesto.query.count() == 0:
        repuestos = [
            ("Aceite 20W50", "Aceites", 20, 8, 35000),
            ("Filtro de aceite AKT", "Filtros", 15, 5, 18000),
            ("Pastillas de freno", "Frenos", 12, 4, 42000),
            ("Cadena 428", "Transmisión", 10, 3, 90000),
            ("Bujía NGK", "Encendido", 25, 10, 15000),
        ]
        for nombre, categoria, stock, minimo, costo in repuestos:
            db.session.add(
                Repuesto(
                    nombre=nombre,
                    categoria=categoria,
                    stock_actual=stock,
                    stock_minimo=minimo,
                    costo_unitario=costo,
                )
            )
        db.session.commit()

    if Moto.query.count() == 0:
        recep = User.query.filter_by(username="recep1").first()
        ejemplo = [
            (
                "NKD 125",
                "KL889H",
                "Juan Pérez",
                "3001234567",
                "Revisión 500km, cambio de aceite, sonido raro al frenar",
                "Normal",
            ),
            (
                "TT 200",
                "XY456Z",
                "María González",
                "3001112233",
                "Cambio de pastillas de freno, ajuste de carburador",
                "Urgente",
            ),
            (
                "NK 150",
                "AB123C",
                "Carlos Rodríguez",
                "3005559012",
                "Revisión 1000km, aceite y filtro, revisión de cadena",
                "Normal",
            ),
        ]
        for modelo, placa, cliente, tel, novedad, prioridad in ejemplo:
            db.session.add(
                Moto(
                    modelo=modelo,
                    placa=placa,
                    cliente_nombre=cliente,
                    cliente_telefono=tel,
                    novedades=novedad,
                    prioridad=prioridad,
                    estado="Disponible",
                    recepcionista_id=recep.id,
                )
            )
        db.session.commit()


app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
