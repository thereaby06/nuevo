if (window.chartEstados && document.getElementById("chartEstados")) {
  new Chart(document.getElementById("chartEstados"), {
    type: "doughnut",
    data: {
      labels: window.chartEstados.map((x) => x[0]),
      datasets: [{ data: window.chartEstados.map((x) => x[1]) }],
    },
  });
}

if (window.chartProductividad && document.getElementById("chartProductividad")) {
  new Chart(document.getElementById("chartProductividad"), {
    type: "bar",
    data: {
      labels: window.chartProductividad.map((x) => x[0]),
      datasets: [{ data: window.chartProductividad.map((x) => x[1]), label: "Motos atendidas" }],
    },
  });
}
