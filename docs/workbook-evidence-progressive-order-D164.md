# D164 · OCR de evidencia financiera en JPEG progresivo fuera de orden

## Si invierto USD 10, ¿cuánto cobro y cuándo?

La corrida sintética usa el equity agregado del proyecto. El PDF de salida muestra cada aporte adicional por fecha.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. La capacidad de refinanciación y todos los movimientos fechados reproducen D163. El dictamen real permanece PENDING.

## Qué se probó

El PDF usa este orden físico: préstamo permanente Base, cotización compartida, crédito de obra Base, copia oficial, préstamo permanente Downside y crédito de obra Downside. Las cinco páginas financieras se generan en JPEG progresivo, con giros de 90°, 180° o 270° y recortes en los márgenes. La copia oficial conserva su texto. B03 localiza cada documento por el encabezado reconocido. B08 conserva la página física, el giro, el recorte y la cita OCR. B16 vuelve a correr el expediente a partir de los bytes guardados.

| Variante sintética | Resultado |
|---|---|
| Falta la página de crédito de obra Base | Base PENDING. Downside conserva la capacidad y los cobros. |
| El recorte oculta C72 del préstamo Downside y el texto superpuesto conserva el dato | Downside PENDING. Base conserva la capacidad y los cobros. |
| C52 del crédito de obra Downside se lee como 10 % en la imagen y 11 % en el texto | Downside PENDING. Se guardan las dos lecturas. Base conserva sus resultados. |
| La cotización Base indica USD 2.340.000 en la imagen y USD 2.340.001 en el texto | Ambos escenarios PENDING por discrepancia en la cotización compartida. |
| La página del préstamo Base se reemplaza con un duplicado de Downside | El inventario queda PENDING y se retiran ambos resultados. |

La prueba usa los mismos criterios, umbral OCR y cálculo de D163. Los giros y recortes pertenecen al perfil sintético, con coordenadas enteras y un raster por página financiera.

## Reproducción en el VPS

El script genera el expediente fuera de orden, lo corre y lo audita. La carpeta de salida contiene el PDF de evidencia y el resumen de una página. Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md) y el decodificador JPEG declarado.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_progressive_order_D164.py --output /tmp/miniuw-d164
```
