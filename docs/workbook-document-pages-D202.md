# Mini-UW v1 · Auditoría de páginas requeridas

Por cada **USD 10 iniciales**, el caso completo registra USD 18,06 de cobros en Base y USD 6,08 en Downside. La auditoría mantiene disponible la caja sintética de los escenarios cuyos insumos financieros se verificaron. [Informe por fecha](review/MiniUW_Informe_USD10_D200.pdf)

En v31, B16 verifica tanto el PDF registrado como el resultado de lectura de las páginas requeridas. Si una página falla, identifica archivo, hoja o rol y motivo. La vigencia y el dictamen quedan PENDING. Cuando falla el PDF completo, la auditoría conserva el motivo de archivo de D201.

| Página faltante en un PDF registrado | Evidencia de B16 | Caja disponible |
| --- | --- | --- |
| A601 del plano | `Plan.pdf:A601:required_sheet_missing` | PENDING en ambos escenarios |
| Préstamo bancario de Downside | `Evidence.pdf:bank_Downside:evidence_page_role_missing` | Base conserva USD 18,06; Downside PENDING |
| Copia del registro oficial | `Evidence.pdf:official_snapshot:evidence_page_role_missing` | Base conserva USD 18,06 y Downside USD 6,08; el dictamen sigue PENDING |

La prueba registra cada PDF sintético con su propia huella y conserva los importes y fechas de los escenarios disponibles. La decisión real y el piloto siguen PENDING. Desde una copia limpia con las dependencias y el entorno OCR de D200:

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 tools/check_worksheet_document_pages_D202.py
```

[Resultados de ejecución](review/MiniUW_Verificacion_D202.json)
