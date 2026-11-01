# M5 — Deuda de construcción, interés y equity requerido

Estado: contratos candidatos y referencias algebraicas sintéticas. No es underwriting de producción ni restaura una aplicación histórica. Fuentes: Master v5.1 §3 Costs and TDC / Timing; Input Sheet Inputs!C51:C53; Manual físico pp.11,13,23,32,53; Q6–Q9 y PAR-03:06. Los términos bancarios son entradas distintas de los criterios de inversión de Lorena. Full UW diferido; no se utiliza su ausencia para bloquear la especificación independiente.

## Contratos y ubicación de cada dependencia

| ID | Contrato de salida | Fuente exacta / pendiente |
|---|---|---|
| M5-01 | Base elegible de costo y capacidad del préstamo | C51 es LTC; Master §3 Timing relaciona LTC/TDC. Falta alcance de costo elegible y base contractual; no equiparar automáticamente elegible con TDC. |
| M5-02 | Compromiso, monto disponible, draws acumulados y saldo de deuda separados | Manual p.32 term sheet pendiente; ledger de caja actual. No suponer que todo préstamo comprometido se desembolsa. |
| M5-03 | Interés por período según saldo y convención documentados | C52; PAR-03/04, Manual p.53. Fecha, tasa nominal/efectiva, día-base, saldo inicial/promedio/final, floor y cambios de tasa requieren definición. No dividir siempre la tasa anual por doce. |
| M5-04 | Fee de originación: porcentaje por base y fecha explícitos | C53; Master Costs and TDC. Compromiso, saldo, draw y préstamo aprobado son bases diferentes; fee pagado, retenido o financiado necesita contrapartida. |
| M5-05 | Aplicación de capital: equity requerido y aportes reales por fecha | Master Timing equity-first; Q7/Q8 Manual p.23. No confundir requerido, comprometido, disponible y aportado. Equity-first no fija el origen de cada déficit posterior. |
| M5-06 | Conciliación por préstamo: saldo inicial + principal recibido + interés capitalizado + ajustes documentados − principal repagado | Contrato DEBT-01 y Master §3 financiación. Separar caja prestada de capitalización sin caja; no contar ambos como cobros de deuda. |
| M5-07 | Uso de NOI/caja operativa durante lease-up | Master Timing: NOI paga interés primero; Q6 abierto Manual p.23. NOI devengado no prueba cobro. Destino del excedente y déficits no se inventa. |
| M5-08 | TDC y costo financiero circular | Master Costs and TDC / Manual p.13. Cerrar fórmula, bases, perfiles, convergencia, residuales y dominio; solución algebraica reducida no certifica motor mensual. |
| M5-09 | Control de factibilidad por fecha | Contratos M4/M5 y C2. Capacidad contractual excedida, vencimiento sin financiación o faltante de caja no se cubren con draws/aportes ficticios. Clasificación queda PENDIENTE por información/reglas ausentes; no convertir en FAIL automáticamente. |
| M5-10 | Estado de salida para M6 | Master Refinance: payoff de construcción; Q13 otra deuda. Entregar saldo, interés devengado pendiente, fees, reservas restringidas, vencimiento y alcance del payoff; no asumir saldo = liquidación total. |

## Campos de financiación y madurez de evidencia

Los tres campos originales (C51 LTC, C52 tasa y C53 fee) no describen por sí solos todo el contrato temporal. Se proponen grupos adicionales sólo cuando sean necesarios para el escenario: base elegible y límite monetario, fecha de inicio/vencimiento, calendario de draws y condiciones precedentes, disponibilidad no usada, interés devengado/pagado/capitalizado, convención y evolución de tasas, base/fecha de fees, interés reservado y liberaciones, orden de caja, repago y extensiones. Deben extraerse de documentos o definirse expresamente, sin inventar términos ni exigir todo el detalle Full UW por defecto.

Un campo no aplicable requiere justificación y regla. Cero documentado no es faltante; una reserva de interés de cero no permite asumir que ningún interés será debido. La falta de una cláusula leída no acredita la inexistencia de la obligación. El modelo no interpreta garantías ni reemplaza revisión jurídica.

## Identidades de deuda, caja e interés

Sea B el saldo de principal. En cada período: `B_final=B_inicial+draw_caja+interes_capitalizado+ajustes_principal−repago_principal`.

El interés devengado se concilia entre interés pagado, capitalizado y variación del interés por pagar, con ajustes documentados. El interés capitalizado que aumenta deuda no es al mismo tiempo ingreso de caja del proyecto. Si el banco paga un gasto directamente, registrar ambas contrapartidas económicas/documentales sin simular dos aportes de financiación. Transferir a reserva restringida no es gasto financiero realizado ni distribución al inversor por sí mismo.

Si un fee se retiene del desembolso bruto, distinguir draw bruto, caja neta y pago del fee. No sumar el fee como gasto y reducir de nuevo los proceeds sin conciliación. Definir si pertenece al principal, gasto devengado, pago inmediato o reserva.

## Referencia de cierre reducido TDC/interés (M5-08)

Sólo para una rama algebraica explícita: costo antes de financiación C≥0; préstamo L=λT exactamente desembolsado bajo esa relación; fee fL; interés total kL donde k es coeficiente agregado documentado y fijo; no otras deudas, aportes operativos, reservas o flujos. Aquí k NO es una tasa anual ni una estimación de intereses de construcción. Definir q=λ(f+k). Entonces:

`T=C+qT`; si `1−q≠0`, `T=C/(1−q)` y `E=(1−λ)T`.

Para C>0 y 0≤q<1 existe solución positiva única. La iteración simple T_(n+1)=C+qT_n converge en ese dominio por contracción; el residuo T−C−qT certifica la identidad reducida, no el error de un motor general. Si q=1 y C>0 no existe solución; si q=1 y C=0 hay indeterminación (infinitas soluciones), no un TDC elegido de cero. Para q>1 y C>0 la solución algebraica es negativa e inadmisible para este dominio. Para C=0 y q≠1, T=0 es solución de la ecuación, pero no demuestra viabilidad ni permite calcular ratios con denominador cero. No fijar tolerancia ni iteraciones productivas con estos ejemplos.

En el modelo real, saldos, draws y financiación pueden depender de T por tramos, límites y calendario. No sustituirlos por un coeficiente k supuesto ni extender el argumento de contracción sin verificar el mapa real, sus ramas y el dominio.

## Cierre exigido antes de activar M5

Cada escenario requiere paquete de entradas completo, calendario vigente, versiones de fórmula/política y ledger por préstamo/caja/equity; fuentes/usos y rollforwards conciliados; ningún saldo, aporte o reserva inexplicado; fechas de vencimiento y factibilidad; tolerancias y criterios de solución aprobados; casos independientes y prueba de integración. También cierre de Q6–Q9 aplicables y decisiones de origen de capital. Todos esos cierres permanecen abiertos.

Validación actual: `references/validate_m5_algebra.py` y `m5-validation.json`. Sustitución exacta en ecuación original de cierre reducido, casos degenerados y contraste de recurrencia contra expansión de flujos con fracciones racionales. Datos abstractos sintéticos; no tasas/condiciones bancarias para un deal, no reproducción de referencias históricas ni auditoría independiente. No sumar sus controles a otros para atribuir porcentaje de producto terminado.

Siguiente contrato: M6, deuda permanente y refi; tratar por separado sizing LTV/DSCR, amortización/vencimiento, payoff, reservas y distribución/cash-in netos.

## Secuencia y factibilidad declarada

[El contrato de secuencia financiera](financing-timeline.md) añade 50 controles sintéticos de saldos por acción, disponibilidad, límites y vencimiento. Preserva datos/convenciones ausentes; no infiere un solver, financiación o extensiones. Es diagnóstico condicionado, no cierre de M5.
