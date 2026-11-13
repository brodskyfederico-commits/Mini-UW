# Si invierto USD 10, ¿cuánto cobro y cuándo?

El caso sintético aporta USD 10 el 30/03/2027. La [página por USD 10](review/MiniUW_Preliminar_Planilla_D186.pdf) detalla fechas e importes de ambos escenarios. Los flujos corresponden al equity agregado, antes de impuestos personales.

| Resultado por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, de junio a diciembre de 2027 | USD 11,71 | USD 14,25 |
| Cobros operativos trimestrales, de marzo a diciembre de 2028 | USD 3,45 en total | USD 2,35 en total |
| Cobro neto de venta, incluido el saldo de reservas liberado el 30/12/2028 | USD 33,75 | USD 14,45 |
| Total cobrado | USD 37,20 | USD 16,80 |
| Saldo nominal sin recuperar | USD 0,00 | USD 7,45 |

El resultado formal sigue **PENDING**, incluso si el caso aparece en el ranking preliminar. Los totales se redondean sobre importes exactos.

## De la planilla a los movimientos fechados

La ruta D186 lee dos copias del formato original `Inputs` de 55 campos, una por escenario. El JSON identifica el caso, la fecha, las huellas de ambos libros y el respaldo con fuente, fecha y responsable. El perfil es una prueba residencial sin deuda, con renta mensual por unidad, obra vertical expresada como total y fechas trimestrales comunes. Una corrida recibe un par de planillas del mismo deal. D185 conserva su entrada histórica de proyecciones para varios deals.

| Celdas mínimas del ensayo | Cálculo y control |
| --- | --- |
| C7–C11, C13–C15 | Unidades por tipo documentadas en el respaldo. Renta efectiva tras vacancia y crédito, más otros ingresos. C15 se declara cero en esta ruta y el costo de absorción se documenta aparte. |
| C32–C35, C37–C40, C42 | Terreno y cierre al comprar. Obra directa, estacionamientos, sitio, contingencia y costo blando. C42 fecha el desembolso temprano de costos blandos. El remanente se aporta al terminar la obra. |
| C46–C47 y C51 | Duración de obra y absorción en trimestres. Costo trimestral de absorción documentado. C51 debe ser cero explícito para el caso sin deuda. |
| C57–C60, C62, C75–C76 | Gastos, administración, seguro, impuesto por comparable, reserva y crecimiento anual de renta y gastos fijos. El saldo de reservas se mantiene separado de la caja de operación. |
| C67–C68 | El NOI proyectado para los cuatro trimestres posteriores al cierre dividido por cap de salida estima el precio. Se descuentan costos de venta y se añade la liberación documentada de reservas al cobro del equity. |

El escenario requiere programa, alcance completo de obra y gastos residenciales, espacios de estacionamiento, costo de absorción y política de liberación de reservas. La prueba deja fuera las celdas comerciales y asignaciones de servicios propias de otros perfiles. El período de deuda, la refinanciación, la obra y comercial con contratos detallados y la aplicación fiscal distinta al comparable requieren otra ruta validada. El cálculo conserva esta convención sintética sin cambiar D181 ni la política candidata de D184.

Si falta un mínimo en un escenario, su caja se retira y el deal queda fuera del ranking. La caja del otro escenario se conserva. El ensayo usa el múltiplo de Downside de D185 como convención para priorizar revisión. Un vacío, fórmula o error carecen de valor operativo. Un cero numérico válido participa en el cálculo.

## Reproducción

```sh
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_workbook_D186.py --output /tmp/miniuw-d186
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d186
```

La prueba coteja caja exacta por fecha y saldo sin recuperar con una referencia aritmética. Comprueba una celda vacía, C51 ausente, fórmula con caché, huella incompatible, deuda fuera de perfil y corrección a cero explícito. [Registro de verificación](review/MiniUW_Verificacion_D186.json).
