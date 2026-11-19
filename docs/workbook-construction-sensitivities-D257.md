# Si invierto USD 10, ¿cuánto cobro y cuándo?

D257 conecta C51 (LTC de obra), C52 (tasa nominal anual) y C53 (comisión sobre el compromiso) con los desembolsos, intereses, repago en refi y caja del proyecto por USD 10 de equity inicial verificado. Cada variante cuenta con una cotización PDF sintética ligada al respaldo original. El aporte inicial sigue siendo el 30/03/2027 y la escala es 10/2.400.000. Los aportes adicionales se muestran aparte. El dictamen operativo y el retorno personal sin términos de reparto permanecen PENDING.

| Escenario y variante | Aporte adicional por USD 10 iniciales | Cobro total por USD 10 | Caja sin recuperar después de venta |
|---|---:|---:|---:|
| Base original | USD 4,8670 | USD 18,0594 | USD 0,0000 |
| Base, sólo C51 | USD 4,8702 | USD 18,0594 | USD 0,0000 |
| Base, sólo C52 | USD 4,8968 | USD 18,0594 | USD 0,0000 |
| Base, sólo C53 | USD 4,8035 | USD 18,0594 | USD 0,0000 |
| Base conjunto | USD 4,8333 | USD 18,0594 | USD 0,0000 |
| Downside original | USD 8,1893 | USD 6,0767 | USD 12,1126 |
| Downside, sólo C51 | USD 8,1798 | USD 6,0767 | USD 12,1031 |
| Downside, sólo C52 | USD 8,2322 | USD 6,0767 | USD 12,1555 |
| Downside, sólo C53 | USD 8,2154 | USD 6,0767 | USD 12,1387 |
| Downside conjunto | USD 8,2456 | USD 6,0767 | USD 12,1689 |

En Base conjunto se aportan aproximadamente USD 4,595182 el 30/09/2027 y USD 0,059531 por trimestre entre el 30/12/2027 y el 30/09/2028. Se cobran USD 2,846667 de refi el 30/09/2028 y USD 1,431058 de operación más USD 13,781629 de venta el 30/12/2028. En Downside conjunto se aportan USD 0,775617 el 30/06/2027, USD 0,039302 el 30/09/2027, USD 7,037619 el 30/12/2027 y USD 0,078604 por trimestre entre el 30/03/2028 y el 30/03/2029. Se cobran USD 2,445833 de refi el 30/03/2029 y USD 0,549690 de operación más USD 3,081180 de venta el 30/06/2029. Cada importe exacto y fecha se conserva en `cash_per_usd_10.events`; se redondea después de totalizar.

Los cobros permanecen iguales en estos ensayos porque se conserva el mismo principal de obra efectivamente girado y el costo financiero se cubre con aportes. Cambian los aportes y, por lo tanto, el resultado neto y el múltiplo. Estos valores prueban las conexiones; no son nuevos criterios ni supuestos para un deal real.

## Variables, respaldo y cálculo

| Requisito y ubicación | Definición vigente en el perfil | Conexión y evidencia | Estado |
|---|---|---|---|
| Inputs!C51 | Compromiso = menor entre costo directo elegible × LTC y límite contractual | D146; compromiso cotejado con LTC y límite. Los giros siguen la solicitud de facturas y la disponibilidad por fecha | Conectado en sintético |
| Inputs!C52 | Interés nominal anual simple por trimestre sobre saldo inicial más draw al inicio | D146/T68; interés exacto por período y conciliación con pagos/aportes | Conectado en sintético |
| Inputs!C53 | Comisión de apertura = compromiso × fracción explícita; pagada al abrir | D146; comisión, caja inicial y aportes posteriores conciliados | Conectado en sintético |
| Cotización de cada variante | PDF de una página con escenario, deal, revisión, unidades, convenciones y padre verificado | B08; hash, filas, alcance y coincidencia exacta con las celdas | Validado en sintético |
| Refi y retorno por USD 10 | Repago del principal realmente girado, cierre conciliado y flujos brutos fechados | D146 y motor vigente; fuentes/usos, principal, interés, aportes y cobros cotejados | Validado en sintético |

El ensayo declara, por separado y luego juntos:

- Base: C51 de 60 % a 65 %; C52 de 8 % a 9 % anual; C53 de 1 % a cero explícito.
- Downside: C51 de 50 % a 40 %; C52 de 10 % a 11 % anual; C53 de 1,5 % a 2 %.

| Importe del proyecto completo, USD | Base original | Base conjunto | Downside original | Downside conjunto |
|---|---:|---:|---:|---:|
| Compromiso | 1.524.000 | 1.600.000 | 1.250.000 | 1.097.600 |
| Principal efectivamente girado y repagado | 635.000 | 635.000 | 686.000 | 686.000 |
| Intereses de obra | 57.150 | 64.293,75 | 102.900 | 113.190 |
| Comisión de apertura | 15.240 | 0 | 18.750 | 21.952 |

En Base, subir el LTC lleva el compromiso al límite contractual de USD 1.600.000, pero conserva giros por USD 635.000 porque la solicitud sigue siendo 25 % de las facturas elegibles. En Downside el LTC de 40 % pasa a ser el límite activo. La comisión del conjunto se calcula sobre el compromiso nuevo: no se suman los impactos aislados.

## Contrato sintético v5

`rent_inputs.sensitivities` admite `miniuw.synthetic-worksheet-sensitivities.v5` dentro del perfil de aceptación técnica. Este contrato se concentra en C51–C53, con uno a tres cambios únicos por escenario. Los contratos anteriores, incluido [D256](workbook-calendar-sensitivities-D256.md), conservan su alcance y reproducción.

Cada cambio declara `target_cell`, `operation`, `unit`, `value` exacto y `source_ref`. Las unidades de reemplazo son `fraction` para C51, `annual_nominal_fraction` para C52 y `fraction_of_commitment` para C53. También se admiten cambios relativos, puntos básicos y puntos porcentuales con las unidades explícitas de la operación.

Cada escenario agrega `construction_support.individual` por celda y `construction_support.combined` para el conjunto. Cada soporte exige `source_ref`, `revision`, `parent_document_id`, `parent_sha256`, `pdf_sha256` y `pdf_base64`. El PDF debe contener la página bancaria sintética del escenario y deal correctos, con todos sus campos y convenciones. El padre es la cotización ya leída del expediente original. El PDF nuevo se lee como texto, sin atribuirle una lectura OCR.

El PDF sólo puede variar LTC, tasa y comisión. Compromiso contractual máximo, fracción solicitada de facturas, disponibilidad por draw y vencimiento se conservan. El motor vuelve a comparar la cotización con los valores completos de la variante: un cambio no declarado en otra celda también queda PENDING. La evidencia conserva la huella del padre y la del PDF nuevo, su revisión, página, citas y método de lectura. El PDF está incluido en el JSON del caso para que B16 pueda reproducirlo.

Cada PDF está limitado a 32 KiB; el JSON completo v5 del perfil sintético admite hasta 96 KiB. Los contratos anteriores conservan el límite de 48 KiB y los perfiles previos que corresponda conservan además su límite de 32 KiB. La prueba comprueba estas restricciones. Los soportes no amplían límites bancarios ni autentican una aprobación real.

## Pruebas, bloqueos y reproducción

La aceptación verifica seis cambios individuales y dos conjuntos. Conciliaciones: menor límite LTC/contractual, draws y principal por período, interés, comisión, pagos por fecha, repago de obra en refi, cierre y caja por USD 10. El presupuesto, NOI, calendario y cobros originales se conservan donde el cambio no los afecta. La corrida conjunta usa los tres términos simultáneamente y recoge la interacción entre compromiso y comisión.

Los controles prueban vacíos en la base y el cambio, ausencia de valor o fuente, unidades inválidas, hash alterado, padre incorrecto, filas faltantes, escenario equivocado y cambios indebidos de límites. Los cálculos afectados quedan PENDING. Una cotización que no coincide con C53 también queda PENDING. En otro control, C52 = 0 produce interés cero explícito; C51 = 0 conserva ese valor y deja PENDING la financiación porque los giros solicitados superan el compromiso cero. C53 = 0 produce comisión cero en el ensayo válido. Ningún vacío se interpreta como cero.

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_construction_sensitivities
PYTHONPATH=src:tools:tests python3 tools/check_worksheet_construction_financing_D146.py --output /tmp/miniuw-d257-d146
```

Se utilizan las dependencias de referencia y OCR del repositorio para los respaldos originales. Los paquetes generados y registros del VPS quedan fuera de GitHub; se preservan código, pruebas y esta descripción. El PDF de decisión original conserva su alcance. El perfil sigue usando interés trimestral simple pagado en caja; otros calendarios y capitalización requieren términos y cálculo compatibles. No se adoptan valores por defecto ni se habilitan despliegue o decisiones reales.

En el VPS pasaron las cuatro pruebas nuevas, con seis corridas individuales y dos conjuntas válidas más los controles PENDING y de cero explícito. D146 pasó sus quince casos, con diez PENDING esperados. B16 reprodujo D256 sin diferencias. La ejecución por consola del expediente v5 coincidió byte por byte en sus diez archivos con el ensamblador D198. Se ejecutaron verificaciones dirigidas; la última batería general íntegra sigue siendo la registrada para D253.
