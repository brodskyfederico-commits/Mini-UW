# Financiación de compra y obra y apertura operativa

El calendario sintético conserva cuánto se aporta antes de la operación y en qué fechas. La caja disponible al empezar a operar es un saldo del proyecto; el cálculo del retorno completo deberá conservar los aportes históricos que la financiaron.

En el ejemplo, entre octubre de 2026 y enero de 2027 se registran estos movimientos en USD:

| Fuentes de caja | Importe |
|---|---:|
| Aporte inicial de equity | 1.500 |
| Aporte adicional de equity | 300 |
| Desembolso recibido de deuda | 600 |
| Otro cobro expresamente declarado | 100 |
| **Total de fuentes** | **2.500** |

| Destino de la caja | Importe |
|---|---:|
| Compra | 400 |
| Obra | 800 |
| Costos blandos | 100 |
| Principal repagado | 100 |
| Interés pagado suministrado | 20 |
| Fee pagado suministrado | 5 |
| Otro pago declarado | 50 |
| Distribución de equity | 25 |
| Caja libre al inicio de la operación | 1.000 |
| **Total de usos y saldo final** | **2.500** |

Una transferencia de 200 a reserva y su liberación de 200 se conservan como movimientos separados. La reserva termina en cero y no se suma a los gastos ni al retorno del inversor. El principal de deuda termina en 500: 600 recibidos menos 100 repagados. El interés y el fee pagados no reducen ese principal.

La caja final coincide con la apertura del período operativo existente: 1.000 libres y cero restringidos. **Este vínculo verifica únicamente la frontera de caja.** Los 500 de principal todavía deben conciliarse con la deuda operativa. Tampoco se han conectado los aportes históricos con el ledger de retorno de toda la inversión; la ventana operativa anterior conserva su alcance.

Los controles conservan los aportes y distribuciones brutos, incluso si coinciden en fecha. Un dato faltante bloquea las exportaciones, y un déficit al cierre de una fecha permanece pendiente aunque llegue otro aporte después. La conciliación por fecha no verifica el orden ni la disponibilidad intradía, las condiciones del préstamo o las facturas reales.

La próxima conexión es deuda y activos de apertura, seguida del calendario de equity desde la compra hasta la venta. Debe evitar contar otra vez la caja inicial como aporte. El retorno personal requiere además términos de reparto documentados. Todo continúa con datos sintéticos y decisión **PENDING**, sin despliegue ni decisiones reales.

[Evidencia reproducible del ejemplo](synthetic-preopening-cash-demo.json) · [Alcance técnico y pendientes](../technical-implementation-T57.md) · [Matriz de cobertura del bloque](../technical-coverage-T57.json).
