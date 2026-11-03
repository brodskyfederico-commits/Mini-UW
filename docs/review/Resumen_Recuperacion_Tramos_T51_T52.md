# Recuperación por tramos — prueba interna sintética

Hipótesis explícitas: precio en [0,2000], cargo fijo 10 y 5% del bruto limitado a mínimo 25/máximo 40; demás flujos, deuda y fechas fijos. Fuentes compatibles corresponden a la prueba separada de banco NOI 2000 y cierre sin valoración previa; no modifican el proyecto original ni validan contratos o mercado.

| Tramo de precio | Costo total | Resultado de caja del proyecto |
|---|---|---|
| 0 a 500 | 35 | precio − 116,0803 |
| 500 a 800 | 10 + 0,05 × precio | 0,95 × precio − 91,0803 |
| 800 a 2000 | 50 | precio − 131,0803 |

En este ejemplo el conjunto que recupera en caja los aportes es [116.0803, 2,000.0000]. El cap equivalente se conserva como intervalo racional exacto en la evidencia JSON; es una conversión bajo NOI forward fijo 40, no una recomendación o tasa de mercado. La frontera se reprodujo desde dos precios base con todos sus cargos/caja/retornos recalculados.

El modelo también conserva varios intervalos separados, zonas planas en cero, puntos aislados o ausencia de recuperación, comprobados con pruebas sintéticas independientes. No se elige una solución para obtener PASS.

| Caso de vigencia/cálculo | Salida actual |
|---|---|
| base-price-400 | current_synthetic_piecewise_recovery_at_declared_time |
| repriced-base-200 | current_synthetic_piecewise_recovery_at_declared_time |
| only-domain-expired | PENDING |
| only-domain-review-pending | PENDING |
| domain-binding-missing | PENDING |
| changed-domain-with-stale-evidence | PENDING |
| segment-budget-insufficient | PENDING |
| original-bank-blocked | PENDING |

El binding adicional número 23 cubre dominio/hipótesis/presupuesto. Si falta, vence o cambia sin nueva evidencia, la salida actual no expone el análisis; la historia permanece intacta. Bloqueos de banco, valoración y costos se conservan.

Las cifras se redondean solo aquí; cálculos y JSON usan fracciones exactas. La recuperación al corte no prueba pérdida económica final cero ni retorno personal. Nuevos precios requieren sus propios controles de funding y targets; no se genera un ledger nuevo por calcular la frontera. Sin despliegue o decisiones reales.
