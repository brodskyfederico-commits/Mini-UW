# Mínimos y topes de costos de venta — prueba interna sintética

Hipótesis: cargo fijo separado 10; comisión 5% del bruto, mínimo monetario 25 y máximo 40. Son cifras de software, no comisiones o contratos adoptados. Casos compatibles usan las fuentes sintéticas separadas ya identificadas; el banco original NOI 50 y valoración 500 permanecen intactos y bloqueados.

| Caso | Precio bruto | Costo por fórmula original | Costo con límites | Resultado de caja actual del proyecto |
|---|---:|---:|---:|---:|
| floor-price-200 | 200.0000 | 20.0000 | 35.0000 | 83.9197 |
| floor-price-400 | 400.0000 | 30.0000 | 35.0000 | 283.9197 |
| cap-tie-price-800 | 800.0000 | 50.0000 | 50.0000 | 668.9197 |
| cap-price-2000 | 2,000.0000 | 110.0000 | 50.0000 | 1,868.9197 |
| minimum-maximum-conflict | 400.0000 | 30.0000 | Pendiente | Pendiente |
| original-bank-blocked | 500.0000 | 35.0000 | 35.0000 | Pendiente |
| only-bounds-expired | 400.0000 | 30.0000 | 35.0000 | Pendiente |
| only-bounds-review-pending | 400.0000 | 30.0000 | 35.0000 | Pendiente |

Cada cargo conserva su fórmula, monto original, mínimo/tope y límites empatados. Un mínimo superior al máximo bloquea; no se selecciona una cifra para corregirlo. El total sustituye una sola vez el costo de cierre anterior.

La fuente de límites es el binding adicional número 22. Si solo esa fuente vence o sigue sin revisar, se omite la nueva salida actual mientras el cálculo histórico permanece intacto. No se autentican contratos/revisión profesional ni hay monitor automático.

Este perfil puede cambiar de tramo con el precio: el análisis afín anterior no se aplica automáticamente. Recuperación por tramos, contratos/impuestos reales, retorno personal y cierre financiero continúan pendientes. Sin despliegue o decisiones reales.
