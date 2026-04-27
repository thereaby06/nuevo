function initFlashAutoHide() {
  document.querySelectorAll("article.success, article.error").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(-6px)";
      setTimeout(() => el.remove(), 300);
    }, 4500);
  });
}

function initMotoSearch() {
  const input = document.querySelector("[data-moto-search-input]");
  if (!input) return;
  const rows = Array.from(document.querySelectorAll("tr[data-search-text]"));
  if (!rows.length) return;

  const filterRows = () => {
    const term = input.value.trim().toLowerCase();
    rows.forEach((row) => {
      const text = (row.dataset.searchText || "").toLowerCase();
      row.style.display = !term || text.includes(term) ? "" : "none";
    });
  };

  input.addEventListener("input", filterRows);
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
    }
  });
}

function initWorkTimer() {
  const timer = document.querySelector("[data-work-timer]");
  if (!timer) return;
  const startAt = timer.dataset.startAt;
  const startMs = startAt ? Date.parse(startAt) : NaN;
  if (Number.isNaN(startMs)) {
    timer.textContent = "Sin hora de inicio registrada";
    return;
  }

  const tick = () => {
    const diff = Math.max(0, Date.now() - startMs);
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    timer.textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  tick();
  setInterval(tick, 1000);
}

initFlashAutoHide();
initMotoSearch();
initWorkTimer();
