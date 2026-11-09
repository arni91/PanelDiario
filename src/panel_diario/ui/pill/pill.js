const api = () => (window.pywebview && window.pywebview.api) || null;
const ficha = document.getElementById("ficha");

async function pintar() {
  const a = api();
  if (!a || !a.mini) return;
  try {
    const m = await a.mini();
    if (m.temp === null || m.temp === undefined) return;
    document.getElementById("temp").textContent = m.temp + "°";
    document.getElementById("ico").textContent = m.icono || "🌡️";
    // Máxima y mínima del día + probabilidad de lluvia (la más alta de las próximas 12 h)
    document.getElementById("rango").textContent = m.max != null ? `↑${m.max} ↓${m.min}` : "";
    const lluvia = document.getElementById("lluvia");
    lluvia.textContent = m.lluvia != null ? `💧${m.lluvia}%` : "";
    lluvia.className = "lluvia" + (m.lluvia >= 40 ? " alta" : "");   // en azul si es probable
    document.getElementById("aviso").className = "aviso " + (m.aviso || "");
    ficha.title = `${m.lugar || ""}: ${m.texto || ""}\nClic: obre · Arrossega: mou`;
  } catch (e) { /* se reintenta en el siguiente ciclo */ }
}
window.pintar = pintar;

// --- Clic o arrastre en toda la ficha ---
// Si el ratón se mueve más de 4 px con el botón pulsado es un arrastre; si no, es un clic.
// El arrastre mantiene el punto agarrado bajo el cursor (se autocorrige con cualquier escalado).
let agarre = null, movido = false, ocupado = false, ultimo = null;
ficha.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  agarre = { x: e.clientX, y: e.clientY }; movido = false;
  ficha.setPointerCapture(e.pointerId);
  ficha.classList.add("pulsada");
});
ficha.addEventListener("pointermove", (e) => {
  if (!agarre) return;
  if (!movido && Math.hypot(e.clientX - agarre.x, e.clientY - agarre.y) < 4) return;
  movido = true;
  ficha.classList.remove("pulsada"); ficha.classList.add("arrastrando");
  ultimo = e; empujar();
});
ficha.addEventListener("pointerup", () => {
  const eraClic = agarre && !movido;
  agarre = null; ultimo = null;
  ficha.classList.remove("pulsada", "arrastrando");
  const a = api();
  if (eraClic && a) a.clic();
});
ficha.addEventListener("pointercancel", () => { agarre = null; ficha.classList.remove("pulsada", "arrastrando"); });

async function empujar() {
  if (ocupado || !agarre || !ultimo) return;
  const dx = Math.round(ultimo.clientX - agarre.x), dy = Math.round(ultimo.clientY - agarre.y);
  ultimo = null;
  if (!dx && !dy) return;
  const a = api();
  if (!a || !a.mover_rel) return;
  ocupado = true;
  try { await a.mover_rel(dx, dy); } catch (_) {}
  ocupado = false;
}

let iniciado = false;
function iniciar() {
  if (iniciado) return;
  iniciado = true;
  pintar();
  setInterval(pintar, 60000);
}
window.addEventListener("pywebviewready", iniciar);
if (api() && api().mini) iniciar();
