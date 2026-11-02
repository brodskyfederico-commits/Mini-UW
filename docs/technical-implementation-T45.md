# T45 — rango condicionado de recuperación de caja por precio y exit cap

Apoya el análisis de pérdida/riesgo pedido en la revisión profesional (p.1, punto 2), bajo el perfil acotado de costos T43–T44. No certifica un precio soportado ni un break-even financiero completo. El resultado sigue PENDING y no es un criterio de inversión.

## Condiciones de entrada

Se reproduce la cadena completa T44, desde NOI/valor/costos a cierre/deuda/caja/capacidad y retorno. Una base bloqueada por banco, impuesto sin regla, faltantes o conflicto no produce el análisis. Se suministran además hash exacto del resultado base, un dominio cerrado finito de precios no negativos que contenga el precio base y referencias explícitas de validez hipotética del perfil de cargos y de otras fuentes fijas sobre ese dominio.

El análisis no borra una valoración previa: si el cierre contiene una declaración de valoración, solo se admite el dominio puntual del precio base. Un dominio más amplio exige resolver su consistencia en una revisión separada. No se extrapolan cargos a un rango por defecto. No se afirma que sus fuentes/contratos reales sean lineales o válidos sobre todo el rango.

## Identidad y solución

Con costos de cierre F + rP (suma explícita de fijos y fracciones del precio bruto), otros flujos y deuda fijos, el resultado agregado de caja del proyecto es G(P) = (1 − r)P + b. El intercepto se obtiene del retorno base reproducido: b = G(P0) − (1 − r)P0. La identidad conserva distribución=max(Z,0) y aporte=max(−Z,0) al cierre: D−A=Z, incluso al cruzar el residual cero. No sustituye el EM bruto por un múltiplo de flujos netos.

Se resuelve G(P) ≥ 0 dentro del dominio declarado. Si la pendiente es positiva puede resultar un piso; si es negativa, un techo; si es cero, todo el dominio o ninguno. No se divide por cero, no se presupone que mayores precios mejoren el resultado cuando los costos declarados superan 100% del bruto, y no se genera automáticamente un caso a la frontera para obtener PASS. Una frontera de resultado cero fuera del dominio no se presenta como alcanzable.

Para NOI forward fijo N y cap c > 0, se transforma el conjunto de precios mediante P=N/c, conservando extremos e inclusión. Con N>0, P=0 no corresponde a cap finito: un límite de precio cero produce extremo de cap abierto/no acotado, no una tasa infinita. Con N=0, P=0 para cualquier cap positivo; solo existe conjunto de caps de recuperación si cero pertenece al rango de precios que recupera caja.

La equivalencia con EM≥1 se etiqueta solo cuando hay aportes brutos positivos ajenos al cash-in variable de esa venta; así el denominador permanece positivo sobre el dominio. En otros casos no se inventa un EM definido. Recuperar caja al corte no implica pérdida económica final cero ni retorno personal del LP.

## Límites y evidencia

Este bloque no produce nuevos escenarios o ledgers ni prueba que sus requerimientos de cash-in tengan financiación/targets válidos en todos los precios. Cualquier precio a evaluar como nuevo caso debe recorrer T44 con sus propios inputs y controles. No valida impuestos, comisiones, relación económica NOI/cap, crédito, disponibilidad de capital, prórrogas, fechas o reacción de otras variables al precio.

Pruebas independientes verifican la identidad base, frontera exacta y signos a ambos lados, dominios truncados, pendientes positiva/cero/negativa, NOI cero y extremos de cap, guardas de base/domino/fuentes, replay adulterado y agotamiento aritmético inyectado. No se alteran fuentes originales, parámetros, criterios o resultados anteriores. No hay aprobación financiera, despliegue ni bundle SQLite runtime nuevo.
