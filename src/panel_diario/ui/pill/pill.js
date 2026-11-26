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
    ajustarAncho(a);
  } catch (e) { /* se reintenta en el siguiente ciclo */ }
}

// La ventana se ajusta a lo que ocupa el contenido (de la primera a la última pieza visible, más
// el margen de los lados): con un ancho fijo sobraba espacio cuando el texto es corto.
// El punto de aviso va en posición absoluta y no cuenta.
let anchoPedido = 0;
function ajustarAncho(a) {
  if (!a.ajustar_ancho) return;
  const piezas = [...ficha.children].filter(e => e.id !== "aviso" && e.getClientRects().length);
  if (!piezas.length) return;
  const izq = Math.min(...piezas.map(e => e.getBoundingClientRect().left));
  const der = Math.max(...piezas.map(e => e.getBoundingClientRect().right));
  const css = getComputedStyle(ficha);
  const ancho = Math.ceil(der - izq + parseFloat(css.paddingLeft) + parseFloat(css.paddingRight));
  if (ancho === anchoPedido) return;
  anchoPedido = ancho;
  // También lo que ve ahora la página: con zoom sus píxeles no son los de la ventana
  a.ajustar_ancho(ancho, window.innerWidth);
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
