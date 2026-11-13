# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el caso sintético, Base cobra USD 18,06 hasta el 30/12/2028 y aporta USD 4,87 adicionales. Downside cobra USD 6,08 hasta el 30/06/2029, aporta USD 8,19 adicionales y conserva USD 12,11 sin recuperar. El [informe D181](review/MiniUW_Informe_USD10_D181.pdf) detalla los movimientos.

## Qué pasa si una regla llega mal cargada

El perfil integrado v29 conserva el informe de una página cuando la revisión vigente contiene un criterio mal formado o repetido. Una fila identificable con un umbral inválido queda PENDING. Dos filas para la misma métrica y escenario dejan PENDING esa comparación. El motor conserva los flujos ya verificados y las comparaciones independientes. Los índices de las reglas válidas siguen apuntando al inventario original.

Un inventario con formato incorrecto o identidad indeterminada deja PENDING todas las comparaciones. El expediente registra el bloqueo y, para los registros identificables con formato incorrecto, la posición del criterio. Los registros históricos válidos conservan su reproducción.

La regresión agrega cuatro casos al piloto D181: umbral con denominador cero en YoC, umbral con denominador cero en TIR, criterio duplicado y formato inválido de inventario. En cada caso se reabre el PDF y se cotejan los flujos y el dictamen. Decisión real y retorno personal PENDING. Prueba sintética en el VPS.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_integrated_screening_D181.py --output /tmp/miniuw-d183
```

[Registro del ensayo](review/MiniUW_Verificacion_D183.json) · [Expediente profesional al corte D182](review/MiniUW_Expediente_Revision_Profesional_D182.pdf).
