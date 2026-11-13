# D163 · OCR de JPEG progresivos girados y recortados

## Si invierto USD 10, ¿cuánto cobro y cuándo?

Corrida sintética sobre el equity agregado del proyecto. El PDF de salida detalla cada aporte por fecha.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. La corrida completa reproduce la capacidad y los movimientos fechados de D162. El dictamen real permanece PENDING.

## Evidencia y bloqueos

El PDF sintético de seis páginas incluye tres imágenes JPEG progresivas giradas y recortadas. La cotización está en RGB a 90°, el crédito de obra Base en escala de grises a 180° y el préstamo permanente Base en RGB a 270°. Las dos páginas financieras Downside siguen en Flate y la copia oficial es texto. En el caso completo, las páginas JPEG se leen por OCR y B16 reproduce el PDF, sus citas y la salida. La prueba usa el lector de D162 sin cambiar el motor, los umbrales ni los criterios.

| Ensayo | Resultado |
|---|---|
| El texto superpuesto del préstamo permanente Base coincide con el OCR visible | Se cotejan las dos lecturas y se reproducen la capacidad y los cobros fechados. |
| El recorte oculta C72 del préstamo permanente Base y el texto superpuesto conserva el dato | Base PENDING. Downside conserva sus resultados. |
| El recorte corta un importe de la cotización y el texto superpuesto conserva el dato | Base y Downside PENDING por depender de la cotización. |
| El OCR del préstamo Base indica 5 % anual y el texto indica 6 % | Se guardan ambas lecturas. Base PENDING. Downside conserva sus resultados. |
| El OCR de la cotización indica USD 2.340.000 para Base y el texto indica USD 2.340.001 | Se guardan ambas lecturas. Base y Downside PENDING por discrepancia en la cotización. |
| La primera compresión de las dos imágenes RGB produce renglones por debajo del umbral OCR | La cotización y el préstamo Base quedan PENDING. El umbral de confianza se mantiene en 60. |

El expediente conserva el giro, el área visible, las citas OCR y las huellas de la imagen y del recorte. El ensayo usa giros de página en múltiplos de 90° y un recorte PDF con coordenadas enteras. La validación con documentos reales sigue pendiente.

## Reproducción en el VPS

Se usa el [runtime OCR del piloto](workbook-plan-scan-D131.md) y el decodificador declarado en D162.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_progressive_crop_D163.py --output /tmp/miniuw-d163
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d163 \
  --current-revision templates/synthetic-workbook-current-revision-D163.json
```
