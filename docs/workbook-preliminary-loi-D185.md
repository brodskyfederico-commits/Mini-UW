# Si invierto USD 10, ¿cuánto cobro y cuándo?

El ejemplo D185 arranca con USD 10 de equity agregado el 30/03/2027. Los flujos se cargan como estimaciones de prueba en USD del proyecto y se normalizan con el aporte inicial. Las cifras son antes de impuestos personales.

| Caso A · por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte adicional · 30/06/2027 | USD 2,00 | USD 3,00 |
| Cobro operativo · 30/12/2027 | USD 1,00 | USD 0,50 |
| Cobro neto de venta · 30/03/2028 | USD 14,00 | USD 9,50 |
| Cobro total | USD 15,00 | USD 10,00 |
| Resultado neto nominal | +USD 3,00 | −USD 3,00 |
| Sin recuperar al cierre | USD 0,00 | USD 3,00 |

[Informe sintético de una página](review/MiniUW_Preliminar_LOI_D185.pdf). Dictamen formal, retorno personal y valor retenido PENDING. Las cifras son ilustrativas de la ruta sin refi del fixture. La prueba también incluye la ruta con refi.

## Qué hace el ensayo

El perfil `miniuw.synthetic-preliminary-loi.v1` recibe supuestos de programa, adquisición y costos, renta y gastos, calendario, financiación y salida por escenario. Cada grupo tiene fuente, fecha y responsable. Cada evento de caja conserva su propio importe, fecha, fuente y responsable. Se requieren Base y Downside completos. Los importes aplicables de cero se declaran de forma expresa.

La convención de ensayo compara casos en USD de equity agregado con fecha de corte, grilla trimestral y ruta de financiación comunes. Ordena de mayor a menor por el múltiplo de equity estimado de Downside. El múltiplo usa todos los aportes y cobros brutos. Empates comparten posición. Un caso con un faltante o una base de comparación distinta queda fuera del ranking. Un escenario con caja respaldada sigue disponible si el otro está PENDING.

La caja se ingresa como proyección indicativa. El perfil reutiliza el motor de retornos para normalizar los eventos, sumar aportes y cobros, y reproducir el paquete. Los respaldos son declarativos en este ensayo. La derivación de los flujos desde presupuestos, rentas y documentos reales y el uso operativo requieren validación. El ranking sólo prioriza revisión. El resultado formal de esta ruta siempre es PENDING y el expediente conserva la elegibilidad para Full UW en falso.

## Qué se verificó

La prueba corre por el comando habitual y vuelve a leer el paquete y su PDF. Coteja normalización, fechas, orden, exclusión de un caso sin Downside, datos nulos, fuentes con fecha posterior al corte, faltante de responsable, horizonte o financiación incompatibles, empate, refi y aporte/cobro contradictorios de refi. [Resultado de ejecución](review/MiniUW_Verificacion_D185.json).

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_D185.py --output /tmp/miniuw-d185
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d185
```

## Cierre del piloto

La política de mínimos y ranking de D185 es una propuesta sintética para probar el circuito. La base operativa, el uso de datos reales y la aprobación de SRC-02/SRC-03 siguen pendientes. Para la corrida formal se requieren el inventario de criterios vigentes, responsables designados y un expediente Base/Downside con sus fuentes. Un PASS vigente más aprobación auténtica habilita evaluar el paso de ese deal a Full UW.
