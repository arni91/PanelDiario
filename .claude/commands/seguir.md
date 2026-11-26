---
description: Retoma el proyecto donde se quedó (lee memoria, git y la spec activa) y continúa
---
Retoma el proyecto donde se quedó (cambio de IA o de sesión). No me preguntes qué hacer:
lo dice el propio proyecto. Notas adicionales: $ARGUMENTS

1. Lee AGENTS.md, la memoria del proyecto (.privado/memoria.md o MEMORY.md, la que exista;
   busca la línea «Siguiente paso:»), `git status` y `git log --oneline -5`.
2. Localiza la spec activa: la de la rama actual (feat/NNN-...) o la que diga «Siguiente paso:»,
   y lee su specs/NNN-*/tasks.md (y plan.md si hay que implementar). Usa la skill sdd.
3. Dime en 3-5 líneas: proyecto, spec y fase, tareas hechas/pendientes y lo que vas a hacer.
4. Continúa con ese siguiente paso siguiendo las reglas de siempre (una tarea cada vez, tests
   primero, commit local, marcar la tarea y actualizar «Siguiente paso:» en la memoria).
5. Si hay trabajo sin commit que no entiendes, o el paso necesita una decisión mía, para y
   pregunta en vez de adivinar.
