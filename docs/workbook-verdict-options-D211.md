# Dictamen y aplicabilidad del RLV en Downside

El verificador D211 usa los XLSX y PDF sintéticos de D194. Genera el expediente de control por la misma entrada que el Mini-UW, verifica la revisión mediante B16 y repite la evaluación con cambios limitados al Excel de criterios. Cada corrida conserva el resultado financiero Base y Downside completo, incluidos los importes y fechas por cada USD 10 iniciales.

| Caso | Regla vigente | Alternativa en revisión |
| --- | --- | --- |
| Todos los criterios aplicables cumplen | PASS | PASS |
| Base cruza un umbral de FAIL y no hay bloqueos | FAIL | FAIL |
| Base cruza un umbral de FAIL y Downside incumple un PASS sin umbral de FAIL | PENDING | FAIL |
| Banda intermedia, criterio faltante, fuente faltante o revisión desactualizada | PENDING | PENDING |

La alternativa probada sólo da prioridad al FAIL de Base sobre un PASS de Downside evaluado e incumplido. Mantiene el bloqueo ante evidencia incompleta, banda y aplicabilidad sin confirmar. Los dos resultados son de simulación.

Si el RLV es aplicable en Downside, la prueba exige los criterios y la evidencia de la métrica. Para ensayar N/A se usa una declaración sintética explícita. La exclusión sin respaldo queda PENDING. Excluir Downside mantiene la revisión del RLV de Base y los demás criterios. Se prueba la igualdad y el incumplimiento del umbral RLV usando el comparador de Downside del motor sobre el RLV calculado en el expediente de control. Las variantes de alcance y precedencia se prueban en el verificador, con la decisión real en PENDING.

## Reproducción en el VPS

Configurar el [runtime OCR fijado](workbook-plan-scan-D131.md).

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python tools/check_worksheet_verdict_options_D211.py --output /tmp/miniuw-d211
```

El directorio de salida contiene el paquete de control y `verification.json`, con la matriz de resultados y las huellas del flujo sintético completo por escenario.
