# Si invierto USD 10, ¿cuánto cobro y cuándo?

El caso sintético aporta USD 10 de equity agregado el 30/03/2027. El [PDF de una página](review/MiniUW_Preliminar_Obra_Etapas_D188.pdf) detalla cada movimiento por fecha, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte de obra · 30/06/2027 | USD 3,44 | USD 4,24 |
| Aporte de obra e interés previo · 30/09/2027 | USD 2,48 | USD 3,28 |
| Absorción e interés final · 30/12/2027 | USD 0,30 | USD 0,32 |
| Movimiento neto al refinanciar · 30/12/2027 | Cobro USD 2,65 | Aporte USD 0,17 |
| Aportes adicionales totales | USD 6,22 | USD 8,01 |
| Cobro operativo por trimestre · marzo a diciembre de 2028 | USD 0,65 | USD 0,42 |
| Cobro neto de venta · 30/12/2028 | USD 26,05 | USD 8,47 |
| Total cobrado | USD 31,29 | USD 10,15 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,86 |

Los totales se calculan con importes exactos y luego se redondean. El dictamen formal y el retorno personal permanecen PENDING.

## Cómo se calculan las etapas

El perfil `miniuw.synthetic-preliminary-loi-workbook.v3` conserva dos XLSX del formato original Inputs y el expediente JSON vinculado por huellas. C34–C40 determinan el presupuesto. C42 asigna el costo blando temprano y C46–C47 delimitan las etapas y la absorción. El expediente complementario declara para cada trimestre de obra su fecha, participación del costo directo elegible, fracción solicitada, disponibilidad, fuente y responsable. Las participaciones deben sumar 100 %. El préstamo de cada etapa se calcula multiplicando el costo directo elegible de la planilla por la participación y la fracción solicitada.

El motor exige que la solicitud por etapa quede dentro del costo elegible y la disponibilidad. El acumulado queda sujeto al menor entre el compromiso declarado y el costo directo por LTC (C51). La comisión C53 se calcula sobre ese compromiso y se paga en la primera etapa según la convención de este ensayo. El interés simple de cada trimestre es el saldo de apertura más el desembolso al inicio del intervalo, por C52 dividido entre cuatro. El aporte de obra cubre los costos y el interés exigible en esa fecha, descontando el desembolso. En refi se cancela el principal efectivamente desembolsado. El expediente guarda el calendario de deuda y sus fuentes junto a las cifras calculadas.

| USD de proyecto | Base | Downside |
| --- | ---: | ---: |
| Primer desembolso · 30/06/2027 | USD 25.000 | USD 30.000 |
| Segundo desembolso · 30/09/2027 | USD 35.000 | USD 40.000 |
| Interés pagado · 30/09/2027 | USD 500 | USD 600 |
| Interés pagado · 30/12/2027 | USD 1.200 | USD 1.400 |
| Interés total | USD 1.700 | USD 2.000 |
| Principal cancelado en refi | USD 60.000 | USD 70.000 |

Los ensayos conservan el calendario trimestral residencial y la refinanciación al estabilizar. Las fracciones de etapa y la disponibilidad pertenecen al expediente complementario sintético. Los términos bancarios reales, otro calendario o una convención distinta de interés o comisiones requieren evidencia y validación propias.

## Bloqueos y reproducción

Una celda mínima ausente, una etapa incompleta, una fecha incompatible o un exceso de disponibilidad, compromiso o capacidad de refi retiran la caja del escenario afectado. Se conserva la caja independiente y el caso queda fuera del ranking. El control de refi sigue usando el menor límite aplicable de LTV, DSCR y debt yield. El dictamen formal sigue PENDING en toda la ruta.

Se cotejaron los aportes y cobros fechados contra aritmética independiente. Las doce variantes incluyen C52 y C72 vacíos, disponibilidad faltante, fecha incorrecta, desembolso superior al costo elegible, participaciones inconsistentes, excesos de disponibilidad, compromiso y refi, cero explícito, reprogramación de un desembolso y recálculo de deuda al modificar C35. El perfil D187 de desembolso único reproduce sus resultados y PDF.

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_stages_D188.py --output /tmp/miniuw-d188
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d188
```

[Registro de verificación](review/MiniUW_Verificacion_D188.json).
