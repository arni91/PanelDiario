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
      <p>En uns minuts deixem el panell al teu gust: el temps de la teva ciutat, la teva agenda, els teus esports i equips,
      la borsa i les notícies que t'interessen.</p>
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
    id: "dia",
    pintar: () => {
      const a = INICIO.dia_actual, o = INICIO.dia;
      // La provincia de las gasolineras: por defecto, la de la ciudad (Python la reconoce al guardar)
      const ciutat = (tmp.lugar && tmp.lugar.provincia) || "la teva ciutat";
      return `<div class="paso"><h2>🏠 El teu dia a dia</h2>
      <p>Marca el que et sigui útil. El preu de la llum i les gasolineres són d'Espanya.</p>
      <div class="opciones">
        <label class="opcion"><input type="checkbox" id="dia-llum" ${a.llum ? "checked" : ""}>
          <b>⚡ Preu de la llum</b><small>el preu de cada hora d'avui i les hores més barates</small></label>
        <label class="opcion"><input type="checkbox" id="dia-aire" ${a.aire ? "checked" : ""}>
          <b>🌿 Qualitat de l'aire i pol·len</b><small>a la teva ciutat</small></label>
        <label class="opcion"><input type="checkbox" id="dia-carb" ${a.carburants ? "checked" : ""}>
          <b>⛽ Gasolineres més barates</b><small>les més barates a prop teu</small></label>
      </div>
      <div id="dia-gas" class="${a.carburants ? "" : "oculto"}">
        <div class="niveles" style="margin-top:10px">
          <label>Carburant</label><select id="dia-producte">${o.carburants.map(c =>
            `<option value="${esc(c.id)}" ${a.producte === c.id ? "selected" : ""}>${esc(c.nom)}</option>`).join("")}</select>
          <label>A menys de</label><select id="dia-radi">${o.radis.map(r =>
            `<option value="${r}" ${a.radi_km === r ? "selected" : ""}>${r} km</option>`).join("")}</select>
          <label>Província</label><select id="dia-provincia">
            <option value="">La de ${esc(ciutat)}</option>
            ${o.provincies.map(p => `<option value="${esc(p.id)}" ${a.provincia === p.id ? "selected" : ""}>${esc(p.nom)}</option>`).join("")}</select>
        </div>
      </div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      $("dia-carb").onchange = () => $("dia-gas").classList.toggle("oculto", !$("dia-carb").checked);
    },
    recoger: () => {
      const r = {
        llum: $("dia-llum").checked, aire: $("dia-aire").checked, carburants: $("dia-carb").checked,
        producte: $("dia-producte").value, radi_km: Number($("dia-radi").value), provincia: $("dia-provincia").value,
      };
      if (!r.llum && !r.aire && !r.carburants) { mensaje("Marca almenys una opció (o salta aquest pas).", "error"); return null; }
      return r;
    },
  },
  {
    id: "esports",
    pintar: () => {
      if (!tmp.equips) {
        tmp.equips = [...INICIO.esports_actual.equips];
        tmp.motor = { f1: INICIO.esports_actual.f1, motogp: INICIO.esports_actual.motogp };
        tmp.esport = "futbol";
        tmp.equiposPorEsport = {};  // equipos ya cargados de cada deporte (no se piden dos veces)
      }
      return `<div class="paso"><h2>🏅 Els teus esports</h2>
      <p>Tria un esport i marca els equips que vols seguir: el panell mostra els seus propers partits i l'últim resultat.
      Pots triar-ne tants com vulguis, de diferents esports. En futbol hi surten tots els partits de l'equip
      (lliga, copa, Champions…). A la Fórmula 1 i el MotoGP se segueix el campionat sencer.
      Si el teu equip no hi és, tria <b>Un altre…</b> i escriu-ne el nom.</p>
      <label>Esport</label><div class="fila"><select id="esport">
        ${INICIO.esports.esports.map(e => `<option value="${esc(e.id)}" ${tmp.esport === e.id ? "selected" : ""}>${esc(e.nombre)}</option>`).join("")}
        <option value="${ALTRE}" ${tmp.esport === ALTRE ? "selected" : ""}>Un altre…</option>
      </select></div>
      <div id="cos-esport"></div>
      <div class="grupo">El que segueixes</div>
      <div class="opciones" id="equips"></div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    alMostrar: () => {
      $("esport").onchange = () => { tmp.esport = $("esport").value; pintarEsport(); };
      pintarEsport();
      pintarEquipos();
    },
    recoger: () => {
      if (!tmp.equips.length && !tmp.motor.f1 && !tmp.motor.motogp) {
        mensaje("Marca almenys un equip o un campionat de motor (o salta aquest pas).", "error"); return null;
      }
      return { equips: tmp.equips, f1: tmp.motor.f1, motogp: tmp.motor.motogp };
    },
  },
  {
    id: "borsa",
    pintar: () => {
      const act = INICIO.borsa_actual;
      const grupos = [...new Set(INICIO.borsa.indexs.map(i => i.grup))];
      return `<div class="paso"><h2>📈 Borsa</h2>
      <p>Els índexs que vulguis seguir, amb la variació del dia, i les accions que més es mouen avui
      (mercat dels Estats Units).</p>
      ${grupos.map(g => `<div class="grupo">${esc(g)}</div><div class="opciones">${INICIO.borsa.indexs.filter(i => i.grup === g).map(i => `
        <label class="opcion"><input type="checkbox" data-index value="${esc(i.simbol)}" ${act.indexs.includes(i.simbol) ? "checked" : ""}>
          <b>${esc(i.nom)}</b><small>${esc(i.simbol)}</small></label>`).join("")}</div>`).join("")}
      <div class="grupo">Accions del dia</div>
      <div class="opciones">${INICIO.borsa.moviments.map(m => `
        <label class="opcion"><input type="checkbox" data-moviment value="${m.id}" ${act.moviments.includes(m.id) ? "checked" : ""}>
          <b>${esc(m.nombre)}</b></label>`).join("")}</div>
      <div class="mensaje" id="mensaje"></div></div>`;
    },
    recoger: () => {
      const marcados = (attr) => [...document.querySelectorAll(`[data-${attr}]:checked`)].map(el => el.value);
      const r = { indexs: marcados("index"), moviments: marcados("moviment") };
      if (!r.indexs.length && !r.moviments.length) { mensaje("Tria almenys un índex o una llista (o salta aquest pas).", "error"); return null; }
      return r;
    },
  },
  {
    id: "drawdown",
    pintar: () => {
      const d = INICIO.actual.drawdown || {};
      const niv = (d.niveles && d.niveles.length ? d.niveles : [
        { caida: -10, extra_pct: 50 }, { caida: -20, extra_pct: 100 }, { caida: -30, extra_pct: 200 }, { caida: -40, toda_la_reserva: true }]);
      return `<div class="paso"><h2>📉 El teu ETF o acció (opcional)</h2>
      <p>Si inverteixes periòdicament en un ETF o una acció, el panell mostra quant ha caigut des del seu màxim
      i quant aportar <b>de més</b> aquell mes, en % sobre la teva aportació habitual. No guarda cap import.
      Si no t'interessa, prem <b>Salta</b>.</p>
      <label>ETF o acció</label><div class="fila"><select id="etf">
        ${INICIO.etfs.map(e => `<option value="${e.ticker}">${esc(e.nombre)} (${e.ticker})</option>`).join("")}
        <option value="">Un altre…</option></select></div>
      <div class="fila oculto" id="otro-etf" style="margin-top:6px"><input type="text" id="ticker" placeholder="Símbol de Yahoo Finance (p. ex. EUNL.DE o AAPL)" value="${esc(d.ticker || "")}">
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
      Cada titular porta el nom del mitjà. A <b>Actualitat</b> hi ha els diaris generals; a <b>Per temes</b>, els especialitzats.</p>
      ${INICIO.grupos_medios.map((g, i) => `${i === 0 || INICIO.grupos_medios[i - 1].bloc !== g.bloc ? `<h3 class="bloc">${esc(g.bloc)}</h3>` : ""}
        <div class="grupo">${esc(g.nombre)}</div>
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
    id: "final", sinSaltar: true,
    pintar: () => {
      const nombres = { ubicacion: "🌤️ Temps", agenda: "📅 Agenda", dia: "🏠 Dia a dia", esports: "🏅 Esports", borsa: "📈 Borsa", drawdown: "📉 El teu ETF", noticias: "📰 Mitjans", seccions: "🗂️ Seccions" };
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

// --- Deportes: desplegable de deportes → todos sus equipos (con buscador) o su campeonato de motor ---
// Mismo equipo = mismo calendario en ESPN: en fútbol basta el id (juega liga, copa y Champions);
// en los demás deportes, el id dentro de su liga (un id de la NBA y uno de la WNBA pueden coincidir).
const claveEquipo = (e) => e.lliga.startsWith("soccer/") ? `soccer/${e.id}` : `${e.lliga}/${e.id}`;
const sigue = (e) => tmp.equips.some(x => claveEquipo(x) === claveEquipo(e));
// Competición de un equipo elegido: la del catálogo o, en los de «Un altre…», la que dio el buscador
const nomLliga = (e) => (INICIO.esports.lligues.find(l => l.path === e.lliga) || { nom: e.competicio || e.lliga }).nom;
const ALTRE = "altre";  // la opción «Un altre…» del desplegable
const deporte = (id) => INICIO.esports.esports.find(e => e.id === id) || { id: ALTRE, tipus: ALTRE };
// Para buscar sin acentos ni mayúsculas ("atletico" encuentra "Atlético")
const sinAcentos = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

function pintarEsport() {
  const d = deporte(tmp.esport);
  if (d.tipus === ALTRE) {
    $("cos-esport").innerHTML = `<div class="fila" style="margin-top:8px">
        <input type="text" id="buscar-altre" placeholder="Nom de l'equip o el club (per exemple, Celtic)">
        <button class="btn" id="btn-altre">Cerca</button></div>
      <div id="llista-equips" class="nota">Escriu el nom de l'equip de qualsevol esport i prem «Cerca».
        Només hi surten els equips amb partits publicats.</div>`;
    $("btn-altre").onclick = buscarAltre;
    $("buscar-altre").onkeydown = (ev) => { if (ev.key === "Enter") buscarAltre(); };
    if (tmp.equiposPorEsport[ALTRE]) casillasEquipos(tmp.equiposPorEsport[ALTRE]);
    return;
  }
  if (d.tipus === "motor") {
    $("cos-esport").innerHTML = `<div class="opciones"><label class="opcion">
      <input type="checkbox" id="motor" ${tmp.motor[d.id] ? "checked" : ""}>
      <b>Seguir el campionat de ${esc(d.nombre)}</b><small>la propera cursa i qui va guanyar l'última</small></label></div>`;
    $("motor").onchange = () => { tmp.motor[d.id] = $("motor").checked; pintarEquipos(); };
    return;
  }
  $("cos-esport").innerHTML = `<div class="fila" style="margin-top:8px">
      <input type="text" id="buscar-equip" placeholder="Cerca l'equip (per exemple, Barcelona)"></div>
    <div id="llista-equips" class="nota">Carregant els equips de ${esc(d.nombre)}…</div>`;
  $("buscar-equip").oninput = pintarListaEquipos;
  cargarEquipos(d.id);
}

async function cargarEquipos(esport) {
  if (!tmp.equiposPorEsport[esport]) {
    const equipos = await llamar("equipos", esport);
    if (!equipos) return;
    tmp.equiposPorEsport[esport] = equipos;
  }
  if (esport === tmp.esport) pintarListaEquipos();  // si mientras tanto se ha elegido otro, no se pinta
}

// «Un altre…»: busca el nombre en ESPN; Python ya descarta los equipos sin partidos publicados
async function buscarAltre() {
  const texto = $("buscar-altre").value.trim();
  $("llista-equips").className = "nota";
  $("llista-equips").textContent = "Buscant equips i comprovant que tenen partits…";
  const equipos = await llamar("buscar_equipo", texto);
  if (!equipos) { $("llista-equips").textContent = ""; return; }
  tmp.equiposPorEsport[ALTRE] = equipos;
  if (tmp.esport === ALTRE) casillasEquipos(equipos);
}

function pintarListaEquipos() {
  const texto = sinAcentos($("buscar-equip").value.trim());
  casillasEquipos(tmp.equiposPorEsport[tmp.esport].filter(e => sinAcentos(e.nom).includes(texto)));
}

// Una casilla por equipo, con su competición; marcarla lo añade a «El que segueixes»
function casillasEquipos(equipos) {
  if (!equipos.length) {
    $("llista-equips").className = "nota";
    $("llista-equips").textContent = "No he trobat cap equip amb partits publicats amb aquest nom.";
    return;
  }
  $("llista-equips").className = "";
  $("llista-equips").innerHTML = `<div class="rejilla llarga">${equipos.map((e, i) => `
    <label class="opcion"><input type="checkbox" data-equip="${i}" ${sigue(e) ? "checked" : ""}>
      <b>${esc(e.nom)}</b><small>${esc(e.competicio)}</small></label>`).join("")}</div>`;
  document.querySelectorAll("[data-equip]").forEach(el => el.onchange = () => {
    const e = equipos[Number(el.dataset.equip)];
    if (el.checked) { if (!sigue(e)) tmp.equips.push({ lliga: e.lliga, id: e.id, nom: e.nom, competicio: e.competicio }); }
    else tmp.equips = tmp.equips.filter(x => claveEquipo(x) !== claveEquipo(e));
    pintarEquipos();
  });
}

// Lo que se sigue: los equipos y los campeonatos de motor marcados, cada uno con su botón «Treu»
function pintarEquipos() {
  const motor = INICIO.esports.esports.filter(d => d.tipus === "motor" && tmp.motor[d.id]);
  const filas = tmp.equips.map((e, i) => `
    <div class="opcion on"><b>${esc(e.nom)}</b><small style="flex:1">${esc(nomLliga(e))}</small>
      <button class="btn" data-quitar-equip="${i}">Treu</button></div>`).concat(motor.map(d => `
    <div class="opcion on"><b>${esc(d.nombre)}</b><small style="flex:1">campionat sencer</small>
      <button class="btn" data-quitar-motor="${esc(d.id)}">Treu</button></div>`));
  $("equips").innerHTML = filas.length ? filas.join("") : `<div class="nota">Encara no en segueixes cap.</div>`;
  document.querySelectorAll("[data-quitar-equip]").forEach(el => el.onclick = () => {
    tmp.equips.splice(Number(el.dataset.quitarEquip), 1);
    refrescarCasillas();
  });
  document.querySelectorAll("[data-quitar-motor]").forEach(el => el.onclick = () => {
    tmp.motor[el.dataset.quitarMotor] = false;
    refrescarCasillas();
  });
}

// Tras quitar algo de «El que segueixes», la lista de debajo del desplegable se desmarca también
function refrescarCasillas() {
  const tipus = deporte(tmp.esport).tipus;
  if (tipus === "motor") pintarEsport();
  else if (tipus === ALTRE) { if (tmp.equiposPorEsport[ALTRE]) casillasEquipos(tmp.equiposPorEsport[ALTRE]); }
  else if (tmp.equiposPorEsport[tmp.esport]) pintarListaEquipos();
  pintarEquipos();
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
