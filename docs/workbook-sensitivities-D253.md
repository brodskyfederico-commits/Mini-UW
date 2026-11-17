# Si invierto USD 10, ¿cuánto cobro y cuándo?

D253 recalcula sensibilidades explícitas de cap de salida (C67), costo de venta (C68) y crecimiento de rentas (C75). La prueba usa el expediente sintético de aceptación D200. Los montos representan caja del proyecto por cada USD 10 de equity inicial verificado.

| Escenario y variante | Aporte adicional | Cobro de refi | Cobro operativo al cierre | Venta neta al cierre | Cobro total | Sin recuperar |
|---|---:|---:|---:|---:|---:|---:|
| Base original | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,78 | USD 18,06 | USD 0,00 |
| Base con los tres cambios | USD 4,87 | USD 2,85 | USD 1,43 | USD 13,26 | USD 17,54 | USD 0,00 |
| Downside original | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,08 | USD 6,08 | USD 12,11 |
| Downside con C68 en 0 % | USD 8,19 | USD 2,45 | USD 0,55 | USD 3,72 | USD 6,72 | USD 11,47 |
| Downside con los tres cambios | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

El aporte inicial en ambos escenarios es el 30/03/2027. En Base se agregan USD 4,66 el 30/09/2027 y cerca de USD 0,05 por trimestre entre el 30/12/2027 y el 30/09/2028. La refi se cobra el 30/09/2028 y la operación y la venta el 30/12/2028. En Downside se agregan USD 0,76 el 30/06/2027, USD 0,04 el 30/09/2027, USD 7,03 el 30/12/2027 y cerca de USD 0,07 por trimestre entre el 30/03/2028 y el 30/03/2029. La refi se cobra el 30/03/2029 y la operación y la venta el 30/06/2029. El expediente guarda cada importe exacto y calcula los totales antes de redondear.

En Base, C67 sube de 8,75 % a 9,25 % y, por separado, reduce el cobro a USD 17,02. C75 baja de 3 % a 2 % anual y reduce el cobro a USD 17,82. C68 baja de 4 % a 0 % y eleva el cobro a USD 18,86. La corrida conjunta vuelve a calcular el NOI y el cierre, por lo que recoge la interacción entre precio y costos de venta.

En Downside, C67 en 12,50 % queda PENDING por exceder el rango de mercado documentado en el caso sintético. C75 en −12 % anual deja la refi solicitada por encima de la capacidad. C68 en 0 % se calcula por separado. La combinación y el ranking de Downside quedan PENDING. El dictamen y el retorno histórico del 1101 real siguen PENDING.

## Entrada, salida y bloqueos

En el ensamblador D198, el perfil sintético de aceptación técnica admite `rent_inputs.sensitivities` de tipo `miniuw.synthetic-worksheet-sensitivities.v1`. Debe declarar `scenarios.Base.changes` y `scenarios.Downside.changes`. Cada lista admite de uno a tres cambios con celdas distintas. Cada cambio lleva `target_cell`, `operation`, `unit`, `value` como fracción exacta y `source_ref` sintético declarado.

| Operación | Unidad | Recálculo |
|---|---|---|
| `replace_absolute` | Unidad de la celda | Valor de reemplazo explícito, incluido cero |
| `relative_change` | `fraction_of_baseline` | Valor original × (1 + cambio) |
| `basis_point_change` | `bps` | Valor original + cambio ÷ 10.000 |
| `percentage_point_change` | `percentage_points` | Valor original + cambio ÷ 100 |

Cada cambio guarda la celda original, los valores antes y después y la referencia al expediente. La corrida vuelve a pasar por los controles de evidencia, parámetros y capacidad del motor. La falta de una fuente vigente, una unidad inválida o un bloqueo financiero impide publicar la caja afectada. El ranking requiere todas las corridas individuales y ordena de menor a mayor por el cambio en cobros menos aportes, sin descuento. Los empates comparten posición. La corrida conjunta se informa por separado.

`results.json` registra los resultados en `sensitivity_evaluation`. Incluye aportes y cobros fechados por USD 10 y sus diferencias frente al original, para la ruta principal de caja del expediente. Las sensibilidades son un análisis sintético separado del PDF de decisión y del dictamen. La derivación automática de Downside, los demás drivers y el Upside de la Política 33 quedan pendientes de implementación y, donde corresponda, de aprobación de criterios.

## Reproducción en el VPS

Con las dependencias de referencia y OCR del repositorio:

```sh
PYTHONPATH=src:tools:tests python3 -m unittest -v test_worksheet_sensitivities
PYTHONPATH=src:tools python3 tools/check_worksheet_alternatives_D155.py --output /tmp/miniuw-d155
```

La prueba nueva ensambla el expediente original y las variantes, verifica los cobros contra sus movimientos y el precio de salida, reproduce el expediente por B16 y prueba unidad inválida y revisión financiera desactualizada. D155 verifica la compatibilidad de las alternativas C80–C82.
