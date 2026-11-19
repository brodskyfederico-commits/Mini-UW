# Si invierto USD 10, ¿cuánto cobro y cuándo?

D255 conecta las sensibilidades explícitas del presupuesto C37–C42 con la deuda de obra, sus intereses, el cierre de refinanciación y la caja fechada por USD 10 de equity inicial. Usa los respaldos sintéticos de aceptación D200. El dictamen operativo y los retornos reales permanecen PENDING; los términos de reparto personales requieren su propia evidencia.

| Escenario sintético | Aporte inicial | Aportes adicionales | Cobro de refi | Cobro operativo | Cobro neto de venta | Cobro total | Caja sin recuperar |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base original | USD 10,00 | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,78 | USD 18,06 | USD 0,00 |
| Base con siete cambios conjuntos | USD 10,00 | USD 4,90 | USD 2,84 | USD 1,43 | USD 13,77 | USD 18,05 | USD 0,00 |
| Downside original | USD 10,00 | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,08 | USD 6,08 | USD 12,11 |
| Downside con siete cambios conjuntos | USD 10,00 | USD 6,92 | USD 2,44 | USD 0,55 | USD 3,08 | USD 6,07 | USD 10,85 |

El aporte inicial es el 30/03/2027. En Base conjunto se aportan aproximadamente USD 4,69 el 30/09/2027 y USD 0,05 por trimestre entre el 30/12/2027 y el 30/09/2028. La refi se cobra el 30/09/2028 y la operación y venta el 30/12/2028. En Downside conjunto se aportan aproximadamente USD 6,56 el 30/12/2027 y USD 0,07 por trimestre entre el 30/03/2028 y el 30/03/2029. La refi se cobra el 30/03/2029 y la operación y venta el 30/06/2029. Los totales se calculan con fracciones exactas antes de redondear; el expediente conserva cada fecha e importe en `cash_per_usd_10.events`.

Los importes corresponden a ensayos del motor. La eliminación explícita de contingencia y de pagos anticipados en Downside prueba el comportamiento del cero y sus interacciones; no es una recomendación financiera ni una nueva política de Downside.

## Conexiones implementadas

La entrada optativa `rent_inputs.sensitivities` agrega el esquema `miniuw.synthetic-worksheet-sensitivities.v3`. Conserva los contratos v1 y v2 de [D253](workbook-sensitivities-D253.md) y [D254](workbook-operating-sensitivities-D254.md). Admite hasta veinte celdas distintas por escenario: las catorce existentes y las seis siguientes. Cada cambio exige celda, operación, unidad, valor numérico explícito y fuente sintética. Las celdas originales conservan valor, unidad, fuente y revisión.

| Celda y requisito | Definición vigente en el perfil sintético | Unidad de reemplazo | Módulo y evidencia de validación | Estado |
|---|---|---|---|---|
| Inputs!C37, estacionamiento | Tarifa × espacios acreditados; integra obra directa elegible | `USD_per_parking_space` | D144 → D146; presupuesto, compromiso, draws e intereses cotejados | Conectado en sintético |
| Inputs!C38, trabajos de sitio | Importe total separado de obra vertical y estacionamiento | `USD_total` | D144 → D146; fuentes y usos por fecha | Conectado en sintético |
| Inputs!C39, contingencia | Fracción de obra directa vertical + estacionamiento + sitio | `fraction` | D144; reserva financiada separada del costo elegible para draws | Conectado en sintético |
| Inputs!C40, costos indirectos | Fracción del presupuesto de obra con contingencia; incluye developer fee según el alcance declarado | `fraction` | D144; TDC y aportes recalculados | Conectado en sintético |
| Inputs!C41, TI/LC | Tarifa × superficie comercial acreditada; N/A requiere declaración y queda protegido | `USD_per_rentable_sf` | D141 → D144; fuente de superficie conservada, TDC y caja cotejados | Conectado en sintético |
| Inputs!C42, pago anticipado de indirectos | Fracción de indirectos pagada en la fecha inicial de obra; resto al terminar | `fraction` | D144 → D146; pagos, caja libre y aportes por fecha | Conectado en sintético |

Las fórmulas se mantienen en [presupuesto D144](../tools/worksheet_construction_budget_D144.py) y [financiación D146](../tools/worksheet_construction_financing_D146.py). La ampliación conecta esos productores con el runner de sensibilidades y sus pruebas; conserva las bases, frecuencias y restricciones declaradas. Las tarifas admiten reemplazo absoluto o cambio relativo; los puntos básicos y porcentuales corresponden sólo a fracciones.

Cada variante conserva el presupuesto completo, costos de desarrollo, calendario, detalle de financiación, cierre de refi, NOI por período, capacidad y movimientos por USD 10. La cita de cada celda modificada enlaza al cambio exacto. La combinación ejecuta otra corrida y recoge las interacciones; no suma impactos aislados. El expediente original y su PDF integral conservan sus resultados.

## Casos de prueba y conciliaciones

En ambos escenarios se declaran aumentos relativos del 1 % en C37, C38 y C41, un aumento de 10 pb en C40 y una reducción relativa del 0,1 % en la renta C9. Base añade 10 pb a C39 y un punto porcentual a C42. Downside reemplaza C39 y C42 por cero explícito. Cada cambio se ejecuta solo y después junto con los otros seis. Estos valores sólo identifican el ensayo y no se cargan como valores por defecto.

El presupuesto Base pasa de USD 4.100.700,00 a USD 4.108.927,842 y los intereses de obra de USD 57.150,00 a USD 57.195,00. Downside pasa de USD 4.809.792,00 a USD 4.505.823,64 y los intereses de USD 102.900,00 a USD 102.991,50. El presupuesto baja al eliminar la contingencia, mientras los costos directos elegibles crecen y aumentan los draws e intereses. Son conexiones diferentes, que se cotejan separadamente.

La prueba verifica presupuesto por componentes, compromiso igual al menor límite contractual/LTC, principal por período, interés del perfil trimestral, fuentes y usos por fecha, repago de obra en refi y cierre de refi. También concilia los aportes y cobros exactos con sus totales y el saldo de caja sin recuperar. Los cambios de presupuesto aislados preservan el NOI; la combinación con C9 recalcula el NOI y la caja posterior.

En C42, cambiar cuándo se pagan los indirectos conserva el costo total y los cobros. En Base el pago anticipado adicional usa la caja inicial disponible y no genera otro llamado de capital. En Downside el cero explícito difiere aportes hasta el cierre de obra. Se cotejan las dos conductas con sus pagos y saldos por fecha.

Los seis campos prueban valores vacíos, ausencia de valor o fuente, unidades incompatibles y N/A. Ningún vacío se convierte en cero. Otro ensayo declara C37 en USD 1.000.000 por espacio para superar el compromiso documentado: la financiación y la caja afectadas quedan PENDING, con los bloqueos y el detalle de deuda visibles; C40 se calcula por separado y la combinación queda fuera del ranking.

## Reproducción y alcance restante

Con las dependencias de referencia y OCR instaladas:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_budget_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_construction_budget_D144.py --output /tmp/miniuw-d255-d144
```

La prueba integrada parte de los respaldos sintéticos, ensambla el expediente y lo reproduce con B16. Los registros y artefactos del VPS quedan fuera de GitHub; el repositorio conserva código, ensayos sintéticos y esta descripción.

En el VPS pasaron las tres pruebas nuevas, con catorce corridas individuales y dos conjuntas en el ensayo válido, más el ensayo con compromiso excedido. El verificador D144 pasó sus diecisiete casos de planilla, incluidos nueve PENDING esperados. B16 reprodujo sin diferencias los expedientes guardados con sensibilidades v1 y v2. Se ejecutaron verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.

La matriz histórica [D252](worksheet-policy-implementation-audit-D252.md) conserva sus pendientes de escenarios: aún faltan otros drivers, la derivación aprobada de Downside, sus excepciones y el Upside. El precio vertical de C35 sigue ligado a su cotización y no se sustituye mediante este contrato. Los plazos, las condiciones bancarias y las reglas fiscales conservan sus respaldos y controles. Este hito no adopta nuevas reglas del Automation Spec ni habilita datos reales o despliegue.

[D256](workbook-calendar-sensitivities-D256.md) conecta C46–C47 con intereses y caja mediante un contrato sintético separado de calendario, con soportes explícitos para cada variante. Conserva la reproducción de v3.
