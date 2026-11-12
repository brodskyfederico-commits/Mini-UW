# D160 · OCR de evidencia financiera en color y escala de grises

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

Los totales se calculan antes de redondear. Con evidencia legible y coincidente, los flujos y la capacidad reproducen D159. El dictamen real queda PENDING.

## Alcance y evidencia

El archivo de prueba combina cinco páginas financieras giradas y recortadas. La cotización de obra, el préstamo permanente de Base y el crédito de obra de Downside usan RGB. Las otras dos páginas financieras usan escala de grises. La página de copia oficial se coteja desde el texto PDF. El caso positivo usa píxeles de color cuya conversión conserva la luminancia de los escaneos de referencia.

El perfil acepta una imagen completa de 8 bits por canal en `DeviceRGB` o `DeviceGray` con compresión `FlateDecode`. Antes de orientar y recortar, convierte el RGB a gris con coeficientes enteros 299, 587 y 114 sobre 1.000 y redondeo a la unidad más cercana. Guarda la huella del raster en sus canales originales, la huella de la conversión, el giro, el recorte y los renglones OCR citados. La lectura visible conserva los controles de D159.

| Ensayo | Resultado |
|---|---|
| Recorte trunca dígitos de una cotización RGB | PENDING para los escenarios que dependen de la cotización. |
| Imagen RGB muestra 10 % de interés de obra y el texto superpuesto indica 11 % | Downside PENDING. Se conservan ambas observaciones y Base conserva su cálculo. |
| Tasa de interés borrada de la imagen RGB | Downside PENDING. Base conserva su cálculo. |
| Página CMYK acompañada por texto extraíble | Downside PENDING por formato de imagen fuera del perfil. |
| Cambio de color reduce la confianza por debajo del mínimo del piloto | PENDING para los cálculos afectados. |

La validación cubre el formato sintético declarado. Los documentos reales y los formatos de imagen fuera de ese alcance siguen pendientes.

## Reproducción en el VPS

B16 vuelve a leer el archivo mixto guardado. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_color_D160.py --output /tmp/miniuw-d160
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d160 \
  --current-revision templates/synthetic-workbook-current-revision-D160.json
```
