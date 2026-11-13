// Pestañas de noticias: vienen de config.json ("pestanas"), cada una con id, nombre y,
// si mira más atrás en el tiempo, "filtro_periodo" (botones de esta semana / este mes)
const pestanas = () => (D && D.pestanas) || [];
let periodo = 7;
let pestana = null;   // id de la pestaña abierta; null = la primera
let D = null;
let mostradoEn = 0;

// --- Puente con Python (o datos de demostración en un navegador normal) ---
function api() {
  if (window.pywebview && window.pywebview.api) return window.pywebview.api;
  return {
    obtener: async () => window.__DEMO__ || {},
    refrescar: async () => true,
    abrir: async (u) => { window.open(u, "_blank"); return true; },
    marcar_leido: async () => true,
    ocultar: async () => true,
  };
}


function hace(ts) {
  if (!ts) return "";
  const m = Math.round((Date.now() / 1000 - ts) / 60);
  if (m < 1) return "ara";
  if (m < 60) return `fa ${m} min`;
  const h = Math.round(m / 60);
  return h < 24 ? `fa ${h} h` : `fa ${Math.round(h / 24)} d`;
}

function pct(v) {
  if (v === null || v === undefined) return "—";
  const s = (v > 0 ? "+" : "") + v.toFixed(2).replace(".", ",") + "%";
  return `<span class="${v > 0 ? "up" : v < 0 ? "down" : ""}">${s}</span>`;
}

// --- Render ---
function pintarFecha() {
  const f = new Date().toLocaleDateString("ca-ES", { weekday: "long", day: "numeric", month: "long" });
  document.getElementById("fecha").textContent = f;
}

function pintarAvisos(avisos) {
  const el = document.getElementById("avisos");
  if (!avisos || !avisos.length) { el.innerHTML = ""; return; }
  el.innerHTML = avisos.map(a =>
    `<div class="aviso ${a.nivel}">⚠️ Avís ${({ amarillo: "groc", naranja: "taronja", rojo: "vermell" })[a.nivel] || a.nivel}: ${esc(a.evento)} · ${esc(a.zona)}${a.cuando ? " · " + esc(a.cuando) : ""}</div>`
  ).join("");
  el.style.display = "flex"; el.style.flexDirection = "column"; el.style.gap = "6px";
}

function pintarTiempo(t) {
  const el = document.getElementById("tiempo");
  if (!t) { el.innerHTML = `<div class="vacio">Encara no hi ha dades del temps.</div>`; return; }
  const maxLl = Math.max(...t.horas.map(h => h.lluvia), 1);
  el.innerHTML = `
    <div class="tiempo-top">
      <div class="ico">${t.icono}</div>
      <div class="temp">${t.temp}°</div>
      <div class="desc">
        <b>${esc(t.texto)}</b>
        <span>Sensació ${t.sensacion}° · Vent ${t.viento} km/h</span><br>
        <span>${esc(t.lugar)} · ☀ ${t.salida_sol}–${t.puesta_sol}</span>
      </div>
    </div>
    <div class="horas">
      ${t.horas.map(h => `
        <div class="hora">
          <div class="muted">${h.hora}</div>
          <div class="i">${h.icono}</div>
          <div class="t">${h.temp}°</div>
          <div class="barra"><div style="height:${Math.max(2, Math.round(h.lluvia / 100 * 22))}px; opacity:${h.lluvia ? .85 : .2}"></div></div>
          <div class="p">${h.lluvia ? h.lluvia + "%" : ""}</div>
        </div>`).join("")}
    </div>
    <div class="dias">
      ${t.dias.map(d => `
        <div class="dia" title="${esc(d.texto)}">
          <div class="n">${esc(d.dia)}</div>
          <div class="i">${d.icono}</div>
          <div><span class="mx">${d.max}°</span> <span class="mn">${d.min}°</span></div>
          <div class="p">${d.lluvia ? "💧" + d.lluvia + "%" : "&nbsp;"}</div>
        </div>`).join("")}
    </div>`;
}

// --- Secciones sin configurar (falta su clave o dato en config.json): se ocultan y el pie dice qué falta ---
function sinConfigurar(s) {
  const falta = [];
  if (s.agenda && s.agenda.sin_url) falta.push("agenda (adreça iCal)");
  return falta;
}

function ocultarSi(el, ocultar) {
  el.style.display = ocultar ? "none" : "";
  return ocultar;
}

// --- Agenda (Google Calendar). verSemana = mostrar los próximos días además de hoy ---
let verSemana = false;
function pintarAgenda(a, error) {
  const el = document.getElementById("agenda");
  const cab = (botones) => `<div class="agenda-cab"><h3>📅 Agenda</h3>${botones}
    <button class="mini-btn" data-url="https://calendar.google.com/calendar/r">Obre Calendar ↗</button></div>`;
  if (ocultarSi(el, !!(a && a.sin_url))) return;
  if (!a) {
    el.innerHTML = cab("") + `<div class="nota">${error ? "Google Calendar no respon ara." : "Encara no hi ha dades."}</div>`;
    return;
  }
  const botones = `<button class="mini-btn ${verSemana ? "" : "on"}" data-agenda="hoy">Avui</button>
                   <button class="mini-btn ${verSemana ? "on" : ""}" data-agenda="semana">Setmana</button>`;
  const lista = (a.eventos || []).filter(e => verSemana || e.es_hoy);
  if (!lista.length) {
    el.innerHTML = cab(botones) + `<div class="nota">${verSemana ? "Res els propers dies." : "Avui no tens res al calendari."}</div>`;
    return;
  }
  let html = "", diaActual = null;
  for (const e of lista) {
    if (verSemana && e.dia !== diaActual) { diaActual = e.dia; html += `<div class="dia-cab">${esc(e.dia)}</div>`; }
    html += `<div class="ev">
      <div class="h">${e.todo_el_dia ? "Tot el dia" : esc(e.hora)}</div>
      <div><div class="t" title="${esc(e.titulo)}">${esc(e.titulo)}</div>
        ${e.lugar || e.hora_fin ? `<div class="l">${e.hora_fin ? "fins a les " + esc(e.hora_fin) : ""}${e.lugar && e.hora_fin ? " · " : ""}${
          e.enlace ? `<a data-url="${esc(e.enlace)}" title="${esc(e.enlace)}">${esc(e.lugar)}</a>` : esc(e.lugar)}</div>` : ""}
      </div></div>`;
  }
  el.innerHTML = cab(botones) + html;
}

// --- Planes de los próximos días. verTot = toda la agenda; si no, solo los de los interesos ---
let verTot = false;
function pintarPlans(p, error) {
  const el = document.getElementById("plans");
  if (ocultarSi(el, !p || !!p.sin_configurar)) return;
  // Sin interesos que coincidan, «Per a tu» estaría vacío: se enseña toda la agenda
  const tot = verTot || !p.per_a_tu.length;
  const botones = p.per_a_tu.length
    ? `<button class="mini-btn ${tot ? "" : "on"}" data-plans="per">Per a tu</button>
       <button class="mini-btn ${tot ? "on" : ""}" data-plans="tot">Tot</button>` : "";
  const lista = tot ? p.tot : p.per_a_tu;
  const filas = lista.length ? lista.map(x => `<div class="ev plan" data-url="${esc(x.enllac)}" title="${esc(x.enllac)}">
      <div class="h">${esc(x.quan)}</div>
      <div><div class="t">${esc(x.titol)}</div>
        <div class="l">${esc(x.lloc)}${x.gratuit ? " · gratuït" : ""}</div>
        ${x.interessos.length ? `<div class="meta">${x.interessos.map(i => `<span class="chip tema">${esc(i)}</span>`).join("")}</div>` : ""}
      </div></div>`).join("")
    : `<div class="nota">No hi ha plans a ${esc(p.ciutat)} els propers ${p.dies} dies.</div>`;
  el.innerHTML = `<div class="agenda-cab"><h3>🎭 Plans a ${esc(p.ciutat)}</h3>${botones}</div>${filas}
    ${error ? `<div class="dd-aviso">⚠ Dada desactualitzada: l'Agenda Cultural no respon</div>` : ""}`;
}

// --- Deportes: próximos partidos y último resultado de cada equipo, y los campeonatos de motor ---
const rivalTxt = (p) => `${p.local ? "vs" : "@"} ${esc(p.rival)}`;

function bloqueEquipo(e) {
  const [prox, ...resto] = e.proxims || [];
  let html = `<div class="equip"><b>${esc(e.nom)}</b>`;
  html += prox
    ? `<div class="partido-prox"><b>${rivalTxt(prox)}</b><div>${esc(prox.data)} · ${esc(prox.hora)}</div>
        <div class="c">${esc(prox.competicio)}</div></div>`
    : `<div class="nota">No hi ha propers partits publicats.</div>`;
  const sec = resto.map(p => `<div>${esc(p.data)} · ${rivalTxt(p)}</div>`);
  const u = e.ultim;
  if (u && u.gols_equip !== null && u.gols_equip !== undefined) {
    sec.push(`<div>Últim: <span class="res ${u.resultat}">${u.gols_equip}-${u.gols_rival}</span> ${rivalTxt(u)}</div>`);
  }
  if (sec.length) html += `<div class="partido-sec">${sec.join("")}</div>`;
  return html + `</div>`;
}

// F1 y MotoGP: próxima carrera y ganador de la última
function bloqueMotor(nombre, m) {
  return `<div class="equip"><b>${nombre}</b>
    ${m.proxim ? `<div class="partido-prox"><b>${esc(m.proxim.nom)}</b><div>${esc(m.proxim.data)}</div></div>` : ""}
    ${m.ultim ? `<div class="partido-sec"><div>Últim: ${esc(m.ultim.nom)} · 🏆 ${esc(m.ultim.guanyador)}</div></div>` : ""}</div>`;
}

function pintarEsports(b, error) {
  const el = document.getElementById("esports");
  if (ocultarSi(el, !b || !!b.sin_configurar)) return;
  let html = `<h3>🏅 Esports</h3>` + (b.equips || []).map(bloqueEquipo).join("");
  if (b.f1) html += bloqueMotor("Fórmula 1", b.f1);
  if (b.motogp) html += bloqueMotor("MotoGP", b.motogp);
  if (error) html += `<div class="dd-aviso">⚠ Dada desactualitzada: la font d'esports no respon</div>`;
  el.innerHTML = html;
}

// --- Calidad del aire (índice europeo) y polen de hoy ---
// Color de cada tramo del índice: de bona (verde) a extremadament dolenta (granate)
const COLORES_AIRE = ["var(--up)", "#8bd17c", "#f2c94c", "#f2994a", "#eb5757", "#a33ea1"];

function pintarAire(a, error) {
  const el = document.getElementById("aire");
  if (ocultarSi(el, !a || !!a.sin_configurar)) return;
  const pollen = a.pollen.length
    ? a.pollen.map(p => `${esc(p.nom)} <b>${esc(p.nivell)}</b> <span class="muted">(${coma(p.valor, 0)} grans/m³)</span>`).join(" · ")
    : `<span class="muted">res destacable avui</span>`;
  el.innerHTML = `<h3>🌿 Aire i pol·len</h3>
    <div class="aire-fila"><span class="punt" style="background:${COLORES_AIRE[a.nivell] || COLORES_AIRE[0]}"></span>
      Qualitat de l'aire: <b>${esc(a.qualitat)}</b> <span class="muted">(índex ${a.ica})</span></div>
    <div class="aire-fila">Pol·len: ${pollen}</div>
    ${error ? `<div class="dd-aviso">⚠ Dada desactualitzada: Open-Meteo no respon</div>` : ""}`;
}

// --- Precio de la luz: ahora, el día en barras y las horas más baratas ---
const euros = (n, dec = 3) => coma(n, dec) + " €";
// Barata (verde) por debajo del 90 % de la media del día, cara (roja) por encima del 110 %
const colorLlum = (preu, mitjana) => preu <= mitjana * 0.9 ? "var(--up)" : preu >= mitjana * 1.1 ? "var(--down)" : "#f2c94c";

function pintarLlum(l, error) {
  const el = document.getElementById("llum");
  if (ocultarSi(el, !l || !!l.sin_configurar)) return;
  const max = Math.max(...l.hores.map(h => h.preu));
  const ara = new Date().getHours();
  el.innerHTML = `<h3>⚡ Preu de la llum</h3>
    <div class="llum-top">
      ${l.ara !== null ? `<div class="llum-ara" style="color:${colorLlum(l.ara, l.mitjana)}">${euros(l.ara)}</div>` : ""}
      <div class="llum-txt">per kWh ara · mitjana d'avui ${euros(l.mitjana)}<br>
        Més barata a les <b>${l.min.h} h</b> (${euros(l.min.preu)}) · més cara a les <b>${l.max.h} h</b> (${euros(l.max.preu)})</div>
    </div>
    <div class="llum-barres">${l.hores.map(h => `
      <div class="${h.h === ara ? "ara" : ""}" title="${h.h} h: ${euros(h.preu)}"
        style="height:${Math.max(8, Math.round(h.preu / max * 100))}%; background:${colorLlum(h.preu, l.mitjana)}"></div>`).join("")}
    </div>
    <div class="llum-eix"><span>0 h</span><span>6 h</span><span>12 h</span><span>18 h</span><span>23 h</span></div>
    <div class="muted llum-nota">Les 3 hores més barates: ${l.barates.map(h => h + " h").join(", ")}</div>
    ${error ? `<div class="dd-aviso">⚠ Dada desactualitzada: Red Eléctrica no respon</div>` : ""}`;
}

// --- Carburantes: precio medio de cada combustible en la provincia ---
function pintarCarburants(c, error) {
  const el = document.getElementById("carburants");
  if (ocultarSi(el, !c || !!c.sin_configurar)) return;
  el.innerHTML = `<h3>⛽ Carburants · preu mitjà a ${esc(c.provincia)}</h3>
    <div class="gas">${c.preus.map(p => `<div><small class="muted">${esc(p.nom)}</small>
      <b>${p.mitjana !== null ? euros(p.mitjana) : "—"}</b></div>`).join("")}</div>
    ${error ? `<div class="dd-aviso">⚠ Dada desactualitzada: el Ministeri no respon</div>` : ""}`;
}

// --- Borsa: índices con la variación del día y listas de valores del día ---
// Precio con separador de miles y dos decimales, al estilo catalán (12.000,00)
const preuCa = (n) => Number(n).toLocaleString("ca-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function filaMercat(nom, detall, preu, canvi) {
  const cls = canvi > 0 ? "puja" : canvi < 0 ? "baixa" : "";
  return `<span class="nom">${esc(nom)}${detall ? `<small>${esc(detall)}</small>` : ""}</span>
    <span class="preu">${preu === null || preu === undefined ? "" : preuCa(preu)}</span>
    <span class="canvi ${cls}">${canvi > 0 ? "+" : ""}${coma(canvi)} %</span>`;
}

function pintarBorsa(b, error) {
  const el = document.getElementById("borsa");
  if (ocultarSi(el, !b || !!b.sin_configurar)) return;
  const indexs = (b.indexs || []).map(i => filaMercat(i.nom, "", i.preu, i.canvi_pct)).join("");
  const llistes = (b.moviments || []).map(m => `<div class="mercat-sub">${esc(m.nombre)}</div>
    <div class="mercat">${m.valors.map(v => filaMercat(v.nom, v.simbol, v.preu, v.canvi_pct)).join("")}</div>`).join("");
  const hora = (b.indexs || [])[0] ? ` · ${esc(b.indexs[0].hora)}` : "";
  el.innerHTML = `<h3>📈 Borsa${hora}</h3>
    ${indexs ? `<div class="mercat">${indexs}</div>` : ""}${llistes}
    ${error ? `<div class="dd-aviso">⚠ Dada desactualitzada: Yahoo Finance no respon</div>` : ""}`;
}

// --- Caídas del ETF desde su máximo y compras extra (en % sobre la aportación habitual) ---
const coma = (n, dec = 2) => Number(n).toFixed(dec).replace(".", ",");

// Colores por nivel (0 = sin caída relevante). Si hay más niveles, se repite el último.
const COLORES_NIVEL = ["var(--up)", "#f2c94c", "#f2994a", "#eb5757", "#c81e3c"];
const colorNivel = (i) => COLORES_NIVEL[Math.min(i, COLORES_NIVEL.length - 1)];

function pintarDrawdown(d, error) {
  const el = document.getElementById("drawdown");
  if (ocultarSi(el, !!(d && d.sin_configurar))) return;
  if (!d) {
    el.innerHTML = `<h3>📉 Caigudes d'un ETF</h3><div class="nota">${error ? "Yahoo Finance no respon i encara no hi ha cap dada desada." : "Encara no hi ha dades."}</div>`;
    return;
  }
  const n = d.nivel;
  const niveles = d.niveles || [];
  // Barra de 0 % a -50 %: la marca indica dónde estamos (más a la derecha = más caída).
  // Los tramos de color salen de los niveles configurados, así que se adaptan si los cambias.
  const pos = (c) => Math.min(Math.max(-c / 50 * 100, 0), 100);
  const cortes = niveles.map(l => pos(l.umbral));
  const tramos = [0, ...cortes].map((desde, i) =>
    `${colorNivel(i)} ${desde}% ${i < cortes.length ? cortes[i] : 100}%`).join(", ");
  const ticks = niveles.map(l => `<span class="tick" style="left:${pos(l.umbral)}%">${l.umbral}%</span>`).join("");
  // Una casilla por nivel: "si cae X %" → "+Y %" sobre la aportación (o "toda la reserva" en el último)
  const casillas = niveles.map((l, i) => `
    <div class="dd-nivel ${l.alcanzado ? "ok" : ""}" style="${l.alcanzado ? "color:" + colorNivel(i + 1) : ""}">
      <span class="u">${l.alcanzado ? "✓ " : "si cau "}${l.umbral} %</span>
      <span class="p">${l.toda_la_reserva ? "Tot" : "+" + l.extra_pct + " %"}</span>
      <span class="e">${l.toda_la_reserva ? "tota la reserva" : "d'aportació"}</span>
    </div>`).join("");
  const actual = niveles[n - 1];
  let accion;
  if (n === 0) accion = "Tot normal: aquest mes fes la teva aportació habitual. Sense extra.";
  else if (actual.toda_la_reserva) accion = `Caiguda de ${actual.umbral} % o més: hi poses tota la reserva.`;
  else accion = `Caiguda de ${actual.umbral} % o més: aquest mes aporta un ${actual.extra_pct} % més de l'habitual.`;
  el.innerHTML = `
    <div class="dd-cab"><h3>📉 ${esc(d.nombre)}</h3>
      <span class="pr">${coma(d.precio)} ${esc(d.moneda)} · ${esc(d.hora)}</span></div>
    <div class="dd-top">
      <div class="dd-caida" style="color:${colorNivel(n)}">${coma(d.caida, 1)} %</div>
      <div class="dd-info">des del màxim històric<br>
        Màxim: <b>${coma(d.maximo)} ${esc(d.moneda)}</b> (${esc(d.fecha_maximo)})</div>
    </div>
    <div class="dd-barra" style="background:linear-gradient(90deg, ${tramos})">
      <span class="marca" style="left:${pos(d.caida)}%"></span>${ticks}</div>
    <div class="dd-niveles">${casillas}</div>
    <div class="dd-accion" style="color:${colorNivel(n)}">${accion}</div>
    ${d.desactualizado ? `<div class="dd-aviso" title="${esc(d.error || "")}">⚠ Dada desactualitzada (última: ${esc(d.hora)})</div>` : ""}
    <div class="nota" style="margin-top:6px">Històric de ${esc(d.ticker)} des del ${esc(d.primer_dato)}</div>`;
}

function pestanaActual() {
  const lista = pestanas();
  return lista.find(p => p.id === pestana) || lista[0] || null;
}

function pintarTabs() {
  const actual = pestanaActual();
  document.getElementById("tabs").innerHTML = pestanas().map(p =>
    `<button class="tab ${p === actual ? "on" : ""}" data-tab="${esc(p.id)}">${esc(p.nombre)}</button>`).join("");
}

function pintarLista() {
  const el = document.getElementById("lista");
  const s = (D && D.secciones) || {};
  const actual = pestanaActual();
  let lista = (actual && (s.noticias || {})[actual.id]) || [];
  // Las pestañas con "filtro_periodo" miran un mes atrás: se pueden filtrar por semana o mes
  const conPeriodo = !!(actual && actual.filtro_periodo);
  document.getElementById("periodo").innerHTML = conPeriodo
    ? `<button class="mini-btn ${periodo === 7 ? "on" : ""}" data-periodo="7">Aquesta setmana</button>
       <button class="mini-btn ${periodo === 30 ? "on" : ""}" data-periodo="30">Aquest mes</button>`
    : "";
  if (conPeriodo) {
    // Filtra por fecha de publicación de la noticia (no es la fecha del evento)
    const limite = Date.now() / 1000 - periodo * 86400;
    lista = lista.filter(n => !n.ts || n.ts >= limite);
  }
  const leidos = new Set((D && D.leidos) || []);
  if (!lista.length) {
    el.innerHTML = `<div class="vacio">${conPeriodo ? "Res de nou en aquest període." : "Encara no hi ha titulars en aquesta secció."}</div>`;
    return;
  }
  el.innerHTML = lista.map(n => {
    // Una etiqueta por medio que lo publica (el del titular primero)
    const medios = [n.medio, ...(n.otros_medios || [])];
    // En las pestañas con periodo se muestra también el resumen de la fuente (dónde, cuándo, de qué va)
    const resumen = (conPeriodo ? n.resumen : "") || "";
    return `<div class="noti ${leidos.has(n.enlace) ? "leida" : ""}" data-url="${esc(n.enlace)}"
              title="${esc(medios.join("\n"))}">
      <div class="tit">${esc(n.titulo)}</div>
      ${resumen ? `<div class="resum">${esc(resumen)}</div>` : ""}
      <div class="meta">
        ${medios.slice(0, 3).map(m => `<span class="etiqueta"><span class="medio">${esc(m)}</span></span>`).join("")}
        ${medios.length > 3 ? `<span class="chip">+${medios.length - 3}</span>` : ""}
        <span>${hace(n.ts)}</span>
        ${n.tema ? `<span class="chip tema">${esc(n.tema)}</span>` : ""}
      </div>
    </div>`;
  }).join("");
}

function pintarPie() {
  const pie = document.getElementById("pie");
  const caidas = (D && D.fuentes_caidas) || [];
  const err = (D && D.errores) || {};
  const partes = [];
  const falta = sinConfigurar((D && D.secciones) || {});
  if (falta.length) partes.push(`<span title="Sense configurar: ${esc(falta.join(", "))}.\nOmple-ho a config.json (instruccions al README).">⚙ ${falta.length} ${falta.length === 1 ? "secció" : "seccions"} per configurar</span>`);
  if (caidas.length) {
    const lista = caidas.map(c => `${c.fuente} (${c.categoria}): ${c.error}`).join("\n");
    partes.push(`<span class="aviso-f" title="${esc(lista)}">⚠ ${caidas.length} ${caidas.length === 1 ? "font no respon" : "fonts no responen"}</span>`);
  }
  const nombres = { tiempo: "temps", avisos: "avisos", esports: "esports", borsa: "borsa", drawdown: "el teu ETF", noticias: "notícies", agenda: "agenda", aire: "aire i pol·len", llum: "llum", carburants: "carburants", plans: "plans" };
  const fallos = Object.keys(err).map(k => nombres[k] || k);
  if (fallos.length) partes.push(`<span class="aviso-f" title="${esc(Object.entries(err).map(([k, v]) => k + ": " + v).join("\n"))}">⚠ sense actualitzar: ${esc(fallos.join(", "))}</span>`);
  pie.innerHTML = (partes.length ? partes.join(" · ") : "Tot en ordre")
    + `<span style="margin-left:auto">v${esc((D && D.version) || "?")}</span>`;
}

async function cargar() {
  D = await api().obtener();
  const s = (D && D.secciones) || {};
  pintarFecha();
  document.getElementById("actualizado").textContent = D && D.actualizado ? "Act. " + D.actualizado : "";
  document.getElementById("btn-ref").classList.toggle("girando", !!(D && D.actualizando));
  pintarAvisos(s.avisos);
  pintarTiempo(s.tiempo);
  pintarAire(s.aire, D && D.errores && D.errores.aire);
  pintarAgenda(s.agenda, D && D.errores && D.errores.agenda);
  pintarPlans(s.plans, D && D.errores && D.errores.plans);
  pintarLlum(s.llum, D && D.errores && D.errores.llum);
  pintarCarburants(s.carburants, D && D.errores && D.errores.carburants);
  pintarEsports(s.esports, D && D.errores && D.errores.esports);
  pintarBorsa(s.borsa, D && D.errores && D.errores.borsa);
  pintarDrawdown(s.drawdown, D && D.errores && D.errores.drawdown);
  pintarTabs();
  pintarLista();
  pintarPie();
  clearTimeout(temporizador);
  if (D && D.actualizando) temporizador = setTimeout(cargar, 2500);
}
let temporizador = null;

// --- Eventos ---
document.addEventListener("click", async (ev) => {
  const botonPeriodo = ev.target.closest("[data-periodo]");
  if (botonPeriodo) { periodo = Number(botonPeriodo.dataset.periodo); pintarLista(); return; }
  const botonPlans = ev.target.closest("[data-plans]");
  if (botonPlans) {
    verTot = botonPlans.dataset.plans === "tot";
    pintarPlans(D && D.secciones && D.secciones.plans, D && D.errores && D.errores.plans);
    return;
  }
  const botonAgenda = ev.target.closest("[data-agenda]");
  if (botonAgenda) {
    verSemana = botonAgenda.dataset.agenda === "semana";
    pintarAgenda(D && D.secciones && D.secciones.agenda);
    return;
  }
  const tab = ev.target.closest("[data-tab]");
  if (tab) { pestana = tab.dataset.tab; pintarTabs(); pintarLista(); document.getElementById("lista").scrollIntoView({ block: "nearest" }); return; }
  const link = ev.target.closest("[data-url]");
  if (link && link.dataset.url) {
    await api().abrir(link.dataset.url);
    link.classList.add("leida");
    if (D) { D.leidos = D.leidos || []; D.leidos.push(link.dataset.url); }
  }
});
document.getElementById("btn-ref").addEventListener("click", async () => {
  document.getElementById("btn-ref").classList.add("girando");
  await api().refrescar();
  setTimeout(cargar, 1500);
});
document.getElementById("btn-cerrar").addEventListener("click", () => api().ocultar());
document.addEventListener("keydown", (e) => { if (e.key === "Escape") api().ocultar(); });
// Se oculta al hacer clic fuera (Python ignora la pérdida de foco justo después de abrirlo)
window.addEventListener("blur", () => {
  if (arrastrando) return;
  const a = api();
  if (a.ocultar_por_foco) a.ocultar_por_foco(); else if (Date.now() - mostradoEn > 600) a.ocultar();
});

// --- Arrastre propio: mantiene el punto agarrado bajo el cursor (se autocorrige con cualquier escalado) ---
let arrastrando = false;
function hacerArrastrable(el) {
  let agarre = null, ocupado = false, ultimo = null;
  el.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    agarre = { x: e.clientX, y: e.clientY }; arrastrando = true;
    el.setPointerCapture(e.pointerId); e.preventDefault();
  });
  el.addEventListener("pointermove", (e) => { if (agarre) { ultimo = e; empujar(); } });
  const fin = () => { agarre = null; ultimo = null; arrastrando = false; };
  el.addEventListener("pointerup", fin);
  el.addEventListener("pointercancel", fin);
  async function empujar() {
    if (ocupado || !agarre || !ultimo) return;
    const dx = Math.round(ultimo.clientX - agarre.x), dy = Math.round(ultimo.clientY - agarre.y);
    ultimo = null;
    if (!dx && !dy) return;
    const a = api();
    if (!a.mover_rel) return;
    ocupado = true;
    try { await a.mover_rel(dx, dy); } catch (_) {}
    ocupado = false;
  }
}
document.querySelectorAll(".arrastre").forEach(hacerArrastrable);

window.alMostrar = () => { mostradoEn = Date.now(); cargar(); };

let iniciado = false;
function iniciar() {
  if (iniciado) return;
  iniciado = true;
  mostradoEn = Date.now();
  cargar();
  setInterval(() => { if (document.hasFocus()) cargar(); }, 60000);
}
// Arranca cuando el puente con Python está listo (sus métodos pueden llegar después que window.pywebview)
window.addEventListener("pywebviewready", iniciar);
if (window.pywebview && window.pywebview.api && window.pywebview.api.obtener) iniciar();
// En un navegador normal (sin Python) arranca con los datos de demostración
setTimeout(() => { if (!window.pywebview) iniciar(); }, 800);
