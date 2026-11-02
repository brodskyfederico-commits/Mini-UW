# Revisión de venta T39–T40 — prueba interna sintética

El ejemplo original conserva su bloqueo de capacidad de refinanciación. Ninguna revisión de venta lo elimina y no se genera un retorno en esa rama.

La tabla siguiente corresponde exclusivamente a una prueba de software separada: NOI bancario sintético 2000, frente a 50 en el original, y target explícito de aporte adicional de venta. No actualiza el proyecto original ni acredita comparabilidad de NOI, préstamo aprobado, capital disponible o retorno personal. Las demás cifras del ejemplo siguen fijas.

| Revisión | Proceeds brutos | Costos de cierre | Distribución de venta | Aporte de venta requerido | Resultado neto de caja del proyecto |
|---|---:|---:|---:|---:|---:|
| SYNTHETIC-sale-0 | 0.0000 | 20.0000 | 345.9097 | 0.0000 | -101.0803 |
| SYNTHETIC-sale-200 | 200.0000 | 20.0000 | 545.9097 | 0.0000 | 98.9197 |
| SYNTHETIC-sale-400 | 400.0000 | 20.0000 | 745.9097 | 0.0000 | 298.9197 |
| SYNTHETIC-sale-funding-required | 0.0000 | 500.0000 | 0.0000 | 134.0903 | -581.0803 |

Importes de presentación redondeados; cálculos/evidencia usan fracciones exactas. El aporte requerido no equivale a fondos disponibles. Una brecha de caja al corte no prueba pérdida económica definitiva.

Cada revisión pasa por cierre → deuda fechada → continuidad de caja → control de capacidad → ledger de equity del proyecto → retorno/riesgo. Faltantes conservan PENDING. No se selecciona un caso como aprobado.

Pendientes: productores de precio/NOI/exit cap, costos/impuestos que respondan al precio, otros escenarios de financiación/tiempo, términos LP/JV y cierre económico completo. Sin despliegue, decisiones reales ni ampliación a condominios.
