# D161 · OCR de evidencia financiera en PDF con JPEG comprimido

## Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida sintética usa el equity agregado del proyecto. El PDF de salida muestra los aportes adicionales por fecha y las alternativas.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. Con los datos visibles y coincidentes, la prueba reproduce los movimientos y la capacidad de D160. El dictamen real permanece PENDING.

## Formato y trazabilidad

La prueba mezcla tres imágenes JPEG sin capa de texto con dos imágenes financieras Flate. El JPEG contiene la cotización de obra en RGB, el crédito de obra Base en gris y el préstamo permanente Base en RGB. Las imágenes JPEG se codifican con ajustes de calidad 97 en RGB y 100 en gris. Las dos páginas Downside conservan el formato Flate, con giros y recortes.

El perfil usa JPEG secuencial JFIF de 8 bits por canal y coteja dimensiones y modo de color con el PDF. B03 registra las versiones de Pillow y libjpeg-turbo. B08 conserva la huella de los bytes comprimidos, la del raster decodificado, el recorte y los renglones OCR citados. B16 vuelve a ejecutar la misma lectura desde los archivos guardados. La validación cubre este formato sintético y la consulta oficial sigue siendo local.

| Ensayo | Resultado |
|---|---|
| Falta C52 en el JPEG de crédito de obra Base | Base PENDING. Downside conserva su cálculo. |
| JPEG de préstamo permanente muestra 5 % y el texto superpuesto indica 6 % | Base PENDING. El expediente conserva las dos observaciones. |
| La cotización JPEG muestra USD 2.340.000 y el texto superpuesto indica USD 2.340.001 | PENDING para ambos escenarios que dependen de la cotización. |
| El JPEG del préstamo Base está truncado y hay texto superpuesto legible | Base PENDING. |
| El decodificador declarado difiere del runtime | PENDING. |

Los JPEG progresivos y otros modos de codificación quedan fuera del perfil probado. La validación con documentos reales sigue pendiente.

## Reproducción en el VPS

El perfil fija Pillow 13.0.0, libjpeg-turbo 3.2.0 y el runtime OCR declarado en el expediente. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_jpeg_D161.py --output /tmp/miniuw-d161
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d161 \
  --current-revision templates/synthetic-workbook-current-revision-D161.json
```
