# Si invierto USD 10, ¿cuánto cobro y cuándo?

D258 conecta C57 (gastos controlables), C58 (administración) y C59 (seguro) con gastos, NOI, capacidad de refi y flujos del proyecto. El ensayo utiliza respaldos sintéticos D200 y revisiones explícitas del seguro. Se mantiene la escala de USD 10 sobre USD 2.400.000 de equity inicial verificado, con aportes posteriores separados. El dictamen operativo y el retorno personal sin términos de reparto siguen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C57 | USD 4,8670 | USD 18,0422 | USD 0,0000 |
| Base, sólo C58 | USD 4,8670 | USD 18,0569 | USD 0,0000 |
| Base, sólo C59 | USD 4,8670 | USD 18,0554 | USD 0,0000 |
| Base conjunto | USD 4,8670 | USD 18,0357 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C57 | USD 8,1893 | USD 6,0594 | USD 12,1299 |
| Downside, sólo C58 | USD 8,1893 | USD 6,0753 | USD 12,1140 |
| Downside, sólo C59 | USD 8,1893 | USD 6,0708 | USD 12,1186 |
| Downside conjunto | USD 8,1893 | USD 6,0521 | USD 12,1372 |

El aporte inicial ocurre el 30/03/2027. En Base conjunto se agregan aproximadamente USD 4,655375 el 30/09/2027 y USD 0,052917 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,429122 de operación más USD 13,759945 de venta el 30/12/2028. En Downside conjunto se agregan USD 0,762275 el 30/06/2027, USD 0,035729 el 30/09/2027, USD 7,034046 el 30/12/2027 y USD 0,071458 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,547629 de operación más USD 3,058660 de venta el 30/06/2029. El expediente conserva fracciones exactas y cada fecha en `cash_per_usd_10.events`; el redondeo se aplica después de totalizar.

Estos son ensayos del motor con cambios declarados. En ambos escenarios se prueba C57 +1 % relativo, C58 +1 punto básico y C59 +1 % relativo. Se ejecuta cada uno y después los tres juntos. Los giros, intereses y aportes de obra se conservan; los gastos operativos reducen el NOI y los cobros de operación y venta. No se cargan como valores por defecto ni como criterios de inversión.

## Bases y conciliaciones

| Campo y ubicación | Definición vigente | Conexión y evidencia de validación | Estado |
|---|---|---|---|
| Inputs!C57 | Importe anual por unidad residencial controlable, incluyendo C25–C28 | D148: total = tarifa × unidades. Servicios incluidos + controlables sin servicios = total. El NOI resta cada gasto una vez | Conectado en sintético |
| Inputs!C58 | Fracción de renta residencial efectiva más otros ingresos C13; excluye renta comercial | D148: base elegible y comisión verificadas por período; se preservan pérdidas, concesiones y crecimiento de la renta | Conectado en sintético |
| Inputs!C59 | Prima anual por unidad residencial asegurada confirmada | D148/D166: prima × unidades cubiertas; cotejo exacto con respaldo de seguro y cobertura | Conectado en sintético |
| Proyección y NOI | Crecimiento de gastos según la convención vigente; impuesto según el perfil | D154 y motor NOI: gastos y NOI reconciliados en las cuatro ventanas del caso | Validado en sintético |
| Capacidad, caja y cierre | Se recalculan con los NOI bancario, de valoración y de salida propios | Cierre y movimientos por USD 10 reconciliados; los bloqueos existentes se conservan | Validado en sintético |

| Importe anual del proyecto completo, USD | Base original | Base conjunto | Downside original | Downside conjunto |
|---|---:|---:|---:|---:|
| Gastos operativos antes de impuesto | 76.702,4000 | 77.167,0048 | 87.482,8000 | 88.076,4380 |
| NOI operativo | 402.439,1000 | 401.974,4952 | 228.710,1667 | 228.215,4683 |

Las pruebas cotejan por período los controlables, servicios, seguro y administración, además de los gastos fijos del alcance. El NOI se concilia con renta efectiva, otros ingresos, comercial neto, gastos e impuesto. La variación del NOI no se supone igual a la variación del gasto: el impuesto se recalcula según la rama fiscal existente. Se conserva el tratamiento del NOI después de reservas en las métricas que lo requieren; esta conexión no redefine sus bases.

## Contrato sintético v6 y respaldo del seguro

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v6` en el perfil sintético de aceptación técnica. Se concentra en C57–C59, con uno a tres cambios únicos por escenario. Los contratos anteriores, incluido [D257](workbook-construction-sensitivities-D257.md), conservan su alcance y reproducción.

Cada cambio declara celda, operación, unidad, valor exacto y fuente sintética. Las unidades de reemplazo son `USD_per_residential_unit_per_year`, `fraction_of_effective_residential_income_plus_c13` y `USD_per_insured_unit_per_year`. Las tarifas admiten sustitución absoluta o cambio relativo; los puntos básicos y porcentuales corresponden a C58.

Cada escenario agrega `expense_support.individual` por celda y `expense_support.combined`. Cada entrada exige `source_ref`. Si el cambio incluye C59, también exige `insurance`, con `parent_sha256`, `document` y `sha256`. El padre es el respaldo de seguro del expediente original; el documento nuevo conserva las claves del padre y sólo puede modificar su fuente y la prima. La vigencia, escenario, deal, unidad, base, cobertura y cantidad de unidades aseguradas se conservan. El motor D166 vuelve a cotejar la prima con C59. Un soporte de C57 o C58 no puede introducir por sí solo otra cotización de seguro.

En el ensayo, la prima Base pasa de USD 300 a USD 303 por unidad/año; Downside pasa de USD 550 a USD 555,50. Son registros estructurados sintéticos ligados por huellas, no una lectura nueva de PDF u OCR. La evidencia conserva el padre, la revisión, su fuente y la cita del valor cambiado. Los soportes no autentican cotizaciones reales ni modifican criterios de aprobación.

El runner conserva los gastos y NOI por período, fuentes de celdas, respaldo de seguro, capacidad, cierre y cada movimiento por USD 10. La corrida conjunta vuelve a ejecutar el motor. El expediente original y su PDF integral mantienen sus resultados. El JSON v6 conserva el límite anterior de 48 KiB.

## Pruebas de faltantes, cero y reproducción

Los tres campos prueban vacíos tanto en la base como en el cambio, y unidades inválidas. El cero numérico explícito se preserva. El ensayo integrado de cero comprueba que C58 = 0 produce administración cero y C59 = 0 produce seguro cero sólo con su respaldo sintético explícito. Son controles técnicos, no supuestos de gratuidad para un deal real. C57 = 0 queda PENDING cuando los servicios incluidos tienen costo: el modelo no elimina C25–C28 para hacerlo coincidir.

Otros controles retiran el respaldo de C59 o suministran una prima contradictoria; el cálculo afectado queda PENDING y su ranking incompleto queda vacío. Se rechazan hashes o padre incorrectos y cambios silenciosos de cobertura, unidades, vigencia o escenario. Ningún vacío se interpreta como cero.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_expense_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_operating_costs_D148.py --output /tmp/miniuw-d258-d148
```

Se utilizan las dependencias de referencia y OCR del repositorio para los respaldos originales. Los paquetes y registros del VPS quedan fuera de GitHub; se preservan código, pruebas y esta descripción. Los costos y períodos ajenos al alcance declarado requieren sus propias fuentes. La validación profesional, los datos reales y el despliegue siguen pendientes.

En el VPS pasaron las tres pruebas nuevas, con seis cambios individuales y dos conjuntos válidos, además de los controles de faltantes y cero explícito. D148 pasó sus doce casos de planilla, con siete PENDING esperados. B16 reprodujo sin diferencias el expediente D257 guardado con sensibilidades v5. Son verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

[D259](workbook-reserve-sensitivities-D259.md) agrega C60 al conjunto de gastos, preservando por separado la reserva restringida, su liquidación y el fondeo adicional requerido.
