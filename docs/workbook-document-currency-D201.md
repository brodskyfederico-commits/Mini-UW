# Mini-UW v1 · Vigencia del plano y de los respaldos financieros

El mismo caso sintético recupera sus cobros por cada **USD 10 iniciales** cuando se restituyen los documentos registrados. Base requiere USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside requiere USD 8,19 adicionales, cobra USD 6,08 hasta el 30/06/2029 y termina con USD 12,11 sin recuperar. El informe reproduce los aportes y cobros por fecha. [Informe del caso completo](review/MiniUW_Informe_USD10_D200.pdf)

En el perfil v31, B16 exige que B03 haya verificado ambos PDF de origen. La huella declarada en la revisión y las reglas financieras se mantienen fijas durante estas pruebas.

| Caso sintético | Motivo registrado | Vigencia y dictamen |
| --- | --- | --- |
| Plano con bytes modificados | `plan_pdf_hash_or_reference_mismatch` | PENDING |
| Plano ausente | `plan_pdf_missing` | PENDING |
| PDF financiero con bytes modificados | `evidence_pdf_binding_unconfirmed` | PENDING |
| PDF financiero ausente | `evidence_pdf_missing` | PENDING |
| Ambos originales registrados | B03 comprueba las fuentes y B16 reproduce el expediente | VIGENTE · PASS simulado |

El ingreso D198 localiza el archivo afectado y el PDF de salida muestra la caja PENDING de Base y Downside. Al restaurar los bytes registrados se recupera el expediente original, incluidos sus flujos y los resultados de auditoría. La decisión real del piloto sigue PENDING.

Desde una copia limpia con las dependencias y el entorno OCR de [D200](worksheet-technical-acceptance-D200.md), ejecutar:

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 tools/check_worksheet_document_currency_D201.py
```

[Resultados y huellas de la prueba](review/MiniUW_Verificacion_D201.json)
