# D162 · JPEG progresivo en el expediente financiero

## Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida sintética usa el equity agregado del proyecto. El PDF de salida muestra cada aporte adicional por fecha y las alternativas.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. La corrida completa reproduce la capacidad y los movimientos fechados de D161. El dictamen real permanece PENDING.

## Alcance y controles

El mismo PDF contiene una cotización en JPEG progresivo RGB, un crédito de obra Base en JPEG progresivo gris, un préstamo permanente Base en JPEG secuencial y dos páginas financieras Downside en Flate. Las cinco páginas financieras se leen por OCR desde sus imágenes. La copia oficial se coteja desde el texto PDF.

D162 identifica el tipo de JPEG al decodificar y conserva la huella de sus bytes, la del raster, el recorte y las citas OCR. El expediente declara el decodificador utilizado. B16 vuelve a correr el cálculo y coteja el PDF y las huellas de origen.

| Ensayo | Resultado |
|---|---|
| Falta C52 en el JPEG progresivo de crédito de obra Base | Base PENDING. Downside conserva su cálculo. |
| La cotización progresiva muestra USD 2.340.000 y el texto superpuesto indica USD 2.340.001 | PENDING para ambos escenarios que dependen de la cotización. Se preservan las dos lecturas. |
| El JPEG progresivo del crédito Base está truncado y hay texto superpuesto legible | Base PENDING. Downside conserva su cálculo. |
| El perfil archivado D161 recibe una página progresiva en el crédito Base | Base PENDING por formato fuera de ese perfil. La corrida secuencial original se reproduce sin cambios. |

El perfil cubre JPEG JFIF progresivo y secuencial en RGB o gris, con las restricciones geométricas del piloto. La validación con documentos reales sigue pendiente.

## Reproducción en el VPS

Se usa el mismo decodificador fijado en D161 y el runtime OCR declarado en el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_progressive_D162.py --output /tmp/miniuw-d162
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d162 \
  --current-revision templates/synthetic-workbook-current-revision-D162.json
```
