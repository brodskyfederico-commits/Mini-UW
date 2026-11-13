# D171 · Regresión de celdas vacías y ceros explícitos

Una celda aplicable sin valor queda **PENDING** y conserva un valor nulo. Una celda puede quedar **NO APLICA** cuando la revisión lo declara expresamente y el campo admite esa condición. El lector conserva el **0 numérico** en un campo aritmético confirmado. El cálculo aplica luego sus propios requisitos de unidad, fuente y dominio.

## Cobertura

La prueba regenera los XLSX de Base y Downside a partir del original preservado y coteja sus bytes con D166. Para cada uno de los 55 campos en cada escenario, prueba la ausencia de la celda, la celda sin contenido, texto vacío y texto con espacios. Son **440 casos de vacío** con valor nulo en la entrada. El único campo con no aplicabilidad declarada en los dos casos base de D166 es C36. La ausencia y la celda sin contenido preservan esa declaración. Las representaciones textuales vacías quedan PENDING.

También prueba **110 ceros numéricos explícitos**, uno por campo y escenario. El lector conserva 98 ceros en campos aritméticos y devuelve PENDING en los 12 casos correspondientes a campos textuales. Este cotejo es de lectura y confirmación. Los controles del cálculo conservan sus dominios y bloqueos.

## Verificación en la corrida integrada D166

| Ensayo sintético | Resultado |
|---|---|
| C13 sin contenido o ausente | Downside PENDING y sin cobros. Base conserva sus flujos. |
| Fórmula en C13 con cero guardado en caché | Downside PENDING. Se guarda el caché como evidencia. |
| C59 seguro o C72 DSCR ausentes | Downside PENDING y sin cobros. Base conserva sus flujos. |
| C13 igual a cero numérico confirmado | El cero llega al NOI. Downside queda PENDING por el límite de refinanciación. |
| C81 con costo de venta de 0 % confirmado | La alternativa calcula caja con ese valor. |
| C81 sin contenido | La alternativa queda PENDING. Downside conserva los flujos de origen. |

Con los datos completos de D166, por USD 10 iniciales del proyecto Base cobra USD 19,10 hasta el 30/12/2028 y Downside cobra USD 6,80 hasta el 30/06/2029. La prueba compara los movimientos brutos fechados con esa corrida para verificar el aislamiento del escenario afectado.

## Reproducción

Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md). La prueba se incorpora al workflow de referencias y corre localmente con este comando. Los resultados corresponden a datos sintéticos. La decisión real queda PENDING.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_blanks_and_zero_D171.py
```
