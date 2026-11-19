# Si invierto USD 10, ¿cuánto cobro y cuándo?

D254 amplía las sensibilidades explícitas del modelo usando el expediente sintético D200. Cada variante recalcula ingresos, NOI, capacidad bancaria y caja fechada por USD 10 de equity inicial verificado. La inversión personal requiere sus propios términos de reparto. El dictamen operativo permanece PENDING.

| Escenario sintético | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar después de venta |
|---|---:|---:|---:|---:|
| Base original | USD 10,00 | USD 4,87 | USD 18,06 | USD 0,00 |
| Base con once cambios operativos simultáneos | USD 10,00 | USD 4,87 | USD 17,79 | USD 0,00 |
| Downside original | USD 10,00 | USD 8,19 | USD 6,08 | USD 12,11 |
| Downside con renta fuera de evidencia y crecimiento de gastos que supera capacidad | USD 10,00 de referencia | PENDING | PENDING | PENDING |

La entrada inicial es el 30/03/2027. En Base, los aportes adicionales ocurren entre el 30/09/2027 y el 30/09/2028; la refinanciación se cobra el 30/09/2028 y los cobros operativos y de venta el 30/12/2028. En Downside original, los aportes adicionales ocurren entre el 30/06/2027 y el 30/03/2029; la refi se cobra el 30/03/2029 y la operación y venta el 30/06/2029. Cada importe y fecha se conservan sin redondear en `cash_per_usd_10.events`. Los importes de esta tabla se redondean después de sumar.

## Alcance y contrato

La entrada optativa `rent_inputs.sensitivities` admite el esquema `miniuw.synthetic-worksheet-sensitivities.v2` dentro del perfil sintético de aceptación técnica. Conserva la estructura de [D253](workbook-sensitivities-D253.md): inventario explícito Base/Downside, celdas únicas y cada cambio con operación, unidad, valor y fuente sintética. El máximo es catorce celdas distintas por escenario.

| Entrada | Unidad de reemplazo | Conexión comprobada |
|---|---|---|
| C8–C11, renta residencial por tipología | `USD_per_unit_per_month` o `USD_per_rentable_sf_per_month`, según C7 | Renta potencial y efectiva, NOI, refi, venta y caja |
| C14, pérdida residencial; C15, concesiones | `fraction` | Descuentos de renta separados, NOI y caja |
| C16–C18, renta comercial | `USD_per_rentable_sf_per_year` | Superficie y vigencia comercial ya documentadas, ingreso reconocido y NOI |
| C19, vacancia comercial | `fraction` | Pérdida comercial, ingreso neto y NOI |
| C76, crecimiento de gastos | `annual_effective_growth_fraction` | Proyección de gastos bajo la convención vigente, NOI y capacidad |
| C67, C68 y C75 | Unidades originales de D253 | Cap de venta, costo de venta y crecimiento de rentas |

La sustitución absoluta y el cambio relativo admiten rentas y fracciones. Los cambios en puntos básicos o porcentuales se admiten sólo en las fracciones. La base de renta residencial debe estar confirmada por C7. Un componente comercial declarado N/A no se convierte en un ingreso mediante una sensibilidad.

C14 conserva su composición documentada. El cambio no inventa el desglose de pérdidas necesario para calcular un equilibrio físico cuando ese desglose falta.

Cada observación v2 conserva los valores originales y propuestos, su fuente, los NOI por período, las fuentes por celda, los términos comerciales y de crecimiento, la capacidad y cada aporte y cobro por USD 10. La corrida conjunta vuelve a ejecutar el motor: el resultado incluye las interacciones entre cambios. La caja y el dictamen del expediente original se preservan. La sensibilidad se registra en `results.json`; no reemplaza el PDF integral vigente.

## Ensayos y bloqueos

En Base, el ensayo declara una reducción relativa del 1 % en C8–C11 y C16–C18 y un aumento de 1 pb en C14, C15, C19 y C76. Son once cambios de prueba explícitos. Se cotejan individualmente y en conjunto; cada uno reduce el NOI de salida y afecta la caja. La combinación produce un resultado distinto de sumar los once impactos aislados.

En Downside, C8 se reemplaza por cero mediante un cambio relativo de −100 %: el cero es explícito y el control de mercado bloquea el resultado por estar fuera del respaldo. Por separado, C76 se reemplaza por 50 % anual y se bloquea la refi porque el principal solicitado supera la capacidad. Son ensayos de bloqueo, sin adopción como escenario financiero del modelo. La combinación y el ranking quedan PENDING.

Los once nuevos campos prueban valor vacío, texto vacío y espacios tanto en el cambio como en la base. Ninguno se convierte en cero. El cero numérico explícito se conserva en el enlace y después debe satisfacer los controles financieros y de evidencia. La falta de vigencia o de fuente sigue bloqueando el cálculo afectado y la entrega correspondiente.

## Reproducción

Con las dependencias de referencia y OCR instaladas:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_operating_sensitivities test_worksheet_sensitivities
PYTHONPATH=src:tools python3 tools/check_worksheet_blanks_and_zero_D171.py
PYTHONPATH=src:tools python3 tools/check_worksheet_alternatives_D155.py --output /tmp/miniuw-d254-d155
```

La prueba integrada ensambla desde los respaldos sintéticos, coteja los movimientos y la interacción, y reproduce la revisión vigente mediante B16. La regresión D253 comprueba sus controles anteriores. La evidencia del VPS y los expedientes generados se guardan fuera de GitHub; el repositorio conserva código, pruebas y esta descripción reproducible.

En el VPS pasaron las tres pruebas nuevas y el ensayo de regresión D253. D171 verificó 440 vacíos con valor nulo (436 PENDING y cuatro N/A declarados), 98 ceros numéricos conservados y doce ceros rechazados en campos no numéricos, más sus casos integrados. D155 verificó cuatro planillas, cinco alternativas calculadas y una bloqueada por capacidad. B16 reprodujo sin diferencias el expediente D200 ya guardado y un expediente de sensibilidades v1 generado con el código original D253. La batería general completa de D253 es el antecedente; este hito ejecuta las verificaciones dirigidas descritas.

Las políticas de escenarios de [D252](worksheet-policy-implementation-audit-D252.md) continúan parcialmente implementadas: aún quedan otros drivers, la derivación aprobada de Downside, las excepciones y el Upside. Esta ampliación técnica requiere cambios declarados y conserva los criterios vigentes. Las políticas financieras pendientes y las recomendaciones del Automation Spec no se activan mediante este hito. Los dictámenes reales y retornos históricos permanecen PENDING.

[D255](workbook-budget-sensitivities-D255.md) agrega el presupuesto C37–C42 y su conexión con deuda y caja mediante el esquema optativo v3. Conserva los resultados y contratos anteriores.
