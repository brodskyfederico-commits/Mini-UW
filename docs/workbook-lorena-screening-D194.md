# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el ensayo, los dos escenarios aportan USD 10 el 30/03/2027. Los flujos corresponden al equity agregado del proyecto.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, fechados en el PDF | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro operativo | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| **Cobro total** | **USD 18,06** | **USD 6,08** |
| **Saldo sin recuperar** | **USD 0,00** | **USD 12,11** |

[Informe de una página](review/MiniUW_Informe_USD10_D194.pdf). Los totales se redondean después del cálculo.

## Del Excel al dictamen

El perfil sintético D193 acepta `--criteria` al correr el caso. El JSON identifica las definiciones, períodos y unidades compatibles por métrica. El Excel suministra los operadores y umbrales de las columnas E–H. Las columnas históricas se conservan sólo como referencia. La revisión enlaza el SHA-256 del Excel y la declaración de versión en B18. El paquete guarda el XLSX y B16 vuelve a calcular desde esos bytes. El resultado conserva la celda y literal de cada condición, las reglas normalizadas y los motivos de PENDING.

La ocupación económica es **32,66 % en Base** y **69,37 % en Downside**. El RLV con deuda fija y C33 es **USD 3.200.000** y **USD 2.720.000**, respectivamente. El último precio antes de FAIL es de USD 7.350.000 y USD 4.140.000. Para la definición de RLV de D193, el literal explícito `> banda RLV` en la celda FAIL delega el umbral a la segunda frontera calculada con los criterios de la misma corrida. Una celda vacía deja la fila PENDING. Un límite fijo incompatible con esa frontera también deja PENDING.

| Prueba | Resultado |
| --- | --- |
| Excel sintético completo y vigente | PASS simulado, 20 comparaciones. |
| Se endurecen los límites de ocupación en el Excel | FAIL simulado de Base. |
| Se cambia equity/TDC Base en el Excel | RLV Base baja a USD 640.000. El precio pedido cae en banda y el dictamen queda PENDING. |
| Regla vacía, incompatible, fórmula o Excel faltante | PENDING, con motivo. |
| Excel cambiado o revisión desactualizada | PENDING. |
| Downside marcado «Sin FAIL» | PENDING hasta confirmar la política aplicable. |

Los cambios de criterio en los ensayos conservan la caja por USD 10. El piloto real y el retorno personal siguen PENDING. Los umbrales del ensayo ejercitan la ruta técnica. Las definiciones reales y los criterios con su vigencia requieren confirmación.

## Reproducción

Configurar [el runtime OCR fijado](workbook-plan-scan-D131.md). El verificador genera la evidencia sintética y prueba la interfaz pública, B16 y las variantes.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_lorena_screening_D194.py --output /tmp/miniuw-d194
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d194 \
  --current-revision templates/synthetic-workbook-current-revision-D194.json
```

[Excel sintético](../templates/synthetic-criteria-lorena-D194.xlsx) · [Caso y asignación de bases](../templates/synthetic-workbook-lorena-screening-D194.json) · [Verificación](review/MiniUW_Verificacion_D194.json)
