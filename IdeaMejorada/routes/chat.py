from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from flask_socketio import emit, join_room

from models import ChatMessage, db


chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def register_chat_handlers(socketio):
    @socketio.on("join")
    def on_join(data):
        room = data.get("room", "general")
        join_room(room)
        # Evita spam visual en recargas y reconexiones de Socket.IO.
        # Si en el futuro se desea presencia en línea, se puede implementar
        # un canal dedicado sin imprimir cada join en la conversación.

    @socketio.on("send_message")
    def on_send_message(data):
        if not current_user.is_authenticated:
            return
        room = data.get("room", "general")
        moto_id = data.get("moto_id")
        mensaje = (data.get("mensaje") or "").strip()
        if not mensaje:
            return
        record = ChatMessage(remitente_id=current_user.id, moto_id=moto_id, mensaje=mensaje)
        db.session.add(record)
        db.session.commit()
        emit(
            "new_message",
            {
                "id": record.id,
                "user": current_user.nombre_completo,
                "remitente_id": current_user.id,
                "mensaje": mensaje,
                "timestamp": record.timestamp.isoformat(timespec="seconds"),
                "moto_id": moto_id,
            },
            room=room,
        )


@chat_bp.route("/messages", methods=["GET"])
@login_required
def listar_mensajes():
    moto_id = request.args.get("moto_id", type=int)
    query = ChatMessage.query.order_by(ChatMessage.timestamp.desc())
    if moto_id:
        query = query.filter_by(moto_id=moto_id)
    else:
        query = query.filter(ChatMessage.moto_id.is_(None))
    query = query.limit(50)
    mensajes = [
        {
            "id": m.id,
            "user": m.remitente.nombre_completo,
            "remitente_id": m.remitente_id,
            "mensaje": m.mensaje,
            "timestamp": m.timestamp.isoformat(timespec="seconds"),
            "moto_id": m.moto_id,
        }
        for m in reversed(query.all())
    ]
    return jsonify(mensajes)


@chat_bp.route("/messages/<int:message_id>", methods=["PATCH"])
@login_required
def editar_mensaje(message_id: int):
    mensaje = ChatMessage.query.get_or_404(message_id)
    if mensaje.remitente_id != current_user.id and current_user.role != "admin":
        return jsonify({"error": "No autorizado"}), 403

    payload = request.get_json(silent=True) or {}
    nuevo_texto = (payload.get("mensaje") or "").strip()
    if not nuevo_texto:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    mensaje.mensaje = nuevo_texto
    db.session.commit()
    return jsonify(
        {
            "id": mensaje.id,
            "mensaje": mensaje.mensaje,
            "timestamp": mensaje.timestamp.isoformat(timespec="seconds"),
        }
    )


@chat_bp.route("/messages/<int:message_id>", methods=["DELETE"])
@login_required
def eliminar_mensaje(message_id: int):
    mensaje = ChatMessage.query.get_or_404(message_id)
    if mensaje.remitente_id != current_user.id and current_user.role != "admin":
        return jsonify({"error": "No autorizado"}), 403

    db.session.delete(mensaje)
    db.session.commit()
    return jsonify({"ok": True, "id": message_id})
