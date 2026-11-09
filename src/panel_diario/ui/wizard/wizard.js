// --- Estado del asistente ---
let INICIO = null;           // opciones y configuración actual que manda Python (ApiAsistente.inicio)
const respuestas = {};       // solo los pasos completados; los saltados no aparecen (se quedan como estaban)
const estadoPaso = {};       // id del paso -> "hecho" | "saltado"
let actual = 0;
// Datos temporales de cada paso mientras se rellena
const tmp = { lugares: [], lugar: null, calendario: "google", ticker: null, medios: null };
// Idioma de cada medio del catálogo, en palabras
const IDIOMAS = { ca: "català", es: "castellà", en: "anglès", fr: "francès" };

const api = () => window.pywebview.api;
const $ = (id) => document.getElementById(id);

function mensaje(texto, tipo) {
  const el = $("mensaje");
  if (el) { el.textContent = texto || ""; el.className = "mensaje " + (tipo || ""); }
}

// Llama a Python y devuelve los datos, o enseña el error y devuelve null
async function llamar(metodo, ...args) {
  mensaje("Comprovant…");
  const r = await api()[metodo](...args);
  if (!r.ok) { mensaje(r.error, "error"); return null; }
  mensaje("");
  return r.datos;
}

// --- Pasos. Cada uno: id, título, pintar() y recoger() (devuelve la respuesta o null si falta algo) ---
const PASOS = [
  {
    id: "inicio", sinSaltar: true,
    pintar: () => `<div class="paso"><h2>Hola! 👋</h2>
      <p>En uns minuts deixem el panell al teu gust: el temps de la teva ciutat, la teva agenda, el teu equip,
      un ETF per seguir i les notícies que t'interessen.</p>
      <p>Cada pas es pot <b>saltar</b>: el que saltis no es mostra al panell (o es queda com estava, si ja ho tenies).
      Tot es desa al teu ordinador, a <b>config.json</b>; no s'envia enlloc.</p></div>`,
    recoger: () => true,
  },
  {
    id: "ubicacion",
    pintar: () => `<div class="paso"><h2>🌤️ On ets?</h2>
      <p>Per al temps i els avisos meteorològics. Tria la teva ciutat${INICIO.actual.lugar ? ` (ara: <b>${esc(INICIO.actual.lugar)}</b>)` : ""}.</p>
      <div class="chips">${INICIO.ciudades.map(c => `<span class="chip" data-ciudad="${esc(c)}">${esc(c)}</span>`).join("")}
        <span class="chip" data-ciudad="">Un altre…</span></div>
      <div class="fila oculto" id="otra-ciudad" style="margin-top:8px"><input type="text" id="ciudad" placeholder="Nom de la teva ciutat">
        <button class="btn" id="btn-buscar">Cerca</button></div>
      <div class="opciones" id="lugares"></div><div class="mensaje" id="mensaje"></div></div>`,
    alMostrar: () => {
      document.querySelectorAll("[data-ciudad]").forEach(el => el.onclick = () => {
        document.querySelectorAll("[data-ciudad]").forEach(x => x.classList.toggle("on", x === el));
        const otra = !el.dataset.ciudad;
        $("otra-ciudad").classList.toggle("oculto", !otra);
        if (otra) { $("ciudad").focus(); } else { buscarLugar(el.dataset.ciudad); }
      });
      $("btn-buscar").onclick = () => buscarLugar($("ciudad").value);
      $("ciudad").onkeydown = (e) => { if (e.key === "Enter") buscarLugar($("ciudad").value); };
      pintarLugares();
    },
    recoger: () => tmp.lugar || (mensaje("Cerca la teva ciutat i tria-la de la llista.", "error"), null),
  },
  {
    id: "agenda",
    pintar: () => `<div class="paso"><h2>📅 La teva agenda</h2>
      <p>Quin calendari fas servir?</p>
      <div class="opciones">${INICIO.calendarios.map(c =>
        `<div class="opcion ${tmp.calendario === c.id ? "on" : ""}" data-calendario="${c.id}"><b>${esc(c.nombre)}</b></div>`).join("")}</div>
      <p class="nota" id="ayuda-calendario"></p>
      <label>Enganxa aquí la seva adreça secreta (una per línia si en tens més d'una). És privada: no la comparteixis.</label>
      <textarea id="ical">${esc((INICIO.actual.ical_urls || []).join("\n"))}</textarea>
      <div class="mensaje" id="mensaje"></div></div>`,
    alMostrar: () => {
      const ayuda = () => {
        $("ayuda-calendario").textContent = "On és: " + INICIO.calendarios.find(c => c.id === tmp.calendario).ayuda;
      };
      document.querySelectorAll("[data-calendario]").forEach(el => el.onclick = () => {
        tmp.calendario = el.dataset.calendario;
        document.querySelectorAll("[data-calendario]").forEach(x => x.classList.toggle("on", x === el));
        ayuda();
      });
      ayuda();
    },
    // Cada adreça es comprova abans de seguir (Python la llegeix; mai l'escriu al registre)
    recoger: async () => {
      const urls = $("ical").value.split("\n").map(s => s.trim()).filter(Boolean);
      if (!urls.length) { mensaje("Enganxa almenys una adreça o salta aquest pas.", "error"); return null; }
      let eventos = 0;
      for (const u of urls) {
        const r = await llamar("verificar_ical", u);
        if (!r) return null;
        eventos += r.eventos;
      }
      mensaje(`✓ ${urls.length === 1 ? "Calendari llegit" : urls.length + " calendaris llegits"} (${eventos} esdeveniments)`, "ok");
      return { ical_urls: urls };
    },
  },
  {
    id: "futbol",
    pintar: () => {
      const f = INICIO.actual.futbol || {};
      return `<div class="paso"><h2>⚽ El teu equip</h2>
      <p>Propers partits i últim resultat de <b>totes</b> les competicions de l'equip que inclou la clau gratuïta de football-data.org
      (lligues i Champions; la Copa del Rei i la Supercopa no hi són):
      <a data-url="https://www.football-data.org/client/register">demana-la aquí</a> (1 minut, t'arriba per correu).</p>
      <label>Clau de football-data.org</label><input type="text" id="clave-futbol" value="${esc(f.football_data_api_key || "")}">
      <label>Competició (només per trobar l'equip a la llista)</label>
      <div class="fila"><select id="competicion">${INICIO.competiciones.map(c => `<option value="${c.codigo}">${esc(c.nombre)}</option>`).join("")}
        <option value="">Un altre…</option></select>
        <button class="btn" id="btn-equipos">Carrega els equips</button></div>
      <input type="text" id="codigo-competicion" class="oculto" style="margin-top:6px" placeholder="Codi de la competició a football-data.org (p. ex. ELC)">
      <label>Equip</label><select id="equipo">${f.team_id ? `<option value="${f.team_id}">${esc(f.nombre || "El teu equip actual")}</option>` : `<option value="">— primer carrega els equips —</option>`}
        <option value="otro">Un altre…</option></select>
      <div class="fila oculto" id="otro-equipo" style="margin-top:6px">
        <input type="text" id="equipo-nombre" placeholder="Nom de l'equip" style="flex:.6">
        <input type="number" id="equipo-id" placeholder="Identificador a football-data.org"></div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      $("btn-equipos").onclick = cargarEquipos;
      $("competicion").onchange = () => $("codigo-competicion").classList.toggle("oculto", $("competicion").value !== "");
      $("equipo").onchange = () => $("otro-equipo").classList.toggle("oculto", $("equipo").value !== "otro");
    },
    recoger: () => {
      const clave = $("clave-futbol").value.trim(), sel = $("equipo");
      const otro = sel.value === "otro";
      const id = otro ? $("equipo-id").value : sel.value;
      const nombre = otro ? $("equipo-nombre").value.trim() : sel.options[sel.selectedIndex].text;
      if (!clave || !id || !nombre) { mensaje("Posa la clau i tria el teu equip (o salta aquest pas).", "error"); return null; }
      return { football_data_api_key: clave, team_id: Number(id), nombre };
    },
  },
  {
    id: "drawdown",
    pintar: () => {
      const d = INICIO.actual.drawdown || {};
      const niv = (d.niveles && d.niveles.length ? d.niveles : [
        { caida: -10, extra_pct: 50 }, { caida: -20, extra_pct: 100 }, { caida: -30, extra_pct: 200 }, { caida: -40, toda_la_reserva: true }]);
      return `<div class="paso"><h2>📉 Un ETF per seguir</h2>
      <p>Mostra quant ha caigut des del seu màxim històric i quant aportar <b>de més</b> aquell mes,
      en % sobre la teva aportació habitual. El panell no guarda cap import.</p>
      <label>ETF</label><div class="fila"><select id="etf">
        ${INICIO.etfs.map(e => `<option value="${e.ticker}">${esc(e.nombre)} (${e.ticker})</option>`).join("")}
        <option value="">Un altre…</option></select></div>
      <div class="fila oculto" id="otro-etf" style="margin-top:6px"><input type="text" id="ticker" placeholder="Ticker de Yahoo Finance (p. ex. EUNL.DE)" value="${esc(d.ticker || "")}">
        <button class="btn" id="btn-ticker">Comprova</button></div>
      <label>Si cau… → aporta de més (%)</label>
      <div class="niveles" id="niveles">${niv.map((n, i) => `
        <input type="number" data-caida="${i}" value="${Math.abs(n.caida)}" min="1" max="90" title="Caiguda en %">
        ${n.toda_la_reserva ? `<span>tota la reserva</span>` : `<input type="number" data-extra="${i}" value="${n.extra_pct}" min="0" max="1000" title="% extra">`}`).join("")}</div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      // El ticker actual: si es uno de la lista, se elige ahí; si no, "Un altre…" con el campo ya escrito
      const actualTicker = (INICIO.actual.drawdown || {}).ticker || "";
      const enLista = INICIO.etfs.some(e => e.ticker === actualTicker);
      $("etf").value = enLista ? actualTicker : (actualTicker ? "" : INICIO.etfs[0].ticker);
      const mostrarOtro = () => $("otro-etf").classList.toggle("oculto", $("etf").value !== "");
      $("etf").onchange = () => { tmp.ticker = null; mostrarOtro(); if ($("etf").value === "") $("ticker").focus(); };
      mostrarOtro();
      $("btn-ticker").onclick = comprobarTicker;
    },
    recoger: async () => {
      if (!tmp.ticker || tmp.ticker.ticker !== tickerElegido()) {
        if (!(await comprobarTicker())) return null;
      }
      const niveles = [...document.querySelectorAll("[data-caida]")].map(el => {
        const extra = document.querySelector(`[data-extra="${el.dataset.caida}"]`);
        return extra ? { caida: Number(el.value), extra_pct: Number(extra.value) } : { caida: Number(el.value), toda_la_reserva: true };
      });
      return { ticker: tmp.ticker.ticker, nombre: tmp.ticker.nombre, niveles };
    },
  },
  {
    id: "noticias",
    pintar: () => {
      prepararNoticias();
      return `<div class="paso"><h2>📰 Els teus mitjans</h2>
      <p>Marca els mitjans que vulguis llegir. N'hi ha de tots els colors: tria'n de diferents per contrastar.
      Cada titular porta el nom del mitjà.</p>
      ${INICIO.grupos_medios.map(g => `<div class="grupo">${esc(g.nombre)}</div>
        <div class="opciones">${g.medios.map(m => `
          <label class="opcion"><input type="checkbox" data-medio value="${esc(m.nombre)}" ${tmp.medios.has(m.nombre) ? "checked" : ""}>
            <b>${esc(m.nombre)}</b><small>${esc(IDIOMAS[m.idioma] || m.idioma)} · ${esc(m.seccions.length === INICIO.seccions.length ? "totes les seccions" : m.seccions.map(nomSeccio).join(", "))}</small></label>`).join("")}
        </div>`).join("")}
      <div class="grupo">Un altre mitjà</div>
      <div class="opciones">
        <div id="propios" class="opciones" style="margin-top:0"></div>
        <div class="opcion" id="otro-medio"><b>Un altre…</b><small>un mitjà amb la seva adreça RSS (surt a Portades)</small></div>
        <div class="fila oculto" id="form-medio">
          <input type="text" id="nom-medio" placeholder="Nom del mitjà" style="flex:.6">
          <input type="text" id="rss-medio" placeholder="https://…/feed">
          <button class="btn" id="btn-medio">Comprova i afegeix</button></div>
      </div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      document.querySelectorAll("[data-medio]").forEach(el => el.onchange = () => {
        tmp.medios[el.checked ? "add" : "delete"](el.value);
      });
      $("otro-medio").onclick = () => { $("form-medio").classList.remove("oculto"); $("nom-medio").focus(); };
      $("btn-medio").onclick = anadirPropio;
      pintarPropios();
    },
    recoger: () => {
      if (!tmp.medios.size && !tmp.propios.length) {
        mensaje("Tria almenys un mitjà (o salta aquest pas).", "error");
        return null;
      }
      return { medios: [...tmp.medios], propios: tmp.propios };
    },
  },
  {
    id: "seccions",
    pintar: () => {
      prepararNoticias();
      return `<div class="paso"><h2>🗂️ Les seccions del panell</h2>
      <p>Cada secció és una pestanya amb les notícies d'aquell tema dels teus mitjans.
      <b>Portades</b> és el resum per llegir en diagonal: les notícies principals de totes les portades,
      primer les que surten a més mitjans. Si en vols més, clica la notícia o ves a les altres seccions.</p>
      <div class="opciones">${INICIO.seccions.map(s => `
        <label class="opcion"><input type="checkbox" data-seccio value="${s.id}" ${tmp.seccions.has(s.id) ? "checked" : ""}>
          <b>${esc(s.nombre)}</b><small>${esc(cobertura(s.id))}</small></label>`).join("")}
        <label class="opcion"><input type="checkbox" id="plans" ${tmp.plans ? "checked" : ""}>
          <b>Plans a la teva ciutat</b><small>concerts, exposicions i festivals (Google Notícies)</small></label>
      </div>
      <label>Temes propis</label>
      <div class="opciones">
        <div id="temas-propios" class="opciones" style="margin-top:0"></div>
        <div class="opcion" id="otro-tema"><b>Un altre…</b><small>unes paraules que Google Notícies busca als titulars</small></div>
        <div class="fila oculto" id="form-tema"><input type="text" id="tema-texto" placeholder="Paraules del tema (p. ex. energia solar)">
          <button class="btn" id="btn-tema">Afegeix</button></div>
      </div>
      <label>Idioma</label>
      <div class="opciones"><label class="opcion"><input type="checkbox" id="traduir" ${tmp.traduir ? "checked" : ""}>
        <b>Tradueix al català</b><small>les notícies en anglès, francès…; si no, cada notícia surt en el seu idioma</small></label></div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      document.querySelectorAll("[data-seccio]").forEach(el => el.onchange = () => {
        tmp.seccions[el.checked ? "add" : "delete"](el.value);
      });
      $("plans").onchange = () => { tmp.plans = $("plans").checked; };
      $("traduir").onchange = () => { tmp.traduir = $("traduir").checked; };
      $("otro-tema").onclick = () => { $("form-tema").classList.remove("oculto"); $("tema-texto").focus(); };
      $("btn-tema").onclick = anadirTema;
      $("tema-texto").onkeydown = (e) => { if (e.key === "Enter") anadirTema(); };
      pintarTemasPropios();
    },
    recoger: () => {
      if (!tmp.seccions.size && !tmp.plans && !tmp.temes.length) {
        mensaje("Tria almenys una secció (o salta aquest pas).", "error");
        return null;
      }
      return { seccions: [...tmp.seccions], plans: tmp.plans, temes: tmp.temes, traduir: tmp.traduir };
    },
  },
  {
    id: "claude",
    pintar: () => `<div class="paso"><h2>✨ Filtre amb IA (opcional)</h2>
      <p>Amb una clau de l'API de Claude, el panell tria les notícies més rellevants i n'escriu un resum d'una línia.
      Costa uns cèntims al mes. Si no en tens, salta aquest pas: tot funciona igual.</p>
      <label>Clau de l'API d'Anthropic</label>
      <input type="password" id="clave-claude" value="${esc(INICIO.actual.claude_api_key || "")}" placeholder="sk-ant-…">
      <div class="mensaje" id="mensaje"></div></div>`,
    recoger: () => {
      const k = $("clave-claude").value.trim();
      return k ? { api_key: k } : (mensaje("Posa la clau o salta aquest pas.", "error"), null);
    },
  },
  {
    id: "final", sinSaltar: true,
    pintar: () => {
      const nombres = { ubicacion: "🌤️ Temps", agenda: "📅 Agenda", futbol: "⚽ Futbol", drawdown: "📉 ETF", noticias: "📰 Mitjans", seccions: "🗂️ Seccions", claude: "✨ IA" };
      return `<div class="paso"><h2>Tot a punt</h2><p>Això és el que es desarà:</p>
      <div class="resumen">${Object.entries(nombres).map(([id, n]) =>
        `<div>${n}: ${estadoPaso[id] === "hecho" ? "<b>configurat</b>" : "es queda com estava"}</div>`).join("")}</div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    recoger: () => true,
  },
];

// --- Acciones de los botones de cada paso ---
// Busca la ciudad y deja elegida la primera (la más poblada): si no es la buena, se elige otra de la lista
async function buscarLugar(texto) {
  const lugares = await llamar("buscar_lugar", texto);
  if (!lugares) return;
  tmp.lugares = lugares;
  tmp.lugar = lugares[0] || null;
  if (!lugares.length) mensaje("No trobo cap ciutat amb aquest nom.", "error");
  pintarLugares();
}

function pintarLugares() {
  $("lugares").innerHTML = tmp.lugares.map((l, i) => `
    <div class="opcion ${tmp.lugar === l ? "on" : ""}" data-lugar="${i}">
      <b>${esc(l.nombre)}</b><small>${esc([l.provincia, l.region, l.pais].filter(Boolean).join(" · "))}</small></div>`).join("");
  document.querySelectorAll("[data-lugar]").forEach(el => el.onclick = () => {
    tmp.lugar = tmp.lugares[Number(el.dataset.lugar)]; pintarLugares();
  });
}

async function cargarEquipos() {
  const codigo = $("competicion").value || $("codigo-competicion").value.trim().toUpperCase();
  if (!codigo) { mensaje("Escriu el codi de la competició.", "error"); return; }
  const equipos = await llamar("equipos", $("clave-futbol").value, codigo);
  if (!equipos) return;
  $("equipo").innerHTML = equipos.map(e => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("")
    + `<option value="otro">Un altre…</option>`;
  $("otro-equipo").classList.add("oculto");
  mensaje(`${equipos.length} equips. Tria el teu.`, "ok");
}

// El ticker elegido: el de la lista o, con "Un altre…", el que se ha escrito
const tickerElegido = () => ($("etf").value || $("ticker").value).trim().toUpperCase();

async function comprobarTicker() {
  const t = await llamar("validar_ticker", tickerElegido());
  if (!t) return false;
  tmp.ticker = t;
  mensaje(`✓ ${t.nombre} · ${t.precio ?? "?"} ${t.moneda}`, "ok");
  return true;
}

// La primera vez que se pinta el paso: lo marcado y los medios propios salen de config.json
// --- Noticias: lo elegido se guarda en tmp para no perderlo al ir y volver entre pasos ---
function prepararNoticias() {
  if (tmp.medios) return;
  const act = INICIO.noticias_actuales;
  tmp.medios = new Set(act.medios);
  tmp.propios = [...act.propios];
  tmp.seccions = new Set(act.seccions);
  tmp.plans = act.plans;
  tmp.temes = [...act.temes];
  tmp.traduir = act.traduir;
}

const nomSeccio = (id) => (INICIO.seccions.find(s => s.id === id) || { nombre: id }).nombre.toLowerCase();

// Cuántos de los medios elegidos publican una sección
function cobertura(seccio) {
  const n = INICIO.grupos_medios.flatMap(g => g.medios)
    .filter(m => tmp.medios.has(m.nombre) && m.seccions.includes(seccio)).length
    + (seccio === "portades" ? tmp.propios.length : 0);
  return n ? `${n} dels teus mitjans` : "cap dels teus mitjans la publica";
}

// "Un altre…" medio: se comprueba el RSS antes de añadirlo
async function anadirPropio() {
  const nombre = $("nom-medio").value.trim(), url = $("rss-medio").value.trim();
  if (!nombre) { mensaje("Posa un nom al mitjà.", "error"); return; }
  const r = await llamar("verificar_rss", url);
  if (!r) return;
  tmp.propios.push({ nombre, url });
  $("nom-medio").value = ""; $("rss-medio").value = "";
  $("form-medio").classList.add("oculto");
  mensaje(`✓ ${nombre}: ${r.titulares} titulars (p. ex. «${r.ejemplo}»)`, "ok");
  pintarPropios();
}

function pintarPropios() {
  $("propios").innerHTML = tmp.propios.map((m, i) => `
    <div class="opcion on"><b>${esc(m.nombre)}</b><small style="flex:1">${esc(m.url)}</small>
      <button class="btn" data-quitar="${i}">Treu</button></div>`).join("");
  $("propios").querySelectorAll("[data-quitar]").forEach(el => el.onclick = () => {
    tmp.propios.splice(Number(el.dataset.quitar), 1); pintarPropios();
  });
}

// "Un altre…" tema: unas palabras que Google Noticias busca en los titulares
function anadirTema() {
  const texto = $("tema-texto").value.trim();
  if (!texto) { mensaje("Escriu les paraules del tema.", "error"); return; }
  tmp.temes.push(texto);
  $("tema-texto").value = "";
  mensaje("");
  pintarTemasPropios();
}

function pintarTemasPropios() {
  $("temas-propios").innerHTML = tmp.temes.map((t, i) => `
    <div class="opcion on"><b>${esc(t)}</b><small style="flex:1">tema propi (Google Notícies)</small>
      <button class="btn" data-quitar-tema="${i}">Treu</button></div>`).join("");
  document.querySelectorAll("[data-quitar-tema]").forEach(el => el.onclick = () => {
    tmp.temes.splice(Number(el.dataset.quitarTema), 1); pintarTemasPropios();
  });
}

// --- Navegación ---
function pintar() {
  const paso = PASOS[actual];
  $("contenido").innerHTML = paso.pintar();
  if (paso.alMostrar) paso.alMostrar();
  $("progreso").innerHTML = PASOS.map((p, i) =>
    `<span class="${i <= actual ? "hecho" : ""} ${estadoPaso[p.id] === "saltado" ? "saltado" : ""}"></span>`).join("");
  $("btn-enrere").disabled = actual === 0;
  $("btn-saltar").style.visibility = paso.sinSaltar ? "hidden" : "visible";
  $("btn-seguent").textContent = paso.id === "final" ? "Desa" : actual === 0 ? "Comencem →" : "Següent →";
}

async function seguir() {
  const paso = PASOS[actual];
  const r = await paso.recoger();
  if (!r) return;
  if (paso.id === "final") return guardar();
  if (!paso.sinSaltar) { respuestas[paso.id] = r; estadoPaso[paso.id] = "hecho"; }
  actual++; pintar();
}

function saltar() {
  const paso = PASOS[actual];
  delete respuestas[paso.id];
  estadoPaso[paso.id] = "saltado";
  actual++; pintar();
}

async function guardar() {
  $("btn-seguent").disabled = true;
  const ok = await llamar("guardar", respuestas);
  $("btn-seguent").disabled = false;
  if (ok === null) return;
  $("contenido").innerHTML = `<div class="paso"><h2>✓ Desat</h2>
    <p>El panell s'està actualitzant amb la nova configuració. Pots tornar a obrir aquest assistent quan vulguis
    des de la icona del costat del rellotge → <b>Configura…</b></p></div>`;
  $("btn-saltar").style.visibility = "hidden";
  $("btn-enrere").style.visibility = "hidden";
  $("btn-seguent").textContent = "Tanca";
  $("btn-seguent").onclick = () => api().cerrar();
}

$("btn-seguent").onclick = seguir;
$("btn-saltar").onclick = saltar;
$("btn-enrere").onclick = () => { if (actual > 0) { actual--; pintar(); } };
// Enlaces externos: se abren en el navegador (no dentro de la ventana del asistente)
document.addEventListener("click", (ev) => {
  const a = ev.target.closest("[data-url]");
  if (a) api().abrir(a.dataset.url);
});

// Arranca cuando el puente con Python está listo
async function iniciar() {
  if (INICIO) return;
  INICIO = await api().inicio();
  pintar();
}
window.addEventListener("pywebviewready", iniciar);
if (window.pywebview && window.pywebview.api && window.pywebview.api.inicio) iniciar();
