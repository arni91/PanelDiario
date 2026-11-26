# Spec 001 — Notícies d'IA
Estado: implementada

## Contexto y objetivo
La inteligencia artificial cambia cada semana: salen modelos nuevos, herramientas y cambios de precio. Hoy el panel solo trae lo que publican las secciones de tecnología de los medios generales, que lo mezclan con móviles, videojuegos o empresas. El objetivo es tener una pestaña de noticias propia de IA con dos tipos de fuentes: los medios especializados (qué pasa y cómo se valora) y los anuncios oficiales de los laboratorios que hacen los modelos (qué sale y cuándo, de primera mano).

## Usuarios
Quien usa el panel y quiere seguir la actualidad de la IA sin ir a buscarla.

## Historias de usuario
- HU-1. Como usuario, quiero una pestaña «IA» en Notícies para ver de un vistazo las novedades de inteligencia artificial.
- HU-2. Como usuario, quiero distinguir un anuncio oficial de un laboratorio de una noticia de un medio, para saber si es la fuente original o una valoración.
- HU-3. Como usuario, quiero poder activarla o quitarla desde el asistente, como el resto de pestañas.

## Definiciones
- **Medio especializado en IA**: medio o sección de un medio que publica sobre todo de IA.
- **Laboratorio**: empresa u organización que desarrolla modelos de IA de referencia y publica sus anuncios en un blog o sala de prensa propios.

## Requisitos funcionales
- RF-1: EL SISTEMA ofrece una sección de noticias «IA» que junta las noticias de los medios especializados y de los laboratorios elegidos.
- RF-2: EL SISTEMA incluye en el catálogo al menos 3 medios especializados en IA y al menos 3 laboratorios, cada uno con un feed que, al añadirlo, responde, es válido, lleva fecha y tiene alguna noticia de los últimos 14 días.
- RF-3: CUANDO una noticia de la pestaña «IA» viene de un laboratorio, EL SISTEMA la marca con la etiqueta «Oficial».
- RF-4: CUANDO el usuario pasa por el asistente, EL SISTEMA ofrece la sección «IA» y sus fuentes igual que las demás secciones (marcar o desmarcar).
- RF-5: MIENTRAS la pestaña «IA» esté abierta, EL SISTEMA permite filtrar por «Aquesta setmana / Aquest mes», porque los laboratorios publican pocas veces al mes.
- RF-6: EL SISTEMA muestra los titulares en su idioma original y los traduce solo si la traducción está activada, como en el resto de pestañas.
- RF-7: SI una fuente de IA no responde, ENTONCES EL SISTEMA muestra el resto y avisa en el pie, como con cualquier fuente.
- RF-8: CUANDO un feed se descarta por no cumplir RF-2, EL SISTEMA (documentación) lo apunta en la lista de descartados con el motivo.

## Requisitos no funcionales
- Fuentes públicas y sin clave.
- Un config.json antiguo sigue funcionando sin la pestaña.
- Interfaz en catalán.

## Casos límite
- Un laboratorio sin noticias en el último mes: la pestaña no se queda vacía mientras haya noticias de los medios.
- La misma noticia publicada por varios medios: sale una vez, con todos los medios (como en Portades).
- Un feed de laboratorio que publica también ofertas de empleo o eventos: si es así, se descarta o se filtra.

## Fuera de alcance
- Un ranking de «los mejores modelos»: no hay una fuente pública y estable para eso. Se puede estudiar en otra spec.
- Resúmenes generados por IA de las noticias.
- Añadir la pestaña sola a los config.json que ya existen (ver dudas).

## Criterios de finalización
- Todos los RF validados, con tests en verde (red simulada).
- README, docs de configuración y lista de fuentes al día.
- Comprobado con `--demo` y la versión subida.

## Decisiones (26-11-2026, el usuario pidió cerrar rápido: se tomaron las propuestas)
- La pestaña se activa desde el asistente; no se añade sola a un config.json que ya existe.
- Idiomas mezclados: los laboratorios y la mayoría de medios, en inglés (con la traducción opcional).
- Medios: Xataka, The Verge, Wired, Ars Technica, TechCrunch y MIT Technology Review (su sección de IA).
  Laboratorios: OpenAI, Anthropic, Google DeepMind, Google AI, Mistral AI y Hugging Face.
  Descartado: Meta AI (sin RSS y, por Google Noticias, la última noticia tenía 25 días).
