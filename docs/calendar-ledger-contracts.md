# Calendario y ledgers: estructura independiente de políticas financieras

Fuentes de requisitos: traspaso §§3/5/7; contratos M4-01/04/06, M5-06/10, M6-07:10 y M7-04/06:09. Se desarrolla estructura y conciliación con perfiles sintéticos, sin parámetros bancarios, supuestos de mercado o respuestas expertas.

## Calendario explícito

Cada período tiene ID, inicio y fin expresos. La convención de extremos se entrega como parámetro; no se decide si un evento de cierre pertenece al período anterior o siguiente por intuición. La referencia soporta intervalos cerrados a izquierda/abiertos a derecha y la alternativa inversa, sin valor por defecto. Rechaza períodos vacíos, invertidos, superpuestos o IDs repetidos. Si se declara cobertura continua, rechaza huecos; con huecos permitidos, un evento dentro del hueco no se asigna a un período cercano.

No genera mensualidades corrigiendo automáticamente el 31 de enero al último día de febrero ni mueve fechas por fines de semana. Las fechas son ISO y se comprueban como fechas reales. La fracción de año sólo se ilustra para diferencia real de días dividida por denominador explícito; no se selecciona actual/360, actual/365, 30/360, capitalización o calendario bancario de la casa.

Un date_ref de evento debe resolver a una fecha expresamente enlazada. No se interpreta una etiqueta como fecha ni se inventa el día a partir de un índice de mes. La fecha debe pertenecer exactamente al período declarado bajo la convención configurada. Las relaciones temporales TCO/estabilización/refi/maturity/venta siguen siendo entradas/políticas por cerrar.

## Caja, principal y capital bruto

La caja identifica cuentas libres/restringidas del proyecto y contrapartes externas. Los saldos iniciales son explícitos; ausencia no significa cero. Toda transferencia tiene origen/destino, monto bruto no negativo, unidad/moneda/base, fecha/período, contexto y fuente. La reserva restringida se concilia como saldo y movimiento interno, no como gasto o distribución automática.

Cada movimiento de principal lleva debt_id, efecto firmado y vínculo al evento de caja cuando corresponde: draw positivo y principal pagado negativo. Interés capitalizado es un cambio de principal sin caja en esta clase; no inventa un draw. Un pago de interés con draw efectivo se representa por los movimientos reales, no se agrega además otra capitalización del mismo monto. Los ajustes documentados conservan su signo y evidencia.

El ledger rechaza IDs de evento duplicados y uso duplicado de un mismo evento de draw/repago para inflar principal. Un mismo monto en eventos distintos no se elimina automáticamente. Cada draw/repago de caja debe conciliar con un movimiento de principal, mismo debt_id, contexto, monto firmado y período. Las obligaciones que no se modelan como principal no se deducen ni se inventan; su ledger devengado sigue un contrato separado.

Aportes y distribuciones se totalizan por eventos brutos explícitos. Un repago a banco, transferencia a reserva o capitalización no se clasifica como distribución del inversor. Se exige contraparte externa y cuenta del proyecto según el movimiento declarado, sin afirmar autenticidad por etiqueta.

## Conciliación y bloqueos

Por período: caja final = caja inicial + entradas externas − salidas externas, con transferencias internas canceladas en la caja total y conservadas por cuenta. Principal final = principal inicial + efectos de los movimientos de deuda. Comparar saldos derivados contra afirmaciones de cierre explícitas; discrepancias conservan monto afirmado/derivado/residual y bloquean cierre, sin sobrescribir ninguno.

La referencia usa fracciones exactas, no introduce tolerancia financiera. Rechaza moneda/unidad/base o contexto incompatibles, monto/fecha/revisión ausente, evento huérfano y cierre incompleto. Saldos de caja/principal negativos en el fixture simple requieren otra estructura explícita, como sobregiro documentado; no se truncan a cero ni se inventa capital. Los controles por período NO acreditan liquidez intradía ni orden contractual de uso de fondos: eso exige condiciones y secuencia temporal adicionales.

Una conciliación interna sólo acredita las entradas suministradas y su relación aritmética; no demuestra completitud documental, autenticidad bancaria, observancia contractual, solvencia, retorno aprobado o aprobación de deal. La referencia no guarda en bases de datos ni publica reportes financieros.

## Evidencia

`schemas/calendar.schema.json`, `schemas/event-ledger.schema.json` y `references/validate_calendar_ledger.py`. La prueba usa un calendario y eventos ficticios con aportes, draw, costo, reserva, capitalización y repago. Incluye casos negativos de duplicación, períodos, enlaces de deuda y discrepancias; no incorpora valores de Lorena ni actualiza R02.

## Devengos de interés/comisiones y liquidación pendiente

Se añade un ledger explícito de obligaciones: saldo por pagar inicial + devengos − pagos − capitalizaciones + ajustes documentados = saldo por pagar final. Cada obligación se identifica y se vincula al préstamo, clase y fuente. Un devengo no crea caja; un pago de interés/comisión no reduce principal; una capitalización reduce la obligación pendiente y aumenta principal en el mismo monto sin cash draw ficticio.

Los enlaces de pago o capitalización se usan una vez y deben coincidir en contexto, préstamo/obligación, período y monto. Se rechaza capitalización sin contrapartida de obligación, pago de interés/comisión huérfano y doble uso de un mismo movimiento. Los ajustes requieren evidencia; no son un mecanismo para forzar residual cero.

La referencia recibe devengos explícitos, no calcula tasas o fees. No da por supuesto que intereses/comisiones ausentes son cero. Si se declara un ledger sin obligaciones, eso sólo describe el alcance del fixture: no demuestra ausencia de obligaciones reales. Otros devengos operativos, impuestos, obligaciones legales y contingencias no se consideran completos por esta conciliación.

El reporte conserva saldos por pagar junto con principal. Por ello principal no equivale a payoff total. Qué saldo integra una liquidación, penalidades o maturities necesita términos documentados; aquí no se inventa. En el fixture puede permanecer una comisión devengada sin pagar y se informa, en vez de desaparecer dentro de la deuda.

Los saldos iniciales se referencian a `OPENING:<primer período>` y los cierres a `CLOSING:<último período>` como IDs técnicos del fixture, no como convención bancaria. Las fechas y pertenencia de eventos siguen el calendario entregado.
