# D155 · Alternativas solicitadas en C80–C82

## Si invierto USD 10, ¿cuánto cobro y cuándo?

Importes en USD por cada USD 10 iniciales del equity agregado. Cada alternativa sintética parte de su propio escenario de origen.

| Variante | Base · aporto | Base · cobro total | Base · sin recuperar | Downside · aporto | Downside · cobro total | Downside · sin recuperar |
|---|---:|---:|---:|---:|---:|---:|
| Origen D154 | 14,87 | 19,10 | 0,00 | 18,19 | 6,80 | 11,39 |
| C80 · Cap de salida del 8 % en Base y 11,5 % en Downside | 14,87 | 21,00 | 0,00 | 18,19 | 6,00 | 12,19 |
| C81 · Costo de venta del 0 % en ambos | 14,87 | 19,94 | 0,00 | 18,19 | 7,50 | 10,69 |
| C82 · Crecimiento de renta del 4 % en Base y −12 % en Downside | 14,87 | 19,31 | 0,00 | PENDING | PENDING | PENDING |

El 30/03/2027 se aportan los USD 10 iniciales. Los aportes posteriores suman USD 4,87 en Base y USD 8,19 en Downside. Para las alternativas calculadas, Base cobra USD 2,85 al refinanciar el 30/09/2028 y USD 1,43 de operación el 30/12/2028. Downside cobra USD 2,45 al refinanciar el 30/03/2029 y USD 0,55 de operación el 30/06/2029. El cobro por venta cambia según el reemplazo solicitado. El PDF muestra los aportes por fecha y el expediente conserva todos los movimientos fechados por alternativa.

| Cobro neto de venta | Base · 30/12/2028 | Downside · 30/06/2029 |
|---|---:|---:|
| Origen D154 | 14,82 | 3,81 |
| C80 | 16,72 | 3,00 |
| C81 | 15,66 | 4,51 |
| C82 | 15,03 | PENDING |

Los totales se calculan antes de redondear. C82 en Downside reduce la capacidad a USD 1.260.726,37 por DSCR frente al préstamo solicitado de USD 1.400.000. La alternativa queda PENDING y se retienen sus flujos dependientes. El origen conserva su propio resultado sintético y el dictamen real queda PENDING.

## Conexión y evidencia

| Ubicación | Tratamiento sintético | Evidencia |
|---|---|---|
| `Inputs!A80:F80` · Alternative 1 | La solicitud confirmada reemplaza C67 de su escenario en el piloto. | El NOI de salida se conserva. Se recalculan el precio, el costo porcentual y el cobro neto. |
| `Inputs!A81:F81` · Alternative 2 | La solicitud confirmada reemplaza C68 de su escenario en el piloto. | Se verifica el cero explícito y se concilia la deducción del costo sobre el precio bruto. |
| `Inputs!A82:F82` · Alternative 3 | La solicitud confirmada reemplaza C75 de su escenario en el piloto. | Se recalculan los NOI proyectados, el precio de salida y la capacidad bancaria. La prueba de Downside bloquea el cobro. |

El perfil acepta reemplazos absolutos de C67, C68 y C75 en cualquiera de los tres espacios. B04 coteja el texto con una confirmación estructurada que declara la celda, unidad, valor y fuente. B13 recalcula cada alternativa desde los datos del escenario de origen. El expediente guarda la solicitud, el valor anterior, la referencia de planilla, la revisión y la diferencia por USD 10. B16 vuelve a generar la salida desde las fuentes guardadas. El texto se conserva como evidencia y su lectura se limita al formato definido. Una omisión explícita de un campo opcional se registra como no solicitada. Un dato incompatible, un reemplazo sin confirmar o un expediente desactualizado dejan la alternativa PENDING.

Las alternativas se calculan de forma independiente. Su resultado financiero queda separado de la simulación de los escenarios de origen. La habilitación de otros cambios y la evaluación con datos y reglas vigentes quedan pendientes de sus fuentes y definiciones. [Planilla preservada](../sources/originals/b433468ec6cb__Input_Sheet_vigente_original.xlsx) · [F20 en `/cards/11`](current-structure/MiniUW_Contratos_Financieros_Complementarios_D10.json) · [Contratos M8-01 a M8-07](model-scenarios-price.md).

## Reproducción en el VPS

El verificador coteja cuatro expedientes D155 y reproduce D154 como referencia. [Runtime de OCR](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_alternatives_D155.py --output /tmp/miniuw-d155
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d155 \
  --current-revision templates/synthetic-workbook-current-revision-D155.json
```
