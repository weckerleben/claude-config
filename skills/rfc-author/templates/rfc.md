---
id: RFC-NNNN
title: <imperative, one line — "Unificar la pérdida FI y FCB en un solo evento">
status: draft            # draft | in-review | accepted | rejected | superseded
prd: .claude/prds/<slug>.prd.md
adrs: []                 # filled as decisions get extracted
ticket: ODOO-NNN         # null until the ticket exists
variant: []              # omit this key entirely when variant_axis is none
components: []
affects_repos: []        # sibling repos this proposal binds
authors: [William Eckerleben]
date: YYYY-MM-DD
superseded_by: null
published: null          # url once published — this is what the tracker gate needs
---

# RFC-NNNN — <title>

## Resumen

Un párrafo. Qué se propone y qué cambia para quien usa el sistema. Si no entra
en un párrafo, el alcance es demasiado grande y hay más de un RFC acá adentro.

## Motivación

Qué problema resuelve, **enlazando al PRD** — no lo repitas. Una o dos frases
más el link. Si el PRD no dice esto, el PRD está incompleto: arreglá el PRD, no
lo compenses acá.

> Requisito del PRD que este RFC atiende (cita textual, sin traducir):
> WHEN ... THE SYSTEM SHALL ...

## Objetivos

- <resultado observable, no tarea>
- <resultado observable>

## No-objetivos

Obligatorio y específico. Cada línea corta un pedido plausible que este cambio
no va a atender.

- <cosa concreta que NO cambia, aunque parezca que debería>
- <cosa que alguien va a pedir en review y la respuesta es "no, en este RFC no">

## Estado actual

Cómo funciona hoy, con referencias a archivo y línea. Sin esto, el review no
puede juzgar si la propuesta es mejor o solamente distinta.

| Pieza | Dónde | Comportamiento hoy |
|---|---|---|
| | `path/to/file.py:120` | |

## Propuesta

El diseño. Diagramas si el flujo tiene más de tres saltos. Contratos de datos,
nombres de campo, formatos de evento — concreto, no descriptivo.

Sin párrafos de justificación acá. El "por qué esta y no la otra" vive en
**Opciones consideradas**.

### Contrato / interfaz

```
<payload, firma, esquema, o el asiento contable que se emite>
```

### Impacto por variante

<!-- Borrar esta sección entera si el perfil del repo dice variant_axis: none.
     No dejarla con "n/a": una sección siempre vacía deja de leerse. -->

| {variante} | Aplica | Implementación | Componentes |
|---|---|---|---|
| | sí / no / distinta | | |
| | sí / no / distinta | | |

Si la implementación difiere entre variantes: ¿la diferencia es una decisión que
merece ADR propio, o es puramente mecánica? Respondelo acá.

### Repos que quedan atados

<!-- Solo si el perfil declara sibling_repos. Responder aunque la respuesta sea
     "ninguno" — un repo atado en silencio es el modo de falla que esto evita. -->

| Repo | Queda atado | Por qué |
|---|---|---|

## Opciones consideradas

Mínimo dos, una suele ser "no hacer nada". La opción elegida se marca. Esta
tabla es la materia prima del ADR — escribila pensando en que se va a leer
dentro de dos años.

| # | Opción | A favor | En contra | Costo de revertir |
|---|---|---|---|---|
| 1 | **<elegida>** ✅ | | | |
| 2 | <descartada> | | | |
| 3 | No hacer nada | | | |

**Por qué la 1**: dos o tres frases. Si necesitás más, la decisión es un ADR y
acá va solo el link.

## Contras de la propuesta elegida

Escrito por quien propone, sobre su propia propuesta. Si está vacío, la
propuesta no se pensó lo suficiente.

- <lo que empeora, lo que se vuelve más difícil, la deuda que se asume>

## Riesgos y rollback

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|

**Rollback**: los pasos exactos para volver atrás, ejecutables por alguien que
no escribió esto, a las 3 de la mañana. Si el cambio no es reversible, decilo
explícitamente acá — y entonces es un ADR sí o sí.

## Preguntas sin resolver

- [ ] <lo que todavía no sabemos y podría cambiar el diseño>

Cerrar el RFC con preguntas abiertas está bien. Cerrarlo escondiéndolas, no.

## Migración y despliegue

- Datos existentes: <qué pasa con lo que ya está en producción>
- Orden de despliegue: <si hay dependencias entre repos o servicios>
- Feature flag / activación gradual: <sí/no, cuál>

## Criterios de Aceptación

Fuente del campo de aceptación del ticket (`tracker.fields.acceptance`). Cada
cláusula binaria, observable y trazable a un requisito del PRD.

```
WHEN <disparador> THE SYSTEM SHALL <comportamiento>.
IF <condición no deseada> THEN THE SYSTEM SHALL <comportamiento>.

Given <estado>
When <acción>
Then <resultado observable>
```

## Decisiones

Elecciones irreversibles extraídas de este RFC. Cada una es un ADR aparte.

| ADR | Decisión | Estado |
|---|---|---|
| ADR-NNNN | <la elección, no el argumento> | pending / accepted |

## Referencias

- PRD: `<path>`
- ADRs vigentes que condicionan este diseño: ADR-NNNN
- Código: `path:line`
- Tickets: ODOO-NNN
