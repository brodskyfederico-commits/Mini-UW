# M3/M4 — Presupuesto y calendario: contratos de diseño

Estado: propuesta trazable; no implementación productiva. Fuentes: Master v5.1 §3 Costs and TDC / Timing; Input Sheet Inputs!C32:C42, C46:C47; Manual v2.2 páginas físicas 10, 13, 22–23 y 58–61. No se completa con datos de mercado ni se necesita recibir el Full UW para desarrollar este bloque.

## M3: alcance y costos antes de financiación

| ID | Contrato candidato | Evidencia / pendientes |
|---|---|---|
| M3-01 | Normalizar hard vertical según base: GSF×precio/GSF, unidades×precio/unidad o total explícito | C34/C35 y programa. Tres bases alternativas, no sumables. No sustituir GSF por NRSF. |
| M3-02 | Registro de inclusiones: cada alcance económico tiene ID, fuente, monto/base, categoría, incluido/excluido/no determinado y vínculo a contrato | Manual p.58 exige definición C35; R1–R4 pp.59. Parking, site, fee, seguros, GC/general conditions y contingencia pueden venir dentro del precio. No sumarlos de nuevo. |
| M3-03 | Contingencias: separar dueño/contratista/escalamiento, base de aplicación, inclusión en precio, control y uso | C39; GC pp.56/58/59. Un porcentaje sin base no determina monto. Una contingencia es presupuesto, no gasto desembolsado automáticamente. |
| M3-04 | Soft y TI/LC: porcentaje por base hard aprobada más TI/LC comercial si corresponde | C40/C41. Definir si base incluye contingencia, parking/site y fees. Un monto GC excluido debe tener cobertura documentada; no se inventa precio. |
| M3-05 | Compra evaluada más gastos de cierre explícitos | C32/C33. Asking y precio evaluado son variables separadas. Precio ausente no se convierte en cero; precio de búsqueda M8 no es dato aportado. |
| M3-06 | Presupuesto antes de financiación = suma de alcances exclusivos, incluyendo ajustes documentados | M3-01:M3-05. Mantener presupuesto, devengo, pago y saldo pendiente separados. TDC all-in requiere financiación M5; no cerrarlo antes. |

La expresión histórica hard=(vertical+parking+site)×(1+contingencia) sólo es candidata cuando las partidas son disjuntas y la contingencia aplica a esa base. No certifica que un precio GC total corresponda al vertical C35. Si no se puede separar una inclusión, detener el resultado afectado y conservar ambos montos.

Cada alcance debe reconciliarse con sus representaciones: una factura, partida de presupuesto y cuota de un contrato pueden representar el mismo costo. Identidad documental no es independencia económica. Permitir descomposición sólo con reparto documentado y suma que concilie; no eliminar automáticamente duplicados por igualdad de montos. Créditos, reembolsos y cambios de alcance requieren eventos y signos documentados.

## M4: devengo, desembolso e hitos

| ID | Contrato candidato | Evidencia / pendientes |
|---|---|---|
| M4-01 | Hitos con fechas/índices separados: compra, inicio obra, TCO, fin obra, estabilización, refi y venta | C46/C47; PAR-04. No asumir equivalencia TCO/estabilización ni adoptar obra+lease-up+1 como fecha aprobada. |
| M4-02 | Pesos explícitos por partida y período w_jt: pago asignado B_j×w_jt | Para presupuesto totalmente programado, Σw_jt=1 y pesos no negativos; no normalizar una curva incompleta silenciosamente. Para programación parcial se conserva saldo sin asignar y bloqueo de financiación. |
| M4-03 | Perfil histórico sin² y soft upfront meses 1–3 | C42; Master Timing. Pendientes discretización, fase, denominador, pesos primeros meses, obra menor a tres meses y calendario de pagos; no elegir una curva por conveniencia. |
| M4-04 | Devengo y caja separados; cuentas por pagar y anticipos conciliados | Un costo incurrido no es necesariamente draw del banco ni aporte de equity; M5 financia eventos de caja bajo reglas propias. Retainage, anticipos y liberaciones necesitan condiciones explícitas. |
| M4-05 | Escenario de retraso modifica fechas, curva y costos sólo mediante políticas explícitas | Q4/Q5, Manual pp.22–23; política 23. Repartir costo fijo en más meses no crea por sí solo costo adicional; costos mensuales requieren importe y período. No inventar shocks. |
| M4-06 | Puente hacia M5: usos por período y saldo no programado, fuentes y versiones | Si Σ pagos≠presupuesto, la diferencia se explica (reserva/saldo/alcance/ajuste) o bloquea C2. No forzar caja final a cero. Cambios de calendario invalidan interés/deuda/retornos aunque total de costo no cambie. |

Si se proponen pesos integrados a partir de una función de densidad, la elección de función y muestreo es una convención nueva a aprobar; la palabra sin² no define por sí sola el algoritmo. Validar suma y signo no valida la forma de una curva ni su adecuación de construcción.

## Escalamiento y circularidad

La polinómica contractual exige P0, coeficientes, índices y fechas base, partidas afectadas, tope/banda y período. Se conserva la fórmula literal. No aplicar ajuste al costo completo si el contrato sólo afecta materiales específicos; evitar duplicación con contingencia de escalamiento. Sin índice/coeficiente/alcance no hay ajuste calculable.

M3 entrega costos sin financiación; M4 ubica los usos; M5 calcula deuda/intereses/fees y su efecto en TDC. La dependencia TDC→equity/deuda→interés→TDC necesita solución y tolerancias aprobadas, no una cifra de financiación presunta. Ni un calendario conservativo ni un presupuesto conciliado prueban convergencia de M5.

## Validación y casos por cerrar

Referencia aislada: `references/validate_m34_allocation.py` y `m34-validation.json`. Comprueba conservación de asignaciones y equivalencia de bases con fracciones exactas; casos negativos rechazan datos incompletos y pesos inválidos. No valida una curva sin² concreta, fechas bancarias, inclusiones reales ni costos del proyecto. No es auditoría independiente ni prueba de producto.

Casos pendientes de fuentes/política: GC que incluye parking/site/contingencia; contingencia sobre base incorrecta; exclusión sin precio; plazo menor que ventana upfront; devengo y pago en períodos diferentes; retraso sin cambio de costo fijo frente a gasto temporal adicional; índices faltantes o ajustes topados; deuda con fechas distintas y payoff. No se marca el módulo cerrado por tener estas descripciones.
