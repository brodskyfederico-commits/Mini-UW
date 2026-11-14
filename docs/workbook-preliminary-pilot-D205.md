# Si invierto USD 10, ¿cuánto cobro y cuándo?

El primer piloto PRELIMINAR reproduce el caso sintético residencial D204 desde las planillas y los respaldos. [Informe de una página con todos los flujos fechados](review/MiniUW_Preliminar_Piloto_D205.pdf)

| Escenario | Aporte adicional total | Refinanciación el 30/12/2027 | Cobro trimestral en 2028 | Venta neta el 30/12/2028 | Total cobrado | Sin recuperar |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Base | USD 6,22 | Cobra USD 2,65 | USD 0,63 | USD 23,98 | USD 29,14 | USD 0,00 |
| Downside | USD 8,01 | Aporta USD 0,17, incluido en el total adicional | USD 0,39 | USD 7,52 | USD 9,06 | USD 8,95 |

Los importes corresponden a USD 10 iniciales de equity agregado. Los totales se calculan antes de redondear.

## Cómo correrlo

```bash
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py run templates/preliminary-pilot-D205 /tmp/miniuw-pilot-D205
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py audit /tmp/miniuw-pilot-D205
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_pilot_D205.py
```

El comando de corrida requiere un directorio de salida nuevo. El comando de auditoría recalcula el expediente y compara el contenido archivo por archivo. El paquete de salida incluye el PDF, la caja exacta, el ranking, los motivos de bloqueo y la copia de las fuentes usadas.

## Fuentes y controles

El [inventario del piloto](../templates/preliminary-pilot-D205/pilot.json) fija los dos proyectos de prueba, la fecha de corte, el calendario común y las huellas de las fuentes. Por proyecto y escenario, el ingreso lee un archivo Inputs.xlsx y siete respaldos estructurados de prueba con fuente, fecha y responsable.

| Respaldo | Datos vinculados |
| --- | --- |
| Programa | Unidades y base de renta |
| Adquisición y costos | Terreno, costo de obra, estacionamientos y alcance |
| Renta y gastos | Rentas, pérdidas, gastos y reposición |
| Calendario | Plazos de obra, absorción y costo de tenencia |
| Financiación | Desembolsos de obra, límites, vencimientos y solicitud de refinanciación |
| Salida | Cap, costos de venta y destino de las reservas |
| Fiscal | Padrones, tasación, millage escolar y no escolar y evidencia de retasación de M2 |

Los respaldos JSON contienen datos sintéticos preparados para probar la carga y la conciliación. La corrida coteja sus valores de celda contra las hojas Inputs y aplica los cálculos de D204 con M2. El piloto permite reproducir esta cadena con los respaldos archivados. La extracción desde documentos de un deal real y la validación del ranking real siguen pendientes de la autorización y del expediente correspondiente.

## Resultado de aceptación

El ranking sintético ordena por múltiplo de equity de Downside. El caso de referencia quedó primero con 0,5031×. El comparador quedó segundo con 0,4204× al usar un cap de salida Downside de 18 % en su planilla y respaldo. Las entradas no incluyen un Excel de criterios de Lorena. El dictamen formal y el retorno personal quedan PENDING.

Se verificaron 32 archivos de origen y cinco variantes bloqueadas. Se retiraron los respaldos fiscal y financiero en pruebas separadas. También se alteró un respaldo sin actualizar su huella, se registró una renta discrepante con la planilla y se registró un respaldo fiscal sin tasa no escolar. El caso afectado quedó PENDING y fuera del ranking en cada variante. Base conservó su caja y el comparador permaneció disponible. Al reponer el respaldo fiscal original, se reprodujo el paquete completo byte a byte. [Evidencia de ejecución](review/MiniUW_Verificacion_D205.json)
