---
name: sdd
description: Úsala siempre que trabajes con Spec-Driven Development en este proyecto (docs/constitution.md o cualquier archivo dentro de specs/) - redactar, revisar o cambiar specs, planes y tareas, o implementar y validar tareas de una spec.
---
# Spec-Driven Development (SDD)
## Flujo
Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación → Cambio.
- Nunca pases a la siguiente fase sin la aprobación explícita del usuario.
- La spec manda: si algo no está en la spec, no se implementa. Si falta una decisión, para y pregunta.
- Un cambio de requisitos se hace primero en la spec, luego en el plan y las tareas, y por último en el código.
- La clarificación se puede repetir después del plan o de las tareas si algo no está claro.
- Cada spec vive en su carpeta: `specs/NNN-nombre/` con `spec.md`, `plan.md` y `tasks.md`.
- Al terminar cada fase, actualiza `.privado/memoria.md` (fuera de git).
## Plantilla de spec (spec.md)
```
# Spec NNN — <Nombre>
Estado: borrador | aprobada | implementada
## Contexto y objetivo
## Usuarios
## Historias de usuario
- HU-1. Como <rol>, quiero <acción> para <beneficio>.
## Definiciones (solo si hay términos que puedan interpretarse de varias formas)
## Requisitos funcionales
## Requisitos no funcionales
## Casos límite
## Fuera de alcance
## Criterios de finalización
## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```
La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos.
## Requisitos en EARS (en español)
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-x: EL SISTEMA <comportamiento permanente>.
Cada RF debe ser verificable: nada de "rápido", "intenso" o "bonito" sin un criterio medible.
## Plan (plan.md)
Archivos y responsabilidades · Funciones puras (lo que dependa del reloj, del disco o de la red entra como parámetro) · Algoritmo en pseudocódigo · Interfaz · Decisiones justificadas con su alternativa descartada · Estrategia de tests con el comando de tests del proyecto (`AGENTS.md` → Comandos). Indica qué RF cubre cada parte.
## Tareas (tasks.md)
```
- [ ] **Tn. <Descripción>.** RF-x, RF-y
  - Hecho cuando: <comprobación verificable>.
```
Máximo 20-30 min por tarea, en orden de dependencia. Si salen más de 10, propón dividir la spec.
## Implementación
Una sola tarea cada vez: tests primero (en rojo), después el código, tests en verde, marcar la tarea y parar.
## Git (reglas de `C:\dev\AGENTS.md`)
- Una rama por spec desde `main`: `feat/NNN-nombre` (o `fix/`, `docs/`…).
- Un commit local por tarea, en inglés (Conventional Commits) y sin atribución a Claude.
- Push, PR y fusión solo después de validar la spec y con el OK del usuario.
## Multiagente (opcional, Claude Code)
- Agentes en `.claude/agents/`: coordinator (sesión principal, solo coordina y habla con el usuario) → planner (spec, plan y tareas) → implementer (una tarea, tests primero) → reviewer (clarificación y validación). Se arranca con `claude --agent coordinator`; un subagente no puede lanzar subagentes.
- Cuándo: una funcionalidad con spec. Para cambios pequeños, `/feature` o una sesión normal.
- Ahorro de tokens: el coordinador pasa rutas y decisiones, no contenidos; un solo reviewer por fase (varios solo si el usuario lo pide); tareas pequeñas de lógica relacionadas, en una sola llamada al implementer si el usuario lo aprueba con las tareas; Chrome DevTools solo en tareas visuales; en la validación, el reviewer se apoya en la verificación visual del implementer; al cerrar, el coordinador informa de los tokens aproximados de los subagentes.
