# Checklist de discrepancias del plano · D209

El [comando de ingreso documental D208](workbook-documentary-intake-D208.md) agrega `preflight.checklist`, con la evidencia, la corrección y los cálculos afectados por cada hallazgo. `preflight.calculations` identifica qué filas bloquean cada cálculo. `plan.verified_inputs` sólo entrega valores cuyo control documental pasó. Las observaciones de origen se conservan en `plan`.

| Fila del checklist | Cálculos directos afectados |
| --- | --- |
| Identificador duplicado o total de viviendas incompatible | Total y mezcla, reservas y obra por unidad, gastos por tipo y ambas bases de renta residencial. |
| Mezcla por dormitorios incompatible | Mezcla, gastos por tipo, metraje rentable y renta residencial por unidad o por área. |
| Tipo sin superficie rentable | Área rentable y renta residencial por superficie. La ruta por unidad conserva su estado documental independiente. |
| Superficie comercial incompatible | Área y renta comercial. La rama residencial conserva su estado documental independiente. |

El efecto aguas abajo pasa por el NOI a la capacidad de refinanciación y a la valoración de salida. Las reservas por unidad también afectan la caja operativa y la obra por unidad afecta los aportes por su propio camino. En este ingreso todavía no se confirmó la base de renta de C7. El gate compartido conserva las dependencias de ambas bases. Un área rentable conflictiva queda separada del área bruta para obra. `CLEAR` sólo indica que el plan no aporta un bloqueo a ese cálculo. La corrida financiera, el dictamen y el retorno por USD 10 siguen PENDING en Base y Downside con el ranking vacío.

La prueba del VPS aisló cada fila del archivo real emitido por D208, comprobó que el gate omite los cálculos afectados y conservó el estado independiente de las otras ramas. La batería sintética también prueba el cálculo de superficies con un expediente limpio, el efecto conjunto de filas y la regresión del checklist XLSX D117. Los archivos y resultados reales quedan en el VPS.

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_documentary_intake.py
PYTHONPATH=src:tests python3 tools/check_worksheet_intake_case_D117.py
```
