# D156 · Evidencia documental en PDF

## Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida sintética usa el equity agregado del proyecto. Los aportes adicionales fechados y los cobros por alternativa están en el resumen de una página y en el expediente reproducible.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. Con importes y condiciones coincidentes, la representación documental reproduce los flujos de origen D155. El dictamen real queda PENDING.

## Conexiones y evidencias

| Bot | Fuente en `Evidence.pdf` | Control y destino |
|---|---|---|
| B03 | Encabezado de cada página y huella del archivo | Clasifica por contenido, identifica la revisión y conserva el número de página. Un rol duplicado o un archivo distinto deja PENDING. |
| B08 y B09 | Página 3 · Área y partidas verticales por escenario | Cotejan área, alcance, moneda e importe con el plano y el costo de obra. Se incorpora la cita a la evidencia del presupuesto de B13. |
| B08 y B13 | Páginas 2 y 4 · Préstamo permanente Downside y Base | Cotejan C69–C72, principal solicitado, frecuencia, vencimiento y convenciones del préstamo. El cálculo de deuda y capacidad incorpora la huella del documento. |
| B10 y B11 | Página 1 · Copia oficial archivada | Cotejan el origen permitido del piloto, el intervalo de vigencia y el valor citado. Una copia vencida deja PENDING el dictamen y conserva los flujos independientes. |
| B16 | Paquete con el PDF original de prueba | Reproduce el expediente desde los mismos archivos y la revisión vigente. |

Cada página lleva un identificador sintético de expediente y revisión. El perfil lee un formato PDF textual delimitado y conserva citas exactas. Faltantes, inconsistencias o páginas duplicadas quedan PENDING. La conexión con copias oficiales se prueba localmente. La extracción general de formatos reales y la consulta externa autorizada siguen pendientes.

## Reproducción en el VPS

El verificador coteja una corrida completa, ocho casos PENDING y la auditoría B16. [Runtime de OCR para el plano](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_pdf_D156.py --output /tmp/miniuw-d156
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d156 \
  --current-revision templates/synthetic-workbook-current-revision-D156.json
```
