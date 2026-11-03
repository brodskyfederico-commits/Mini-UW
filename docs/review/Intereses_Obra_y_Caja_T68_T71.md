# Intereses de obra por desembolsos y su efecto en caja

El ejemplo sintético calcula deuda e intereses antes de la operación a partir de movimientos expresos. Se separan compromiso, disponible declarado, draws acumulados y saldo; no se generan préstamos ni aportes para cerrar un déficit. La decisión continúa PENDING.

| Intervalo | Draw al inicio | Principal expuesto | Factor del intervalo | Interés al final | Fee al inicio | Repago al final | Principal final |
|---|---:|---:|---:|---:|---:|---:|---:|
| Octubre a noviembre de 2026 | 100 | 100 | 1% | 1 | 2 | 0 | 100 |
| Noviembre a diciembre de 2026 | 100 | 200 | 1% | 2 | 2 | 50 | 150 |
| Diciembre de 2026 a enero de 2027 | 50 | 200 | 1% | 2 | 1 | 0 | 200 |

Todos los importes son USD de prueba. El 1% es el factor suministrado para cada intervalo; no es una tasa anual dividida por doce. El fee suministrado es 2% de cada draw bruto. El interés se calcula sobre el saldo previo más el draw inicial, antes del repago final, y se propone pagar al final. Los intereses y fees no se capitalizan en este perfil.

El compromiso no revolvente declarado es 300, los draws brutos suman 250, los repagos 50 y el saldo final es 200. Repagar 50 no restituye capacidad para nuevos draws. Además, cada draw debe caber en el disponible expresamente declarado para ese momento; el cálculo no acredita disponibilidad bancaria real.

La conexión rellena sólo los eventos de deuda vacíos de la caja previa. El aporte inicial de equity es 1.000 y el adicional 400; compra/obra/costos blandos suman 1.000. La identidad del ejemplo es: 1.400 de equity + 250 de draws = 1.000 de usos + 50 de repago + 5 de interés + 5 de fees + 590 de caja libre final. La caja restringida termina en cero.

Un caso separado mantiene el mismo total de equity pero aporta demasiado tarde: queda bloqueado por el déficit inicial, aunque cierre después con fondos. Otro excede el compromiso no revolvente y no se compila. Ambos se recuperan conservando sus bloqueos. Una fuente vencida retira las cifras de la vista actual y conserva la historia.

Todavía no se conectan estos préstamos multidesembolso con un contrato operativo/refi/venta: los perfiles anteriores exigían draw único y permanecen intactos. No se calcula el retorno final ni se presenta EM/IRR desde un alcance intermedio. CoC/capital/equity retenido, base de activos/TDC, convenciones bancarias reales, capitalización, pagos y revisión profesional siguen pendientes. Sin despliegue ni decisiones reales.

[Vista interna actual](Revision_Vigente_Deuda_Obra_T71.md) · [Vista pendiente](Revision_Pendiente_Deuda_Obra_T71.md) · [Evidencia reproducible](synthetic-construction-cash-demo.json) · [Contrato de cálculo y vínculo](../technical-implementation-T68-T69.md).
