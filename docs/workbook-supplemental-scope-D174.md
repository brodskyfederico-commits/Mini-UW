# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el caso sintético, Base cobra **USD 18,06** por USD 10 iniciales y Downside **USD 6,08**. Base incluye USD 10.000 de costos fijos de cierre para todo el proyecto. Downside declara explícitamente USD 0 de costos fijos. Cada escenario usa sus propios datos, fechas y fuentes.

| Por USD 10 iniciales de equity del proyecto | Base | Downside |
|---|---:|---:|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Refi neta | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Operación al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Venta neta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Cobro total | **USD 18,06** | **USD 6,08** |
| Saldo sin recuperar al cierre | USD 0,00 | USD 12,11 |

El primer aporte se hace el 30/03/2027. Las cifras se redondean después del cuadre. El expediente conserva FAIL simulado y la decisión real queda PENDING.

## Cotejo con la revisión profesional

«MiniUW_Revision_Planilla_55_Campos.pdf», pp. 1–2, SHA-256 `ed095c398b482fac1e812fdc85406adfc016da75e02d4406bdbdfa8e0ab36f4a`. Se verificó el archivo D172 antes de editar. Los autofiltros ya estaban presentes en los rangos A4:J59 y A4:K59. Se comprobaron los rangos nuevamente en D174. El PDF cruza algunas referencias en la descripción de la columna G. En el XLSX original C47 trata la absorción, C67 el cap de salida, C13 otros ingresos y C15 las concesiones. Se conservaron esas correspondencias.

| Comentario | Ubicación en el Excel D174 | Conexión y control |
|---|---|---|
| Horizonte / fecha de venta · p. 1, ítem 1 | Complementarios H01 · fila 5 | M7-01 requiere una fecha y fuente por escenario. La usa el calendario de venta. El perfil actual admite el cierre tras la primera cuota permanente y su ventana de operación estabilizada de doce meses. Un horizonte fuera de este perfil queda PENDING. |
| Vencimiento permanente · p. 1, ítem 2 | H02 · fila 6 | M6-07 exige cantidad de cuotas y evidencia. Se concilia con el término bancario y el calendario. La amortización de C70 sigue siendo un dato distinto. |
| Live Local · p. 1, ítem 3 | H03–H05 · filas 7–9 | M2 captura aplicabilidad, unidades/porcentaje y niveles AMI para revisión. El piloto sólo calcula con una declaración explícita de no aplicabilidad. Si aplica o falta evidencia, queda PENDING para verificar el programa, los términos y las fuentes. |
| Downside integrado · p. 2, ítem 4 | H06 · fila 10 | El expediente enlaza la definición de Downside con las huellas de ambos XLSX. Se documentan conjuntamente los supuestos de Downside y su origen. C80–C82 siguen siendo alternativas individuales. |
| Costos fijos de venta · p. 2, ítem 5 | H07 · fila 11 | M7-06 agrega el monto documentado a los costos variables C68, con referencia de no solapamiento. Cero explícito válido. |
| Vacancia adicional del banco · p. 2, ítem 5 | H08 · fila 12 | M6 añade la fracción documentada a la vacancia base C14 sólo para el NOI bancario y el límite DSCR. Cero explícito válido. |
| Millage y seguro de obra · p. 2 | Trazabilidad C40 y C61–C62 | Continúan como asuntos de sus fuentes y contratos. D173 conserva separados los componentes del impuesto del comprador. El alcance real del seguro de obra se coteja con el presupuesto. |
| Conteos, correcciones y valores · p. 2 | Guía · filas 6–16 | Conteos calculados desde «55 campos». Una propuesta de corrección sigue abierta hasta aceptarse en otra revisión. La Guía indica dónde cargar valores por escenario y dónde registrar definiciones y evidencia. |

La [planilla editable](review/MiniUW_Planilla_55_Campos_Revision_Profesional_D174.xlsx) mantiene los 55 IDs, rangos y unidades originales. Los campos complementarios recogen datos y fuentes por escenario para trasladar al expediente estructurado. Los dictámenes de la planilla de revisión no autorizan una corrida real.

## Prueba reproducible

El perfil sintético de planilla v26 incorpora los campos complementarios en la huella de la revisión financiera. La prueba usa los XLSX y documentos sintéticos anteriores, coteja el impacto de los costos fijos en la venta, prueba el cero explícito del ajuste bancario y comprueba siete bloqueos de alcance. B16 reproduce la salida con la revisión vigente. Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_scope_D174.py --output /tmp/miniuw-d174
```
