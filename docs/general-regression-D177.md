# Si invierto USD 10, ¿cuánto cobro y cuándo?

Con el expediente sintético D174, Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales y cobra USD 6,08 hasta el 30/06/2029. Quedan USD 12,11 sin recuperar en Downside. El [piloto D174](workbook-supplemental-scope-D174.md) detalla las fechas y desglosa refi, operación y venta. D176 reproduce las mismas cifras cuando B04 verifica la plantilla compatible.

| Prueba en el VPS | Resultado |
|---|---|
| Batería unitaria general sobre D174 | 1.619 aprobadas |
| Integridad y referencias | 26 suites aprobadas sobre D174 y nuevamente sobre D176 |
| Integración por USD 10 | Dos casos con flujos conciliados, seis pruebas de recuperación, dos entradas bloqueadas y nueve pruebas de financiación |
| Planilla de revisión profesional | 55 campos cotejados con D139 y ocho complementarios. Se comprobaron los filtros, el menú de dictamen, los conteos y los espacios de respuesta vacíos. |
| Vacíos y ceros · D171 | 440 ensayos de vacío y 110 ceros explícitos. Un campo aplicable vacío conserva PENDING. El motor conserva el cero en los campos numéricos y rechaza su uso en campos textuales. |
| Fórmulas corregidas · D173 | CoC del tramo con capital remanente documentado, impuesto del comprador en el NOI de salida, conciliación de cobros y ejemplo LP/GP. Seis variantes PENDING. |
| Datos complementarios · D174 | Venta, vencimiento, costos fijos, estrés bancario y alcance Downside. Siete variantes PENDING. |
| Plantilla versionada en B04 · D176 | Reproducción B16 de la corrida compatible y cinco variantes PENDING. Se cotejaron los hashes de 141 archivos del motor base, 103 de pruebas unitarias y el manifiesto de dependencias con D174. |

El [registro técnico](general-regression-D177.json) identifica los árboles, las herramientas, los resultados y las huellas de los logs. El ensayo de recuperación con comisión sin límites y tope cero, que había reportado un error intermitente en la corrida interrumpida, pasó en la batería general. La verificación se ejecutó con datos sintéticos en el VPS. Decisión real PENDING.

## Comandos

Desde el árbol verificado, con las [dependencias de referencia](../requirements-reference.txt) y el [runtime OCR](workbook-plan-scan-D131.md).

```bash
PYTHONPATH=src python3 -u -m unittest discover -s tests -v
python3 tools/check_reference_package.py
python3 tools/check_integral_miniuw_D102.py
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_blanks_and_zero_D171.py
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_formula_review_D173.py
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_scope_D174.py
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_template_version_D176.py
```
