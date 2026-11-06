# Conciliaciones de deuda caja reservas venta y retorno del Mini-UW

El modelo debe conservar el origen y destino del dinero entre compra, obra, operación y venta. Una diferencia puede indicar una partida duplicada, un saldo perdido o una financiación sin fuente. Este bloque reúne 12 contratos de conciliación y contrasta 24 igualdades con las fuentes del ejemplo sintético T111 ya guardado.

Las 24 igualdades cuadran con fracciones exactas. Esa comprobación acredita consistencia aritmética dentro de las hipótesis suministradas; no autentica pagos bancarios, completa la hoja de Lorena ni aprueba una definición financiera. El deal conserva PENDING, con capital, CoC y retorno personal pendientes. El código, los datos de entrada y los resultados T111 permanecen intactos.

## Qué debe conciliarse

La [matriz de 12 contratos](MiniUW_Contratos_Conciliacion_D13.csv) identifica la relación condicionada, los registros necesarios y el bloqueo por faltante o conflicto. El [registro completo](MiniUW_Conciliaciones_D13.json) enlaza cada contrato con sus definiciones I01 y los traspasos de [D12](MiniUW_Dependencias_y_Traspasos_D12.md).

| Contrato | Conciliación requerida |
| --- | --- |
| Compra y obra | Caja inicial más fuentes menos usos frente a caja final; principal inicial más draws menos repagos, con ajustes/capitalización documentados cuando correspondan. |
| Paso a operación | Misma identidad de préstamo y saldos compatibles entre cierre y apertura; cualquier cambio necesita su fuente. Un cambio de fase no crea financiación. |
| Caja libre | Cobros, pagos, deuda, aportes, distribuciones y transferencias restringidas frente al saldo de cierre por período. NOI devengado conserva su alcance distinto de efectivo. |
| Reservas | Saldo inicial, depósitos, liberaciones y ajustes frente al saldo restringido final. Una transferencia interna no crea gasto o distribución por sí sola. |
| Devengo y pago | Gastos y partidas no monetarias conciliados con payables, prepaid y pagos, bajo la clasificación documentada. Los demás ajustes deben estar expresos. |
| Deuda al cierre | Principal remanente y corte de pagos frente a lo debido/pagado; intereses, fees y otras obligaciones conservan sus partidas. |
| Seguro al corte | Inventario nominal, pagos y saldos contables por separado. Un pago ya incluido en los usos de venta se descuenta una vez. |
| Paso a venta | Caja libre y restringida que sale de operación frente a la apertura del cierre, con movimientos intermedios si corresponden. |
| Venta neta | Proceeds y otras fuentes menos costos, payoffs, retenciones y usos frente al residual; reserva final conciliada aparte. |
| Ciclo completo | Fuentes externas frente a usos externos y saldos finales. Depósitos/liberaciones internos se cancelan en la caja total, conservando sus cuentas. |
| Retorno agregado | Aportes y cobros brutos, neto de caja y equity multiple dentro de la ventana. Deuda recibida y repago al banco conservan su clasificación. |
| Caja anual | Movimientos por sus fechas dentro de cada año; stock de capital, CoC y reparto personal requieren evidencia propia. |

Un residual no se corrige creando un aporte, draw o ajuste sin fuente. Los datos originales y la discrepancia deben conservarse. Una fuente ausente permanece ausente; cero explícito conserva su identidad. La precisión o tolerancia de una futura regla necesita definición, en lugar de fijarse para hacer cuadrar el resultado.

## Reconstrucción del ejemplo sintético

La [evidencia aritmética](MiniUW_Conciliacion_Sintetica_D13.json) conserva expresiones, fuentes con hash y punteros, valores comparados y residual de cada igualdad. La [tabla de 24 comprobaciones](MiniUW_Comprobaciones_24_D13.csv) permite revisar los resultados. La reconstrucción usa sólo `Fraction` de Python y lectura de JSON: no importa ni llama a los productores financieros del modelo.

Todos los importes de esta sección son **USD ficticios del mismo ejemplo existente**. Sus principales puentes son:

| Etapa | Relación observada |
| --- | --- |
| Compra y obra | Aportes de 1.400 y draws de 250, menos costos de 1.000, fees/interés de 10 y repagos de 50, dejan caja de 590. El principal termina en 200. |
| Operación | Caja inicial de 590 más cobros de 88, menos pagos de 25, capex de 40, principal de 100, distribuciones de 200 y depósitos restringidos de 100, deja caja libre de 213 y reserva de 100. |
| Venta | Caja libre de 213, precio bruto de 400 y liberación de reserva de 100, menos principal/fees de 110, costos de 20 y otros usos de 5, dejan distribución de 578. Los saldos finales declarados son cero. |
| Equity del proyecto | Aportes brutos de 1.400 y cobros de 778 —200 operativos más 578 de venta— producen neto de caja de −622 y múltiplo exacto de 389/700. |

El neto negativo es una diferencia de caja del ejemplo dentro de su ventana. No se etiqueta automáticamente como pérdida económica final ni como retorno de una persona. La normalización y la TIR existentes no se recalculan en este bloque, y no se selecciona una tasa puntual.

La fuente de obra contiene 12 casillas de eventos de deuda cuyo monto está vacío porque deben vincularse al calendario del préstamo. Se verificó el mapa explícito de período, préstamo, categoría, ID y fecha antes de reconstruir sus importes en memoria. Los vacíos originales se conservaron; no se rellenaron con cero ni se escribieron importes sobre las fuentes.

El interés de obra utiliza factores por intervalo suministrados. La fase operativa de este ejemplo declara tasa efectiva cero, cuotas/amortización, fechas y ausencia de nuevos draws. La reconstrucción usa esas condiciones y el corte declarado anterior al pago regular de venta; no convierte tasas anuales ni instala esa estructura para otro deal.

En los dos períodos operativos se conservan gastos devengados, pagos y saldos. El seguro deja un payable de 5 antes de venta; un pago de 5 al corte ya está incluido en `other_cash_uses` del cierre. Su conciliación con los saldos suministrados no demuestra que un vencimiento nominal sea pago ni que el banco lo haya ejecutado.

## Qué demuestra y qué queda pendiente

Las igualdades verifican principal y caja de obra; continuidad a operación; dos cierres de caja libre y restringida; dos puentes entre gasto y pago; principal antes de venta; seguro y su uso único; apertura de venta; residual y reserva final; fuentes/usos externos; aportes, cobros, neto y múltiplo; y caja neta de cada uno de los dos años.

El residual cero no demuestra que el inventario esté completo o sea auténtico. Una conciliación por período tampoco acredita liquidez intradía ni el orden contractual de fondos. La hipótesis de apertura cero, las declaraciones de continuidad y el perfil de interés/corte pertenecen a este ejemplo. La aplicación a otro caso necesita sus fuentes, definiciones y conciliaciones correspondientes.

Las 20 conexiones, los 55 campos y las 23 revisiones de salida de [D11](MiniUW_Activacion_y_Aceptacion_D11.md) siguen separados de esta comprobación. Los 54 mapeos semánticos pendientes, las bases de capital/CoC, los términos personales, los criterios y la aceptación financiera conservan sus puertas abiertas. Cuadrar caja no convierte un límite bancario en criterio de inversión ni una banda en FAIL.

La [verificación documental](D13-design-validation.json) reproduce las expresiones desde sus referencias, comprueba las fuentes y conserva los archivos anteriores. Este hito añade documentación y evidencia aritmética interna, sin nuevo código de producto ni nuevas pruebas de software. Se mantiene T111 con datos sintéticos, sin despliegue, decisiones reales o nuevo PDF externo. La ampliación a Full UW permanece diferida.
