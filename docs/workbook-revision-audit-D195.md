# Vigencia del expediente Mini-UW

La auditoría B16 reproduce el expediente desde sus archivos y verifica la revisión vigente por separado. El estado **VIGENTE** exige que el expediente coincida con la revisión designada y que el Excel de criterios corresponda a la huella y versión declaradas. El resultado de la auditoría registra los motivos en `revision_blockers`.

| Caso | Vigencia | Dictamen actual |
| --- | --- | --- |
| Expediente y Excel de criterios coinciden con la revisión designada | VIGENTE | Se reproduce el resultado del ensayo |
| Una corrida válida queda atrás cuando avanza la revisión designada | HISTORICO | PENDING |
| Expediente con reglas distintas de las designadas | PENDING | PENDING |
| Falta el Excel, cambian sus bytes o declara otra versión | PENDING | PENDING |
| Falta la revisión, o el archivo de designación es inválido | PENDING | PENDING |

El expediente sintético de D194 conserva los cobros agregados por USD 10 iniciales de **USD 18,06 en Base** y **USD 6,08 en Downside**. Los bloqueos de vigencia dejan disponibles los flujos conciliados para revisión. El piloto real sigue PENDING.

Con el [entorno OCR del VPS](workbook-plan-scan-D131.md), la prueba reproduce el expediente completo y vuelve a auditar las variantes.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_revision_audit_D195.py
```

[Registro de verificación](review/MiniUW_Verificacion_D195.json) · [Expediente de referencia](workbook-lorena-screening-D194.md)
