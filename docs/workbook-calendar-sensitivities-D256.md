# Si invierto USD 10, ¿cuánto cobro y cuándo?

D256 conecta cambios explícitos de C46 (meses de obra) y C47 (meses desde TCO hasta estabilización) con los desembolsos, intereses, aportes y cobros fechados. El ensayo utiliza el expediente sintético D200 y un respaldo sintético de absorción declarado para estos plazos. La escala sigue siendo USD 10 de los USD 2.400.000 de equity inicial verificados. Los aportes posteriores se muestran aparte; los criterios y el dictamen operativo permanecen PENDING.

| Escenario y ensayo | Aporte adicional por USD 10 iniciales | Cobro total | Fecha de refi | Fecha de operación y venta | Caja sin recuperar después de venta |
|---|---:|---:|---|---|---:|
| Base original: C46 = 6, C47 = 3 | USD 4,87 | USD 18,06 | 30/09/2028 | 30/12/2028 | USD 0,00 |
| Base: sólo C46 = 9 y TCO respaldado al 01/01/2028 | USD 4,89 | USD 18,06 | 30/12/2028 | 30/03/2029 | USD 0,00 |
| Base: sólo C47 = 0 explícito | USD 4,69 | USD 17,98 | 30/06/2028 | 30/09/2028 | USD 0,00 |
| Base conjunto: C46 = 9 y C47 = 0 | USD 4,72 | USD 17,98 | 30/09/2028 | 30/12/2028 | USD 0,00 |
| Downside original: C46 = 9, C47 = 6 | USD 8,19 | USD 6,08 | 30/03/2029 | 30/06/2029 | USD 12,11 |
| Downside: sólo C46 = 6 | USD 8,23 | USD 6,08 | 30/03/2029 | 30/06/2029 | USD 12,15 |
| Downside: sólo C47 = 9 | USD 8,51 | USD 6,12 | 30/06/2029 | 30/09/2029 | USD 12,39 |
| Downside conjunto: C46 = 6 y C47 = 9 | USD 8,55 | USD 6,12 | 30/06/2029 | 30/09/2029 | USD 12,43 |

El aporte inicial de USD 10 ocurre el 30/03/2027 en todos los casos. En Base conjunto se agregan USD 4,556833 el 30/12/2027 y USD 0,052917 por trimestre del 30/03/2028 al 30/09/2028. Se cobran USD 2,846667 en refi y USD 1,355177 de operación más USD 13,781629 de venta en las fechas de la tabla. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 7,284046 el 30/09/2027 y USD 0,071458 por trimestre del 30/12/2027 al 30/06/2029. Se cobran USD 2,445833 de refi y USD 0,590198 de operación más USD 3,081180 de venta. Los importes exactos y cada fecha se conservan en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

Son pruebas de conexiones con valores declarados. C47 = 0 es un supuesto sintético de estabilización inmediata y no una regla por defecto. El retorno personal requiere términos de reparto propios; la caja sin recuperar al cierre es una medida del horizonte del caso.

El respaldo sintético de absorción del ensayo declara un rango de cero a doce meses con fuente y huella propias. El runner no amplía los rangos recibidos para acomodar una variante.

## C46–C47, intereses y calendario

| Ensayo | Intereses de obra del proyecto en Base, USD | Intereses de obra del proyecto en Downside, USD |
|---|---:|---:|
| Original | 57.150 | 102.900 |
| Sólo C46 | 63.500 | 111.475 |
| Sólo C47 | 44.450 | 120.050 |
| Conjunto | 50.800 | 128.625 |

Los intereses de esta tabla son importes del proyecto completo. Se cotejan por período como saldo inicial más draw al inicio, multiplicado por la fracción trimestral documentada. Mover un desembolso puede aumentar intereses aun cuando la obra termina antes. Mover la estabilización cambia los períodos hasta refinanciar, el déficit reservado de lease-up, las ventanas de NOI y las fechas de los cobros. El runner ejecuta cada caso y su conjunto con el motor existente.

| Requisito y ubicación | Definición vigente | Módulo afectado | Evidencia de validación | Estado |
|---|---|---|---|---|
| Inputs!C46 | Meses de obra en la grilla trimestral; mínimo tres; TCO independiente y posterior al fin de obra | D145 → D144 → D146 | Fecha de terminación, pagos, draws, principal e interés por período | Conectado en sintético |
| Inputs!C47 | Meses de TCO a estabilización; cero explícito permitido con respaldo; horizonte compatible | D145 → D154 → D146 y renta/NOI | Estabilización, fondo de lease-up, refi, venta y caja fechada | Conectado en sintético |
| TCO, venta y ventana fiscal | Sólo cambian mediante registros sintéticos explícitos con fuente; se comprueban contra el calendario | Soportes D256, alcance D174 y revisión D173 | Falta de fecha de venta o de ventana fiscal deja PENDING el cálculo afectado | Validado en el perfil de prueba |
| Deuda permanente | Ocho pagos desde la originación, según el PDF bancario del ensayo | D152 y B08 | El plazo se conserva; la fecha absoluta se deriva de la nueva originación. Alterar el plazo sin otro respaldo queda PENDING | Validado en sintético |
| Deuda de obra | Vencimiento absoluto de la cotización, compromiso y disponibilidad por draw conservados | D146 y productor de deuda | Refi posterior al vencimiento produce `schedule_past_maturity_no_extension_inferred` | Validado en sintético |
| Base de USD 10 | Mismo aporte inicial y fecha de compra, aportes/cobros brutos por fecha | Runner D253/D256 | Conciliación exacta con totales, refi y saldo sin recuperar | Validado en sintético |

La obra Base de nueve meses exige un TCO nuevo al 01/01/2028, aportado explícitamente en el ensayo. Al combinarla con C47 = 0, la fecha de venta vuelve a la del original. En Downside se conserva el TCO original y los efectos de C46 y C47 se acumulan. No se mueve el TCO sólo porque cambió C46.

## Entrada y soportes de cada variante

El esquema optativo `miniuw.synthetic-worksheet-sensitivities.v4` se declara en `rent_inputs.sensitivities` del perfil de aceptación técnica. Este contrato se concentra en C46–C47; los contratos anteriores de [D255](workbook-budget-sensitivities-D255.md) conservan su alcance y reproducción.

Cada escenario contiene `changes` y `calendar_support`. Cada cambio declara celda, operación `month_change` o `replace_absolute`, unidad `months`, valor entero explícito y fuente sintética. El resultado debe satisfacer los límites y la grilla trimestral vigentes.

`calendar_support` exige `individual` con una entrada por celda y `combined` para el conjunto. Cada entrada exige `source_ref` y admite sólo TCO, fecha de venta, número de pagos al vencimiento permanente y respaldo fiscal del comprador para la ventana exacta. Los campos ausentes conservan sus respaldos originales; si resultan incompatibles, el motor bloquea el cálculo. El TCO del conjunto debe conservar el respaldo independiente utilizado en los casos individuales. Las fechas derivadas de venta y sus ventanas deben corresponder al calendario conjunto, que puede diferir de cada caso aislado.

El runner conserva la cita de cada cambio, las fechas originales y nuevas, los soportes y sus huellas, presupuesto, financiación por fecha, términos bancarios, capacidad, NOI y caja. La validación bancaria vuelve a cotejar los términos con el PDF original; el soporte estructurado no reemplaza una cotización contradictoria. La revisión del expediente enlaza la solicitud completa. La comparación de deltas de caja es nominal y no decide qué calendario conviene por valor presente.

## Bloqueos y reproducción

Las pruebas verifican vacíos de C46/C47 tanto en la base como en el cambio, unidades inválidas y fracciones de mes. Ningún vacío se convierte en cero. El ensayo válido conserva C47 = 0 como valor explícito. Los controles integrados retiran la fecha de venta de Downside y el respaldo fiscal de Base: ambos cálculos afectados quedan PENDING. Otro control altera a siete pagos el plazo de ocho del PDF y queda PENDING por discrepancia bancaria. Un plazo de lease-up Downside de doce meses lleva la refi después del vencimiento absoluto de obra: tanto el cambio individual como el conjunto quedan PENDING, sin inferir prórroga.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_calendar_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_project_calendar_D145.py --output /tmp/miniuw-d256-d145
```

Se utilizan las dependencias de referencia y OCR del repositorio. La aceptación ensambla desde los respaldos sintéticos y reproduce el expediente vigente con B16. Los artefactos generados y registros del VPS quedan locales. GitHub conserva el código, las pruebas y esta descripción; el PDF de decisión original mantiene su alcance.

En el VPS pasaron las tres pruebas nuevas: cuatro cambios individuales y dos conjuntos válidos, más los controles de faltantes y deuda. D145 pasó sus trece casos de planilla, con diez PENDING esperados. B16 reprodujo sin diferencias el expediente D255 de sensibilidades v3 guardado. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

Se conservan las convenciones del perfil de financiación trimestral y el déficit mensual de lease-up declarado. Otros costos de tiempo, seguros de obra o gastos generales requieren su propio alcance y respaldo antes de recalcularse; no se agregan coeficientes. Los plazos del ensayo no se adoptan como escenarios automáticos, y la validación profesional y el uso real siguen pendientes.

[D257](workbook-construction-sensitivities-D257.md) conecta C51–C53 con desembolsos, intereses, comisiones y caja mediante cotizaciones PDF sintéticas ligadas al respaldo original. Conserva la reproducción de v4.
