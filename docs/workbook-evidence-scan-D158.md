# D158 · OCR de cotizaciones y documentos bancarios

## Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida sintética usa el equity agregado del proyecto. Las fechas de cada aporte adicional y el resultado de las alternativas están en el PDF de salida.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. El caso completo reproduce los movimientos de D157. El dictamen real permanece PENDING.

## Evidencia y conexiones

| Fuente de `Evidence.pdf` | Control | Destino |
|---|---|---|
| p. 4 · Cotización GC con área e importes | B03 clasifica la página por el encabezado reconocido. B08 extrae las partidas y B09 las coteja con plano y presupuesto. | B13 conserva la cita OCR y la huella de la imagen en el costo de obra. |
| pp. 3 y 6 · Préstamo permanente Downside y Base | B08 coteja C69–C72, principal, frecuencia, vencimiento y convenciones. | B13 incorpora la lectura citada al cálculo de deuda y capacidad. |
| pp. 2 y 5 · Crédito de obra Downside y Base | B08 coteja C51–C53, compromiso, giro disponible, vencimiento y convenciones. | Los desembolsos, intereses y cancelación de deuda se reproducen con la evidencia vinculada. |
| p. 1 · Copia oficial local en texto PDF | B10 y B11 verifican copia y vigencia bajo el perfil D157. | El expediente conserva la fuente local citada. |

Las cinco páginas financieras del archivo de prueba contienen una imagen completa en escala de grises. El expediente conserva el número de página, la huella de la imagen, el texto reconocido, las regiones de píxeles y la confianza mínima por renglón. El piloto usa el runtime OCR fijado en D131, con segmentación para un bloque de texto y mínimo sintético de 60 sobre 100. En caso de texto superpuesto, se conservan dos lecturas y ambas deben estar completas y concordar en sus valores e identidad.

| Ensayo | Resultado |
|---|---|
| Texto superpuesto que coincide con el OCR | Los dos cotejos quedan registrados y se reproducen los flujos. |
| C72 borrada físicamente en la imagen del banco Downside | Downside PENDING. Base conserva su cálculo. |
| Cotización GC con USD 2.340.000 en la imagen y USD 2.340.001 en el texto | PENDING. Se conservan ambas lecturas y se bloquean los escenarios que dependen de la cotización compartida. |
| Capa de texto incompleta con imagen completa | PENDING. El campo faltante se registra como discrepancia de lectura. |
| Vencimiento reconocido distinto de la condición declarada | PENDING para el escenario afectado. |
| Confianza inferior al mínimo, página financiera sin imagen o rol duplicado | PENDING. |
| Runtime de OCR no disponible | PENDING. |

El alcance cubre documentos sintéticos textuales en escaneos derechos y con renglones delimitados. La validación con otros formatos y documentos reales sigue pendiente.

## Reproducción en el VPS

B16 vuelve a leer los archivos guardados y reproduce el resultado. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_scan_D158.py --output /tmp/miniuw-d158
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d158 \
  --current-revision templates/synthetic-workbook-current-revision-D158.json
```
