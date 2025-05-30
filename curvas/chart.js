const datos = [
  {
    "intervalo": "00:00",
    "requeridos": 5,
    "asignados": 5,
    "limite_inferior": 4,
    "limite_superior": 6
  },
  {
    "intervalo": "00:30",
    "requeridos": 5,
    "asignados": 5,
    "limite_inferior": 4,
    "limite_superior": 6
  },
  {
    "intervalo": "01:00",
    "requeridos": 0,
    "asignados": 0,
    "limite_inferior": 0,
    "limite_superior": 1
  },
  // [... sigue con los datos completos aquí ...]
];

// --- Gráfico ---
const c = document.getElementById("c");
const ctx = c.getContext("2d");
c.width = 700;
c.height = 350;
const offset = 50;
const chartHeight = c.height - 2 * offset;
const chartWidth = c.width - 2 * offset;
const maxY = Math.max(...datos.map(d => d.limite_superior || 0)) + 1;

ctx.clearRect(0, 0, c.width, c.height);
ctx.lineWidth = 1;
ctx.strokeStyle = "#999";
ctx.fillStyle = "#ccc";
ctx.font = "12px monospace";

// Ejes
ctx.beginPath();
ctx.moveTo(offset, offset);
ctx.lineTo(offset, offset + chartHeight);
ctx.lineTo(offset + chartWidth, offset + chartHeight);
ctx.stroke();

const stepX = chartWidth / datos.length;
const unitY = chartHeight / maxY;

datos.forEach((d, i) => {
  const x = offset + (i + 1) * stepX;
  const yAsignado = offset + chartHeight - (d.asignados * unitY);
  const yLimInf = offset + chartHeight - (d.limite_inferior * unitY);
  const yLimSup = offset + chartHeight - (d.limite_superior * unitY);
  const barHeight = d.requeridos * unitY;

  // Barras
  ctx.fillStyle = "#4477AA";
  ctx.fillRect(x - stepX / 4, offset + chartHeight - barHeight, stepX / 2, barHeight);

  // Asignados
  ctx.beginPath();
  ctx.arc(x, yAsignado, 3, 0, 2 * Math.PI);
  ctx.fillStyle = "#EE6677";
  ctx.fill();

  // Límites
  ctx.beginPath();
  ctx.moveTo(x - 5, yLimInf);
  ctx.lineTo(x + 5, yLimInf);
  ctx.moveTo(x - 5, yLimSup);
  ctx.lineTo(x + 5, yLimSup);
  ctx.strokeStyle = "#000";
  ctx.setLineDash([5, 3]);
  ctx.stroke();
  ctx.setLineDash([]);
});
