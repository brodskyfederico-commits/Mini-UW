# Costos y recuperación de caja — prueba interna sintética

Perfil declarado: cargo fijo 10 + 5% del precio bruto. Son cifras de prueba, no tasas comerciales o fiscales adoptadas. Los casos compatibles usan fuentes sintéticas separadas con banco NOI 2000 y cierre sin valoración previa; el ejemplo original banco NOI 50/valor 500 permanece intacto y bloqueado.

| Caso | Precio bruto | Costo calculado | Resultado neto de caja del proyecto | Estado técnico |
|---|---:|---:|---:|---|
| original-bank-blocked | 500.0000 | 35.0000 | Pendiente | blocked |
| price-800 | 800.0000 | 50.0000 | 668.9197 | compiled_synthetic |
| price-400 | 400.0000 | 30.0000 | 288.9197 | compiled_synthetic |
| price-200 | 200.0000 | 20.0000 | 98.9197 | compiled_synthetic |
| tax-pending | 400.0000 | Pendiente | Pendiente | blocked |

Dentro del dominio sintético explícito [0,1000], manteniendo otros flujos/deuda/fechas fijos, el resultado es 0,95 × precio − 91,0803. La frontera de recuperación de caja es 95.8740. La misma frontera se reprodujo desde tres precios con sus costos/retornos recalculados. No es un precio soportado aprobado ni una meta de inversión.

Los intervalos de precio y exit cap exactos constan en la evidencia JSON; esta presentación redondea importes. Una nueva evaluación de precio necesita recorrer sus controles de cierre, cash-in y financiación; el rango no prueba fondos disponibles. Impuestos sin regla, banco bloqueado y conflictos conservan PENDING.

No hay cálculo de retorno personal, pérdida económica final, reglas fiscales verificadas, despliegue o decisiones reales.
