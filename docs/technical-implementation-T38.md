# T38 — sensibilidad aislada al cobro neto de venta

Extensión acotada de las observaciones de caja T37, dentro de renta/refinanciación/venta del Mini-UW. No amplía el modelo a condominios ni adopta escenarios Downside. La observación profesional de riesgo/pérdida y dependencia de venta (PDF de revisión, p.1, puntos 2 y 6, registrado en miniuw-improvement-scope.json) motiva este análisis; no certifica su cobertura completa.

## Contrato y cálculo

Entrada: bytes de ledger T23, resultado T23 reproducido exactamente y especificación JSON estricta. La especificación liga hashes de ambos, contexto completo, un ID de distribución neta de venta existente, inventario de 1–12 casos explícitos y referencia de la hipótesis de mantener todos los demás flujos fijos. Cada caso declara cobro neto no negativo, misma moneda/fecha y nueva referencia de fuente, escenario sintético y ejecución distintos. No se genera una grilla de shocks por defecto.

Se sustituye únicamente monto/fuente del evento seleccionado y la identidad del escenario/ejecución. Aportes, otros cobros de venta, operación, refinanciación, fechas, snapshots de capital, bases de CoC y configuración IRR se preservan como hipótesis congeladas, sin afirmar que sigan siendo financieramente compatibles con el cambio. Se conserva el original. Cada caso válido reproduce T23 y T37, muestra aportes/cobros brutos, resultado de caja, brecha al corte, pico de financiación de equity, dependencia de venta, EM y todas las raíces/intervalos IRR obtenidos. No selecciona una tasa si hay varias ni un criterio de inversión.

Si A son todos los aportes, D todos los cobros del ledger base y s el cobro neto del único evento seleccionado, el piso de cobro neto para recuperar en caja todos los aportes, congelando los demás flujos, es max(0, A − (D − s)). Para A > 0, el EM alcanza o supera 1 si el nuevo cobro alcanza ese piso. Si los demás cobros ya superan A, el piso es cero y no implica EM exactamente 1. Con A = 0 el EM sigue indefinido; no se convierte la recuperación de caja en un múltiplo definido.

El piso calculado es una observación, nunca un objetivo insertado automáticamente en los casos ni una propuesta para obtener PASS. Un cobro neto negativo requiere modelar aportes/cash-in explícitos en otro perfil; no se recorta a cero. Cero explícito es distinto de ausente. Un caso con dato requerido faltante se conserva bloqueado; otros casos válidos pueden mostrarse sin afirmar que todo el inventario esté completo. Una incompatibilidad global bloquea todos los casos. Sintaxis/forma no admitida se rechaza sin producir un resultado parcial. Se conserva el bloqueo previo de la historia del inversor aunque las cifras de caja sean calculables.

## Alcance y límites

Este análisis de un cobro neto ya definido no cambia precio bruto, exit cap, costos, impuestos, deuda, reserves o calendario. No calcula el precio/cap de equilibrio ni un plan sin venta/refinanciación; tampoco prueba disponibilidad de fondos, liquidez real o pérdida económica final. Modificar el ledger rompe el vínculo con sus productores de cierre/banco: ese vínculo se señala como no preservado y nunca sustituye el camino guardado T36. Los ejemplos anteriores y su bloqueo de capacidad se mantienen intactos.

Retorno personal PENDING sin términos de reparto. Criterios por deal siguen vacíos, políticas y datos reales pendientes, despliegue/decisiones reales deshabilitados. No se modifica el PDF externo ni se cierra el análisis de riesgo completo. El esquema admite únicamente observaciones sintéticas.

## Evidencia y reproducción

Se conservan versión del código/definición, hash del análisis, hashes de fuentes/ejecuciones y JSON compilado por caso válido. `verify_sale_sensitivity` reproduce fuente, caso y reporte; un hash recalculado de un reporte alterado no basta. No se agrega un bundle SQLite T38 ni se declara restauración de runtime. El demo interno usa casos explícitos 0/300/600 sobre un ejemplo cuya venta base es 900; no son shocks de mercado o parámetros de inversión adoptados. Pruebas independientes verifican identidades, múltiples ventas, cero aportes, piso cero, raíz IRR no única, casos incompletos, inmutabilidad, manipulación y agotamiento de presupuesto inyectado.
