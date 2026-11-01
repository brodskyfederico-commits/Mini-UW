# Soporte de precio, caja y retorno de una rama reducida — referencia candidata

Se conecta el catálogo de grilla con condiciones derivadas de una hipótesis matemática explícita, mediante `schemas/affine-price-support.schema.json` y `references/validate_affine_price_support.py`. El perfil no sustituye M1–M7 ni la definición de RLV/Q3. No autoriza cotizaciones, underwriting o decisiones de inversión.

## Hipótesis y entradas

Cada escenario declara `C(P)=a+bP`, NOI N independiente de P, aporte inicial único C(P) y distribución terminal única H después de un intervalo regular expresamente identificado. La rama exige a,b,N,H positivos y costo positivo en todo el intervalo declarado, comprobado mediante el extremo inferior. Es una restricción suficiente de este perfil: si no se cumple, la salida queda pendiente, sin concluir que el deal o todos los precios sean inviables.

Los coeficientes, períodos, unidades, moneda, límites, grilla y objetivos se reciben expresamente; no hay umbral histórico, tick o tasa por defecto. La unidad de normalización de precio sólo transforma el polinomio; no cambia el precio económico. El NOI corresponde al período declarado y la TIR es efectiva del intervalo declarado; no se anualiza ni se presume una convención de calendario.

Se exigen criterios propios por escenario, identidad/definición de métrica, aplicabilidad, operador y revisiones de criterio separadas de la revisión de inputs. Un número de revisión de entradas no se utiliza para completar la revisión de un criterio. Las hipótesis conflictivas conservan al menos dos afirmaciones y sus referencias. Un criterio de FAIL o exclusión no se reinterpreta automáticamente como objetivo de soporte.

## Derivación de condiciones

En esta rama positiva:

- NOI/costo = N/C(P).
- Múltiplo de equity = H/C(P).
- TIR periódica única = H/C(P)−1.

Para un objetivo y de NOI/costo, se compara `N−y(a+bP)` con cero. Para objetivo r de TIR, se compara `H−(1+r)(a+bP)` con cero. Se conserva el operador original, incluido el tratamiento de igualdad. Al escribir x=P/unidad monetaria de normalización, el coeficiente lineal incorpora esa unidad de manera expresa.

La equivalencia usa C(P)>0, N/H independientes del precio y exactamente esa serie de equity. Impuestos dependientes del precio, otros aportes/distribuciones, deuda, reservas, cambios de estrategia o flujos irregulares requieren otro contrato: no se obtienen de este perfil ni se aproximan por sus coeficientes.

## Candidato, caja y siguiente punto

El catálogo evalúa la conjunción declarada para todos los escenarios requeridos dentro de su grilla. Cuando existe un candidato conocido, se recalculan en el precio exacto el costo, los dos objetivos y el múltiplo. El aporte cubre el uso inicial y la recepción terminal cubre la distribución final bajo la hipótesis explícita. Son identidades algebraicas de dos instantes; no representan un ledger bancario fechado, disponibilidad de capital o conciliación integral del proyecto.

La raíz de `−C+Hq` es q=C/H, positiva y única por tratarse de grado uno con H>0. Se conserva residual exacto cero, sin elegir tolerancia o una tasa conveniente entre varias. El control también contrasta casos sintéticos contra el aislador general de raíces periódicas, un método distinto; eso no constituye auditoría financiera independiente.

Se comprueba el siguiente incremento permitido. Si sale del dominio, se registra esa circunstancia, sin llamarlo incumplimiento económico. Si queda dentro, se conservan sus condiciones calculadas. Encontrar un candidato y revisar su vecino no certifica por sí solo un máximo: éste exige la cobertura completa del catálogo declarado. Una búsqueda parcial mantiene sus diagnósticos con clasificación indeterminada.

## Asking y límites

El asking se registra aparte. Ausente no significa cero; un cero explícito se conserva. Una cotización fuera del dominio o de la grilla no se admite por redondeo. El dominio desconocido queda diferenciado de un asking desconocido. No se genera ratio asking/RLV porque esta referencia no acredita un RLV de la casa.

El ejemplo sintético produce máximo de grilla 4, costo 10, NOI/costo 1 y TIR periódica 1/5 para uno de los escenarios. El siguiente precio 5 incumple su objetivo de NOI/costo. Con desigualdad estricta cambia el candidato a 3. Estos números son fixtures matemáticos; no completan datos o criterios reales.

La evidencia retiene 42 controles y 144 combinaciones de operadores/precios cotejadas contra división directa de métricas. Incluye normalización, precio fraccional, grilla parcial/vacía, asking, criterios faltantes, conflictos y comparación con aislamiento de raíces. Toda salida conserva PENDING, publicación desautorizada y `approved_rlv=false`. Fuentes auténticas, objetivos de Lorena, definición completa de precio, integración y revisión independiente permanecen abiertas; R02 y la plantilla vacía se mantienen intactos.
