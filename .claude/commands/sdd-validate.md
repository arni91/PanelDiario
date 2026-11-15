---
description: SDD · Valida la spec RF por RF (tests + Chrome DevTools)
---
Recorre specs/$0/spec.md requisito por requisito. Para cada RF indica qué test
lo cubre y el resultado de ejecutarlo con el comando de tests del proyecto.

Si el proyecto tiene interfaz web, los RF de interfaz que no se puedan testear
así verifícalos con el MCP de Chrome DevTools (incluida la vista móvil de 375 px).

Si algún RF no está cubierto o falla, dilo claramente. NO arregles nada todavía.
Después comprueba los criterios de finalización y dame un veredicto:
¿la spec está cumplida? Si lo está, propón el push y la PR, pero no los hagas sin mi OK.
