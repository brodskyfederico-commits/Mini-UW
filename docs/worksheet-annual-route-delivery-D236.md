# Si invierto USD 10, ¿cuánto cobro y cuándo?

D236 exporta el PDF sintético de una página de la ruta anual D234 seleccionada en el cotejo D235. El calendario, los aportes, los cobros, la TIR y el cash-on-cash se toman de esa ruta. El PDF identifica la revisión auditada y deja el dictamen real y los retornos histórico y personal en PENDING.

| Escenario | Aporte adicional | Cobro de refi | Cobro de venta | Cobro total | Sin recuperar |
| --- | ---: | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,03 el 30/09/2028 | USD 13,68 el 30/09/2029 | USD 16,92 | USD 0,00 |
| Downside | USD 8,32 | USD 1,64 el 30/03/2029 | USD 3,08 el 30/03/2030 | USD 4,94 | USD 13,38 |

La página también muestra los cobros trimestrales y el aporte operativo de Downside el día de la venta, como movimientos separados. Los importes se redondean luego de sumar cada categoría. El PDF de la ruta principal del expediente conserva su salida original. El recibo identifica la huella de la página anual en `annual_pdf.sha256` y la de la página archivada en `pdf_sha256`.

## Reproducción y vigencia

```sh
PYTHONPATH=src:tools python3 tools/lorena_screening.py rehearse-workbook \
    criterios-lorena.json expediente --current-revision vigente.json \
    --route annual_hold_with_refinance --annual-pdf MiniUW_Ruta_Anual.pdf
```

La exportación exige un destino nuevo fuera del expediente, una revisión vigente y caja anual disponible en ambos escenarios. En expedientes con control D219 también exige que el cotejo de evidencia crítica esté aprobado. Vuelve a comprobar los archivos fuente y la revisión designada al publicar el PDF. Los resultados del cotejo de umbrales se conservan en el recibo.

La prueba `test_worksheet_lorena_annual_route` concilia todos los movimientos visibles y comprueba el bloqueo ante un cambio de revisión después de renderizar. `test_worksheet_delivery_snapshot_D227` verifica el mismo control de integridad para la entrega original.
