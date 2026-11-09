// Funciones compartidas por el panel y el asistente.

// Escapa un texto para insertarlo en HTML sin riesgo.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
