const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const sendChat = document.getElementById("sendChat");

if (chatMessages && chatInput && sendChat) {
  const socket = io();
  const room = "general";
  const currentUserId = Number(chatMessages.dataset.currentUserId || 0);
  const currentUserRole = chatMessages.dataset.currentUserRole || "";
  const csrfToken = chatMessages.dataset.csrfToken || "";

  function canManageMessage(msg) {
    return msg && (Number(msg.remitente_id) === currentUserId || currentUserRole === "admin");
  }

  function closeAllMenus() {
    document.querySelectorAll(".chat-menu-list").forEach((el) => el.remove());
  }

  function buildMenu(msg, row) {
    const menuWrap = document.createElement("div");
    menuWrap.className = "chat-menu";

    const menuBtn = document.createElement("button");
    menuBtn.type = "button";
    menuBtn.className = "chat-menu-btn";
    menuBtn.title = "Opciones";
    menuBtn.textContent = "⋯";
    menuWrap.appendChild(menuBtn);

    menuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const existing = menuWrap.querySelector(".chat-menu-list");
      closeAllMenus();
      if (existing) return;

      const list = document.createElement("div");
      list.className = "chat-menu-list";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.textContent = "Editar";
      editBtn.addEventListener("click", async () => {
        const nuevo = prompt("Editar mensaje:", msg.mensaje || "");
        if (nuevo === null) return;
        const texto = nuevo.trim();
        if (!texto) {
          alert("El mensaje no puede quedar vacío.");
          return;
        }
        const res = await fetch(`/chat/messages/${msg.id}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          credentials: "same-origin",
          body: JSON.stringify({ mensaje: texto }),
        });
        if (!res.ok) {
          const detail = await res.text();
          alert(`No se pudo editar el mensaje. ${detail}`);
          return;
        }
        msg.mensaje = texto;
        row.querySelector(".chat-msg-text").textContent = `[${msg.timestamp || ""}] ${msg.user || "Sistema"}: ${msg.mensaje || msg.msg}`;
        closeAllMenus();
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.textContent = "Eliminar";
      deleteBtn.addEventListener("click", async () => {
        if (!confirm("¿Eliminar este mensaje?")) return;
        const res = await fetch(`/chat/messages/${msg.id}`, {
          method: "DELETE",
          headers: { "X-CSRFToken": csrfToken },
          credentials: "same-origin",
        });
        if (!res.ok) {
          const detail = await res.text();
          alert(`No se pudo eliminar el mensaje. ${detail}`);
          return;
        }
        row.remove();
        closeAllMenus();
      });

      list.appendChild(editBtn);
      list.appendChild(deleteBtn);
      menuWrap.appendChild(list);
    });

    return menuWrap;
  }

  function appendMessage(msg) {
    const row = document.createElement("div");
    row.className = "chat-msg";

    const text = document.createElement("div");
    text.className = "chat-msg-text";
    text.textContent = `[${msg.timestamp || ""}] ${msg.user || "Sistema"}: ${msg.mensaje || msg.msg}`;
    row.appendChild(text);

    if (msg.id && canManageMessage(msg)) {
      row.appendChild(buildMenu(msg, row));
    }

    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  fetch("/chat/messages")
    .then((res) => res.json())
    .then((rows) => rows.forEach(appendMessage));

  socket.emit("join", { room });
  socket.on("new_message", appendMessage);
  socket.on("status", appendMessage);
  document.addEventListener("click", closeAllMenus);

  sendChat.addEventListener("click", () => {
    const mensaje = chatInput.value.trim();
    if (!mensaje) return;
    socket.emit("send_message", { room, mensaje });
    chatInput.value = "";
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat.click();
    }
  });
}
