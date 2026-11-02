# T37 — riesgo de caja dentro del alcance Mini-UW

Decisión de alcance del usuario: mejorar el Mini-UW de renta, refinanciación y venta de activo. La ampliación a condominios, preventas y sellout queda para Full UW. No se adoptan parámetros ni instrucciones del PDF profesional por el solo hecho de aparecer allí; sus observaciones al resumen de dos páginas no autentican fórmulas, políticas o aprobación del modelo completo.

Este componente agrega observaciones matemáticas sobre el ledger sintético de equity agregado del proyecto T23. Reproduce exactamente fuente y resultado antes de calcular; conserva fuente, contexto, moneda, horizonte, hash de resultado, versión del código y definición. No modifica fuentes, criterios, ejemplos anteriores ni bloqueos de financiación T35–T36. Un reporte aislado de caja no prueba que el préstamo sea compatible o esté disponible.

## Definiciones acotadas

Con A = aportes brutos, D = distribuciones brutas y S = distribuciones netas de venta clasificadas explícitamente en el ledger:

- Resultado de caja al corte: D − A.
- Aportes no recuperados en caja al corte: max(A − D, 0). Excedente de caja: max(D − A, 0). Ninguno determina por sí solo pérdida económica definitiva; puede quedar activo, deuda, derechos o flujos fuera del horizonte. El campo de pérdida económica final permanece PENDING incluso si existe un evento etiquetado venta.
- Para cada fecha t, B(t) = aportes acumulados − distribuciones acumuladas, con saldo de partida cero dentro del horizonte declarado. Mayor financiación neta acumulada al cierre de fecha = max(0, B(t) para todas las fechas). Se conserva B firmado; no se aplica un piso cero en cada paso que descarte cobros anteriores reutilizables.
- Sin orden intradía documentado, el pico máximo posible dentro de cada fecha es max(0, B previo + aportes brutos de esa fecha). El máximo global de estos valores es una cota superior; el máximo de cierres es una cota inferior del pico dentro del ledger. No son una línea de crédito disponible, el capital contable aún invertido ni una estimación del pico de caja del proyecto/de sus reservas. El ledger no demuestra financiación histórica anterior al horizonte.
- Dependencia de venta: S / D, indefinida cuando D = 0. Se conservan cobros sin venta D − S y brecha aritmética max(A − (D − S), 0). Quitar esos cobros no recalcula operación, deuda, impuestos, retención del activo ni otro plan: no es un escenario sin venta, una sensibilidad o un umbral de equilibrio.
- Aportes adicionales y cash-in de refinanciación permanecen brutos, separados y fechados. Ordenar filas del archivo no declara el orden intradía.

Armonización con el modelo vigente: las distribuciones no se reconstruyen del neto; valor retenido y capital declarado nunca son cobros. El denominador del CoC y la definición de capital aún invertido siguen requiriendo su base explícita. No se sustituyen las métricas 3/4 ni se cambia el EM. No se introduce un umbral de riesgo o una política de inversión.

## Límites y pendientes

Se etiqueta siempre retorno del proyecto. Retorno personal del inversor PENDING: no hay reparto LP/JV, preferencia, promote, fees o dilución inferidos. Un reporte calculable puede conservar faltantes de la historia del inversor, IRR no única u otros bloqueos. Falta de un evento, monto, fecha, moneda, procedencia o inventario requerido bloquea todas estas observaciones de caja; ausencia de capital declarado o CoC no borra las cifras de caja válidas.

La hoja sintética no autentica cobros/pagos reales, cierre económico, financiación, disponibilidad de fondos, contrato bancario o rentabilidad individual. No produce un PDF decisorio externo. Los escenarios Downside, break-even y pérdidas finales requieren alcance e inputs explícitos; no se inventan shocks. PASS/FAIL real, despliegue y aprobación profesional siguen deshabilitados. El indicador `risk_analysis_completed` permanece falso.

`summarize_cash_risk(raw, investor_run)` verifica replay T23 y usa fracciones exactas con límite de aritmética; presupuesto excedido bloquea sin resultados parciales. `verify_cash_risk` reproduce el reporte y rechaza resultados falsificados aunque su hash haya sido actualizado. Fuente/resultados se pueden conservar como archivos de evidencia; no se agrega un archivo SQLite nuevo ni se afirma recuperación de un bundle runtime T37.

Validación: pruebas con cálculos independientes de pérdida de caja al corte, venta, fechas simultáneas, aportes posteriores a recuperar caja, faltantes, ceros, retención de activo, replay adulterado e inyección de agotamiento del presupuesto aritmético. La demostración interna guarda evidencia sintética; no cierra los casos financieros de aceptación originales.
