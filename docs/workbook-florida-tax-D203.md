# Si invierto USD 10, ¿cuánto cobro y cuándo?

El ensayo sintético de M2 usa USD 10 de equity inicial agregado. El expediente muestra los aportes y cobros por fecha. [Informe de una página](review/MiniUW_Informe_USD10_D203.pdf)

| Escenario | Aportes adicionales | Cobro en refi | Operación y venta | Total cobrado | Sin recuperar |
| --- | ---: | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,85 el 30/09/2028 | USD 16,66 el 30/12/2028 | USD 19,51 | USD 0,00 |
| Downside | USD 8,19 | USD 2,45 el 30/03/2029 | USD 4,69 el 30/06/2029 | USD 7,13 | USD 11,06 |

Los totales se calculan antes de redondear. El cotejo con la corrida D200 da USD 1,45 adicionales en Base y USD 1,06 en Downside. La comparación incorpora las valoraciones fiscales y tasas sintéticas declaradas y la retasación del comprador. La diferencia no mide aisladamente el efecto del tope de 5 %.

## Regla y evidencia que consume M2

En el perfil residencial sintético v32, la tasación no escolar de un inmueble alcanzado, en un año sin ajuste aplicable, es el menor entre su valor justo y la tasación no escolar del año anterior multiplicada por 1,05 desde el padrón 2027. La prueba de cambio de vigencia usa 1,10 en el padrón previo. La base imponible escolar ingresa por separado con su propia cifra. Cada componente se multiplica por su millage declarado y se divide por 1.000. [Boletín PTO 26-21](https://floridarevenue.com/property/Documents/PTO_BUL_26-21.pdf) · [Enmienda 3, art. VII §4(g)–(h), pp. 6–7](https://www.flsenate.gov/Session/Bill/2026F/1F/BillText/er/PDF)

La retasación aplica el valor justo cuando existe evidencia de un cambio de titularidad o control, o de una mejora calificada en el perfil §4(h) ensayado. El módulo recibe esa clasificación como un dato con fuente y fecha. No infiere la calificación a partir del costo de obra. El caso Downside incorpora una mejora calificada de prueba en el padrón 2028 y vuelve al tope anual en 2029. El flujo de salida distingue el padrón que rige al vender de la retasación del comprador al siguiente 1 de enero. [Florida §193.1555](https://www.flsenate.gov/Laws/Statutes/2026/193.1555)

| Prueba sintética | Resultado |
| --- | --- |
| Tope de 2027 | Una tasación anterior de USD 1.500.000 y un valor justo de USD 2.000.000 dan una base no escolar de USD 1.575.000. |
| Base, padrón 2028 | Valor justo y base escolar de USD 2.500.000, base no escolar de USD 1.653.750. |
| Downside, mejora calificada | Base no escolar de USD 3.000.000 en 2028 por retasación y USD 3.150.000 en 2029 por el tope. |
| Retasación en la salida | El primer padrón del comprador usa el valor justo. Downside pondera seis meses del padrón previo y seis del padrón retasado en el NOI de salida. |
| Evidencia ausente | Tasación de apertura, millage no escolar, respaldo del ajuste o tasación del comprador. En cada prueba se bloquea Downside y se conserva Base. B16 y el dictamen devuelven PENDING. |

La corrida vincula el impuesto de cada ventana con el NOI operativo, bancario, de valoración y de salida. También usa el impuesto del tramo en el CoC posrefi. Los doce meses de cada ventana se ponderan por mes para el devengo sintético. Operación y venta conservan las fechas de liquidación del expediente.

El ensayo cubre inmuebles clasificados como no homestead con inventario explícito de exclusiones y ajustes. Casos con exenciones, ajustes que no se puedan clasificar y documentación fiscal real quedan PENDING hasta contar con su evidencia. La corrida con datos reales y la autorización de despliegue permanecen fuera del ensayo.

## Reproducción en el VPS

Con las dependencias y el entorno OCR de [D200](worksheet-technical-acceptance-D200.md):

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 tools/check_worksheet_florida_tax_D203.py
```

[Configuración sintética](../templates/synthetic-florida-tax-settings-D203.json) · [Conciliación y casos PENDING](review/MiniUW_Verificacion_D203.json)
