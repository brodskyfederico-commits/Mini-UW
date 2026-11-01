# M2 — Ingresos, gastos, NOI y ocupación de equilibrio

Estado: contrato propuesto y validación algebraica aislada. No es motor de producción, política fiscal aprobada ni análisis de un deal. El usuario indica que el Full UW se entregará al final; su workbook no es una precondición para desarrollar estos contratos. La conciliación con ese material permanece diferida. La salida externa del Mini-UW sigue siendo exactamente una página PDF.

## Fuentes y frontera de autoridad

Master v5.1 §3 Revenue/Expenses (SHA-256 95a304fd3e535f16ebd5eb6abf0b223c211f9f596727c878de720779f7ceb701); Input Sheet Inputs!C7:C28 y C57:C62 (b433468ec6cb2ebf6b9950325fef212dc9df365ac9adbca4895ca1df39234600); Manual v2.2 páginas físicas 8–9 y 19; Estándares políticas 5, 6 y 11. Conflictos relacionados SRC-02 y SRC-04. Las relaciones fiscales siguientes formalizan una hipótesis del documento histórico; no verifican ley, exención, valoración fiscal ni coeficientes aplicables en Florida.

## Contratos por salida

Todos los montos de una operación deben compartir moneda y período. El calendario anual/mensual y el devengo/cobro se declaran, no se deducen del nombre NOI.

| ID | Salida / relación candidata | Entradas y evidencia | Bloqueos |
|---|---|---|---|
| M2-01 | Renta mensual de tipo i: r_i por unidad o s_i × área_i por SF | C7, C8:C11; área y conteos explícitos de planos | Q11; dormitorio no equivale a unit type; no convertir GSF a NRSF |
| M2-02 | Renta residencial potencial mensual = Σ n_i × r_i | M2-01, unidades mercado/asequibles documentadas | No duplicar las unidades asequibles dentro del conteo de mercado |
| M2-03 | Ingreso residencial efectivo: potencial menos pérdidas/concesiones más otros ingresos definidos | C13:C15; perfiles por período y reglas de base | No decidir si vacancia afecta other income; no aplicar concesión otra vez si renta ya es neta |
| M2-04 | Comercial histórico: SF × renta NNN anual × (1−vacancia) × (1−no recuperable) | C16:C21, usos y áreas documentados | Definir inicio pos-TCO y si no recuperable reduce ingreso o es gasto; no descontarlo por ambos lados |
| M2-05 | Gastos sin impuesto = controlables + management + seguro + reservas según inclusión aprobada | C57:C60; management histórico sobre EGI residencial C58 | No aplicar fee al ingreso comercial sin regla; distinguir reserva como gasto NOI y movimiento de caja |
| M2-06 | A = ingresos efectivos − gastos operativos sin impuesto | M2-03:M2-05 con mismo período | A no equivale a caja distribuible, ni incluye deuda por defecto |
| M2-07 | NOI e impuesto simultáneos bajo ecuación documentada | A; comparables C62 × unidades si procede; C61; millage, exención, cap y sus fuentes | Q2, ley/coeficientes/valoración no aprobados; comparar montos totales del mismo período |
| M2-08 | Ocupación de equilibrio como conjunto de q factibles con NOI(q) ≥ servicio de deuda aplicable | Ingresos/costos dependientes de q; reglas fiscales; deuda M6 | Q12; definición de ocupación física/económica; no elegir ratio bruto/efectivo del conflicto SRC-02 |

Asequibilidad se mantiene en contrato aparte pendiente: nivel AMI, límite bruto, utility allowance, elegibilidad y techo de mercado requieren fuentes y aprobación; no se instala el porcentaje histórico ni un límite legal presunto.

## Cierre algebraico condicionado de impuesto / NOI (M2-07)

Sólo bajo estas hipótesis explícitas: A es ingreso operativo antes de impuesto; F es impuesto comparable total no negativo; el proxy es k multiplicado por NOI; k es adimensional, fijo y no negativo; no hay otras ramas, topes, pisos ni ajustes fiscales. La ecuación candidata del modelo es:

`N = A − max(F, k N)`

Las ramas son N_F=A−F, admisible cuando F≥k N_F, y N_P=A/(1+k), admisible cuando k N_P≥F. Se obtiene:

`N = min(A−F, A/(1+k)); T = A−N = max(F, k N)`

La igualdad de ramas no necesita un desempate financiero. Cada rama es admisible exactamente por su desigualdad; con k≥0 la función N+max(F,kN) es estrictamente creciente, por lo que la solución es única. Un A negativo puede producir NOI negativo: no se recorta a cero. Si F o k faltan no se calcula; k=0 explícito es distinto de k ausente.

El k histórico se puede expresar como millage × assessment ratio × (1−exención efectiva) / cap, sólo si todas las bases, unidades, períodos y definiciones son compatibles y se aprueba ese modelo. Millage por mil requiere una conversión explícita; no se adivina si el dato ya está expresado como fracción. No se impone que el NOI fiscal, de valoración y de caja sean el mismo sin definición. Cap cero o k fuera del dominio impide usar este cierre.

## Ocupación de equilibrio condicionada (M2-08)

Si, y sólo si, en un tramo validado A(q)=s q+b, con k y F constantes y DS del mismo período, la condición N(q)≥DS equivale a:

`s q+b ≥ DS+max(F,k DS)`

Para s>0, el límite algebraico es q*=(DS+max(F,kDS)−b)/s. El resultado real es la intersección del semiespacio q≥q* con el dominio de ocupación definido (físico, económico y por escenario). No se recorta un q*>1 a 100% para ocultar inviabilidad. Un q*<0 no es una ocupación negativa permitida: puede implicar que todo el dominio es factible. Para s=0, el conjunto es todo o vacío según la desigualdad; para s<0 se invierte el sentido y no se declara automáticamente un mínimo convencional.

Esta formulación no resuelve por autoridad el conflicto bruto/efectivo: demuestra qué componentes harían defendible una fórmula. Otros ingresos, vacancia, management, costos variables, exenciones dependientes de ocupación e impuestos no afines pueden exigir tramos o un solver con dominio explícito. No aplicar la expresión afín fuera de sus hipótesis.

## Invalidación, controles y evidencia

Cambios de mix, renta, área, ocupación, concesiones o gasto invalidan A y descendientes; cambios fiscales invalidan T/NOI y valoración/refi/retornos/precio; cambios de DS invalidan el equilibrio que lo usa. Un criterio de inversión por sí solo no altera un NOI independiente, pero sí comparaciones y precio objetivo dependiente.

Validación aislada: script `references/validate_m2_algebra.py`, resultado `references/m2-validation.json`. Utiliza fracciones exactas y perfiles sintéticos sin datos reales ni criterios de inversión. Comprueba sustitución en la ecuación original, igualdad de ramas, preservación de NOI negativo/cero, conversión dimensional de renta y equivalencia de la desigualdad de equilibrio. No reproduce referencias históricas, no valida elegibilidad fiscal, no prueba extracción de documentos ni certifica un producto. La validación usa el mismo desarrollo algebraico; no es auditoría independiente.

Pendientes que no requieren Full UW: resolver base de other income/concesiones, clasificación de reservas y NNN, contrato de estabilización y calendario, definición de ocupación y política fiscal aplicable. Agrupar preguntas expertas sin contactar a Lorena. El próximo módulo de diseño es presupuesto y calendario M3/M4, con inclusiones C35, contingencias y desembolsos.

## Puente explícito de devengo a caja

[Operación y cierres](operating-settlement-bridges.md) incorpora 26 controles de M2, saldos inicial/final y movimientos operativos del ledger. Conserva discrepancias y bloqueos; no adopta inclusiones de NOI, impuestos o reservas ni convierte NOI en distribución.
