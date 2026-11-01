# M8 — Escenarios, sensibilidades y precio soportado

Estado: diseño candidato y referencia matemática acotada. No es motor productivo, RLV certificado, auditoría independiente ni evaluación de un deal. No se instalan los shocks/umbrales de los documentos históricos como parámetros activos; Lorena aportará los criterios por deal. Datos/reglas requeridos faltantes dejan PENDIENTE.

## Fuentes y contratos

Master v5.1 §§3–6 (95a304fd3e535f16ebd5eb6abf0b223c211f9f596727c878de720779f7ceb701); Estándares políticas 3,13,17–33; Manual físico pp.14/17/22–23/27/29/40; traspaso §§5–8. El conflicto Q3 permanece abierto. Las referencias históricas de monotonía no se han recuperado ni reproducido.

| ID | Contrato | Fuente y pendiente |
|---|---|---|
| M8-01 | Inventario de escenarios requeridos | Traspaso §6; Master §4. ID, propósito, aplicabilidad, escenarios requeridos/excluidos y regla de agregación explícitos; nada requerido se omite silenciosamente. |
| M8-02 | Entradas completas y aisladas | Traspaso §6; Master §4 change vs Base. Compartir hechos de fuente sólo mediante referencia explícita a la misma versión; sin herencia automática de supuestos o criterios. |
| M8-03 | Transformación y unidad de cada driver | Master §4 tabla; Estándares políticas 18–33. Distinguir cambio relativo, puntos porcentuales, bps, meses y reemplazo absoluto. Base, delta, unidad, orden y fuente explícitos. |
| M8-04 | Downside integrado y dependencias | Estándares política 3/33; Manual p.17. Aplicar drivers autorizados conjuntamente y recalcular dependientes, no sumar sensibilidades individuales como resultado integrado. |
| M8-05 | Sensibilidad individual y ranking | Master §4 Single-driver; Manual p.14. Mantener iguales los hechos/políticas no afectados con referencias explícitas; reportar métrica de ranking, signo, empate y aplicabilidad. |
| M8-06 | Overrides y condicionales | Estándares políticas 5/33; Manual pp.20/27. Fuente, justificación, alcance, vigencia y autorización; no resolver con confianza de OCR o papel nominal del autor. |
| M8-07 | Controles y vigencia por escenario | Manual pp.17/29; traspaso §§6–7. C1/C2 completos por escenario requerido; versiones de fuentes/fórmulas/criterios coherentes y comparación sólo con resultados vigentes. |
| M8-08 | Robustez y Upside | Master §4 Robustness; política 17/33. Upside no rescata Base. Ensayo histórico de terreno cero requiere configuración expresa; no llamar robusto a un FAIL sin prueba pertinente válida. |
| M8-09 | Precio evaluado, asking y objetivos | Master §3 RLV; Estándares política 13; Q3 p.22. Definir conjunto de restricciones de precio; soporte bajo dos objetivos no es RLV completo aprobado de la casa. |
| M8-10 | Dominio, factibilidad y extremos | Traspaso §5; PRICE-01. Distinguir máximo alcanzado, supremo no alcanzado, conjunto vacío, no acotado o indeterminado. Tramos/discontinuidades y desigualdades explícitos. |
| M8-11 | Método y cotización discreta | Traspaso §§5/8; Master §3 RLV. No asumir monotonía global; verificar candidato y siguiente incremento permitido si hay grilla explícita; ni tick ni tolerancia inventados. |
| M8-12 | Entrega y comparaciones dependientes | Traspaso §6; Master §§5–7. Entregar estado de soporte, restricciones activas, alcance validado y pendientes. Cambiar criterios recalcula objetivos dependientes; asking/RLV exige fórmula vigente. |

## Configuración mínima por escenario

Identificar deal y revisión, escenario/versiones, requerido/no aplicable con razón, propósito y relación autorizada con Base, hechos de fuente compartidos por referencia, valores/supuestos propios y criterios propios expresos. Cada transformación declara campo, valor base, fuente/versionado, operador/unidad, delta o reemplazo, momento, alcance y orden cuando intervienen varias transformaciones. Declarar explícitamente conservación de un valor no modificado; una celda vacía no hereda un dato de otro escenario.

Cambiar una tasa en puntos no equivale a un porcentaje de esa tasa. Los bps se convierten a fracción de tasa de forma explícita; los meses son intervalos, no porcentajes. No recortar vacancia, plazo, cap o tasa a un dominio “típico”: validar el dominio aprobado, informar el bloqueo y conservar el valor original. Un cero documentado del delta representa ningún cambio; delta ausente bloquea. Los cambios de plazo requieren además política Q4/Q5 de costo y reparto.

Los 15 drivers históricos son categorías recuperadas: rentas y vacancias residenciales/comerciales; hard/site/parking; obra y lease-up; tasas construcción/permanente; cap refi/exit; seguro; impuesto; LTV permanente; crecimiento de renta. La existencia de la tabla no demuestra que todos sean aplicables ni define sus valores vigentes.

## Sensibilidades, interacciones y control

Single-driver contrasta una sola transformación autorizada contra una corrida de referencia identificada, conservando explícitamente el resto. Downside integrado reejecuta los drivers aplicables juntos: no se obtiene sumando deltas de resultados de ensayos individuales, porque cambian ramas de impuesto, restricciones de deuda, calendarios y retornos.

El ranking histórico usa Δ cash-in al refi. Debe aclararse dirección (aumento de necesidad de capital, no valor absoluto por defecto), unidad, empate y estrategia sin refi. Si todas las perturbaciones dejan cash-in cero, el resultado es empate o falta de discriminación de esa métrica: no inventar top drivers ni sustituirla silenciosamente por otra. Sensibilidad no es probabilidad ni ponderación de escenarios; no asignar pesos esperados sin datos/regla.

Cada escenario repite completitud e integridad de caja/deuda/convergencia y genera su propia evidencia. Un escenario requerido inválido impide una comparación completa; un resultado Base válido no libera automáticamente el conjunto. Upside no corrige Base; las reglas de agregación y el estado entre bandas históricas siguen pendientes de aprobación. Una prueba de robustez sólo acredita la perturbación y alcance realmente configurados.

## Conjunto de precios y clasificación del resultado

Definir D, dominio de precio evaluado, con moneda, cierres de extremos, admisión de valores negativos si procede, estrategia, incrementos permitidos y escenario/revisión. Un límite de exploración numérica no es necesariamente restricción económica. Un asking ausente es un dato ausente, no el precio cero de un ensayo.

El conjunto factible F contiene sólo precios de D con todas las restricciones y escenarios requeridos definidos y satisfechos. Si algún cálculo/regla requerido no puede evaluarse, no clasificar ese punto como infactible probado: es indeterminado, con causa. Un máximo requiere miembro de F que domine todos sus demás precios; un supremo de intervalo abierto no es precio de compra permitido. F vacío requiere evidencia, no sólo que un algoritmo no encontrara candidato.

Distinguir: máximo alcanzado; supremo no alcanzado; vacío demostrado; factible sin cota superior; o indeterminado/cobertura insuficiente. Un rango numérico explorado y un precio candidato no prueban óptimo global. La política Q3 debe cerrar si el objetivo de precio exige dos métricas o el conjunto completo de condiciones; un resultado parcial se etiqueta soporte parcial, nunca RLV certificado.

## Referencia algebraica deliberadamente reducida

Sólo bajo hipótesis explícitas: precio P, costo C(P)=a+bP con a>0,b>0 y C>0; NOI N>0 independiente de P; objetivo de YoC y>0. YoC≥y equivale a P≤(N/y−a)/b. La equivalencia no se extiende a un NOI dependiente del precio por impuestos o financiación ni a bases de costo no afines.

Para una serie con único aporte inicial C(P) y una sola distribución positiva H al final de un intervalo regular: existe una única tasa r=H/C(P)−1 bajo factor de acumulación positivo. Exigir r≥r_obj, r_obj>−1, equivale a C(P)≤H/(1+r_obj), y a P≤[H/(1+r_obj)−a]/b. Este caso no certifica comparar una IRR cualquiera mediante NPV al objetivo si hay múltiples raíces/otros flujos. No se usa una tasa objetivo histórica por defecto.

La intersección de estas dos cotas y un dominio cerrado puede producir un máximo reducido; otras condiciones desconocidas lo hacen parcial. El precio del incremento inmediatamente superior sólo puede comprobarse con paso/grilla explícitos y límites/objetivos válidos. No redondear primero una cota para declarar que la cotización pasa.

Un contraejemplo factorizable con factibilidad (P−1)(P−3)≥0 dentro de [0,4] da dos componentes [0,1] y [3,4]. Un algoritmo que presuponga factibilidad decreciente puede encontrar la primera frontera y perder el máximo. Este ejemplo demuestra un riesgo de método, no describe el modelo inmobiliario real.

## Evidencia y cierre

`references/validate_m8_scenarios_price.py` y `m8-validation.json` verifican transformaciones dimensionales aisladas, intersección de objetivos reducidos, máximos abiertos/cerrados/discretos y un contraejemplo no monótono. Son casos exactos sintéticos; no solver global, ejecución de escenarios productivos, evidencia de monotonía de todo M1–M7, RLV aprobado ni auditoría independiente.

Faltan fuentes/valores de escenario, objetivos de Lorena y Q3, aplicabilidad, cierres de M1–M7, validación independiente y prueba completa de dominio/método. M8 permanece abierto. El siguiente bloque M9 formalizará comparación, estados pendientes, revisión y publicación de la página sin habilitar producción.

## Ampliación independiente: grilla y ensayos declarados

[Catálogo finito de precios](price-grid-catalogue.md): 52 controles y 324 casos de grilla para relaciones normalizadas recibidas, sin suponer monotonía o convertir búsqueda parcial en máximo. [Ranking con signo](sensitivity-ranking.md): 33 controles de entradas conservadas, métricas compatibles, empates y separación de ensayos conjuntos. No derivan las restricciones económicas ni reejecutan el motor financiero; Q3, criterios reales, fuentes y revisión siguen abiertos.
