# D157 · Evidencia del crédito de obra

## Si invierto USD 10, ¿cuánto cobro y cuándo?

Los términos cotejados del piloto reproducen la caja del equity agregado. Las fechas de cada aporte adicional están en el PDF de salida.

| Flujo por USD 10 iniciales | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| **Total cobrado** | **USD 19,10** | **USD 6,80** |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 11,39** |

Los totales se calculan antes de redondear. El dictamen real queda PENDING.

## Conexiones y control

| Fuente | Cotejo | Destino |
|---|---|---|
| `Evidence.pdf` p. 2 y p. 5 | B03 identifica las páginas de crédito de obra de Downside y Base por su contenido, expediente, revisión y huella. | B08 conserva los valores y sus citas. |
| `Inputs!C51:C53` y condiciones complementarias de crédito | B08 coteja el LTC, la tasa nominal, la comisión, el compromiso máximo, la proporción de facturas, la disponibilidad por giro, el vencimiento y las convenciones de cálculo. | B13 incorpora la huella del cotejo al contrato de la deuda. |
| Calendario, desembolsos y caja T68 | Los pagos y desembolsos se concilian con los límites cotejados. La deuda de obra cancelada entra en el cierre de refinanciación. | B16 reproduce la salida y la evidencia desde el paquete original. |

El ensayo de Downside reduce el compromiso documental y la condición declarada a USD 400.000. La evidencia coincide y el motor retiene la caja al detectar que el plan de desembolsos supera el compromiso. Las pruebas también verifican el aislamiento por escenario si difieren la tasa o el vencimiento, falta una página o se usa una revisión anterior. Los PDF del piloto son documentos textuales sintéticos con campos delimitados. La extracción de formatos reales sigue pendiente.

## Reproducción en el VPS

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_construction_pdf_D157.py --output /tmp/miniuw-d157
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d157 \
  --current-revision templates/synthetic-workbook-current-revision-D157.json
```
