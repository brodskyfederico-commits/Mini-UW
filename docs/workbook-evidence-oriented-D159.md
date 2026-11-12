# D159 · OCR de cotizaciones y documentos bancarios girados y recortados

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

Los totales se calculan antes de redondear. Con evidencia visible y coincidente, los flujos y la capacidad reproducen D158. El dictamen real queda PENDING.

## Páginas y controles

| Fuente de `Evidence.pdf` | Giro horario PDF | Evidencia |
|---|---:|---|
| p. 2 · Crédito de obra Downside | 270° | C51–C53, compromiso, giro, vencimiento y convenciones |
| p. 3 · Préstamo permanente Downside | 180° | C69–C72, principal, frecuencia y vencimiento |
| p. 4 · Cotización de obra | 90° | Área e importes verticales para Base y Downside |
| p. 5 · Crédito de obra Base | 180° | C51–C53 y condiciones complementarias |
| p. 6 · Préstamo permanente Base | 270° | C69–C72 y condiciones complementarias |

B03 y B08 orientan cada imagen según los metadatos de página y aplican el recorte PDF a los píxeles visibles. El expediente conserva el ángulo, el rectángulo del recorte, los renglones con regiones de píxeles y las huellas de la imagen original, orientada y usada en OCR. La lectura completa sirve como control de que el recorte haya conservado los renglones y sus regiones. Los valores válidos proceden de la lectura visible. Cuando hay texto superpuesto, ambas lecturas deben estar completas y coincidir.

| Ensayo | Resultado |
|---|---|
| Cinco páginas giradas con todos los renglones visibles | Se reproducen la capacidad y los cobros. |
| Capa de texto coincidente y otra página girada sin recorte | Se registra el cotejo y se reproducen los cobros. |
| C72 oculta por el recorte con texto superpuesto completo | Downside queda PENDING y Base conserva su cálculo. |
| Importe de la cotización truncado | Los escenarios dependientes de la cotización quedan PENDING. |
| Tasa del préstamo Base de 5 % en la imagen y 6 % en el texto | Base queda PENDING y Downside conserva su cálculo. |
| Encabezado oculto por el recorte | B03 deja el paquete PENDING por identidad sin verificar. |
| Recorte con borde fuera de la grilla de píxeles | PENDING por geometría de recorte sin soporte. |

El perfil cubre escaneos sintéticos en escala de grises con orientación declarada en el PDF y recortes alineados a píxeles. Los escaneos de otros formatos y la validación con documentos reales siguen pendientes.

## Reproducción en el VPS

B16 vuelve a leer el PDF guardado. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_evidence_oriented_D159.py --output /tmp/miniuw-d159
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d159 \
  --current-revision templates/synthetic-workbook-current-revision-D159.json
```
