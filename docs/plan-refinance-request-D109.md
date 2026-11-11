# Si invierto USD 10, ¿cuánto cobro y cuándo con la nueva solicitud?

El [plano revisado D105](plan-schedule-intake-D105.md) conserva 20 unidades, con 690 ft² rentables cada una, y declara cero unidades de dos dormitorios. El préstamo sintético original de USD 1.400.000 deja Downside **PENDING** por capacidad. D109 ingresa una solicitud nueva de **USD 1.100.000** con su propia entrada, conservando la misma revisión del plano y las condiciones de renta, obra, crédito y venta de D108. La prueba usa la caja del equity agregado del proyecto.

| Flujo por USD 10 iniciales | Fecha | Base | Downside |
| --- | --- | ---: | ---: |
| Aporte inicial | 30/03/2027 | 10,00 | 10,00 |
| Aporte adicional de obra | 30/06/2027 | 0,42 | 0,42 |
| Cobro neto de refinanciación | 30/03/2028 | 4,49 | 4,49 |
| Cobro de operación después de cuota | 30/06/2028 | 0,93 | 0,69 |
| Cobro neto de venta después de cancelar deuda | 30/06/2028 | 6,84 | 2,75 |
| **Cobro total** | Hasta la venta | **12,26** | **7,93** |
| **Sin recuperar** | Al vender | **0,00** | **2,49** |

USD nominales, redondeados por separado. El saldo sin recuperar incluye el aporte extra. La capacidad de Downside sigue en USD 1.161.903,42. La nueva solicitud queda USD 61.903,42 por debajo. En el mismo plano sin refinanciación, Downside cobra USD 8,08 y queda con USD 2,34 sin recuperar al vender. La refinanciación adelanta USD 4,49 y reduce el cobro nominal total en USD 0,15 por USD 10 por la comisión y el interés de un trimestre. [Corrida sin refinanciación D107](plan-return-per-usd10-D107.md) · [Capacidad y términos D108](plan-refinance-per-usd10-D108.md).

## Entrada y auditoría

El [caso sintético D109](../templates/synthetic-plan-refinance-request-D109.json) identifica la solicitud, el monto exacto en USD y los hashes de ambos planos. El perfil usa el plano revisado y los términos sintéticos D108. El comando habitual genera un PDF de una página, el expediente JSON con los flujos por fecha y un manifiesto con hashes. La auditoría vuelve a calcularlo desde la entrada y las fuentes.

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py run templates/synthetic-plan-refinance-request-D109.json --output /tmp/miniuw-D109
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-D109
PYTHONPATH=src python3 tools/check_plan_refinance_request_D109.py
```

La prueba ejecuta las dos solicitudes, conserva Base disponible cuando Downside supera capacidad y comprueba que una corrida nueva no reemplaza el expediente previo. Rechaza un plano con hash obsoleto, un principal ausente, cero, una fracción de centavo, una identidad no sintética y un resultado alterado. Toda cifra pertenece al caso sintético. Las condiciones reales, el retorno personal y la decisión de inversión siguen PENDING.
