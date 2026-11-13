# Si invierto USD 10, ¿cuánto cobro y cuándo?

El piloto sintético con la plantilla compatible reproduce los flujos de D174. Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales, cobra USD 6,08 hasta el 30/06/2029 y conserva USD 12,11 sin recuperar. Las fechas de los aportes, la refinanciación, la operación y la venta se detallan en la salida del piloto. La decisión real queda PENDING.

## Revisión del flujo

Fuente «MiniUW_Revision_Flujo_Dots_y_Bots.pdf», SHA-256 `809a3446998c449e0bab0ead28f27832ea46eda26018f211c9e24f4eda1aa2b6`.

| Observación y ubicación | Evidencia vigente y estado |
|---|---|
| Carril humano · p. 1, ítem 1 | [D165](review/MiniUW_Flujo_Dots_y_Bots_para_Lorena_D165.md) documenta los responsables, la revisión financiera y la aprobación. La guía identifica el trabajo de Lorena y distingue la reproducción técnica B16. La aprobación real sigue PENDING. |
| Mercado, seguro y términos bancarios · p. 1, ítem 2 | [D166](workbook-market-evidence-D166.md) valida comparables de renta, absorción, concesiones, cap de salida, seguro y términos del banco para el expediente sintético. |
| Reparto y ejemplo por USD 10 · p. 1, ítems 3 y 5 | [D167](workbook-return-metrics-D167.md) verifica la TIR anual del caso D166. [D170](workbook-gp-catch-up-D170.md) prueba el reparto. [D173](workbook-formula-review-D173.md) corrige el CoC y la salida, e incorpora el múltiplo junto al cobro. Los términos de reparto y el equity retenido reales siguen PENDING. |
| Precio pedido frente a RLV · pp. 1–3 | D126 prueba una grilla sintética de precio soportado por dos métricas. El RLV de la casa conserva el conflicto SRC-03. |
| B08 antes de B09, B17 en calidad y estados por etapa · p. 2 | D165 documenta estos cambios. La corrida documentada de D166 registra el orden y el estado de cada escenario. |
| IDs de campo y versión de la plantilla · p. 2 | **D176** vincula los 55 IDs al esquema de la hoja, al hash del catálogo y a una declaración de versión por escenario. B04 coteja tanto la versión declarada como la geometría, etiquetas y unidades del XLSX. |
| Criterios, refinanciación, métricas y lenguaje de dictamen · p. 3 | Se conserva PENDING para banda intermedia, faltantes y discrepancias. Los límites LTV/DSCR y los criterios de inversión se registran por separado. Debt yield queda PENDING hasta contar con base, mínimo y aplicabilidad bancaria. |
| Florida, impuestos personales y pruebas reales · p. 4 | [D173](workbook-formula-review-D173.md) distingue impuesto escolar y no escolar del comprador. [D174](workbook-supplemental-scope-D174.md) registra la aplicabilidad de Live Local. Los cobros sintéticos se muestran antes de impuestos personales. La validación con proyectos cerrados, documentos reales y corrida en paralelo requiere fuentes y autorización. |

## Contrato de B04

El perfil v27 exige `native_mapping.scenarios.<escenario>.template` con `version` y `layout_sha256`. La huella cubre la especificación JSON canónica de la hoja. B04 verifica la huella del XLSX, coteja la identidad de la plantilla y valida la estructura efectiva del archivo. El expediente incorpora la declaración en la huella de su revisión financiera. El catálogo mantiene los IDs originales y la trazabilidad hasta la celda exacta.

La prueba conserva Base ante cinco fallos de Downside. Faltante de declaración, versión desconocida, huella distinta, cambio de unidad y traslado de un valor fuera de su fila dejan PENDING antes de entregar filas al cálculo. La plantilla original se verifica por su propia huella. B16 vuelve a ejecutar la corrida compatible desde sus fuentes. Un futuro diseño necesita su propio mapa revisado.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_template_version_D176.py --output /tmp/miniuw-d176
```
