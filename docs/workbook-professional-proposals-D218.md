# Si invierto USD 10, ¿cuánto cobro y cuándo?

Las propuestas de dictamen conservan cada movimiento por USD 10 iniciales, con su fecha y monto en Base y Downside. La prueba compara la caja exacta contra el control reproducido por B16. Los ejemplos usan el expediente sintético D194 con un XLSX de criterios de ensayo.

## Propuestas ensayadas

| Caso | Resultado de la propuesta |
| --- | --- |
| Downside sin disposición especial para RLV | N/A para el dictamen. El precio de Downside se conserva como dato informativo si se puede calcular. La métrica y los criterios de Base conservan su alcance. |
| Downside con excepción que exige RLV | Se evalúa si la aplicabilidad está respaldada. La excepción sin confirmar o el criterio requerido faltante mantiene PENDING si no existe un FAIL independiente verificado. |
| Una métrica verificable cruza su umbral de FAIL y otra tiene un dato o criterio faltante, está en banda, o incumple un PASS sin umbral FAIL | FAIL simulado con cada faltante o banda identificados por escenario y métrica. |
| La propia métrica carece de valor, umbral o localizador, o su período difiere del criterio | Esa comparación no sustenta FAIL. El caso queda PENDING si no hay otro FAIL verificado. La igualdad con un umbral estricto no cuenta como cruce. |
| Revisión anterior o bloqueo de integridad del expediente o del contrato de criterios | PENDING. La precedencia sólo se prueba sobre resultados de revisión sintética vigente. |

La precedencia requiere celdas o localizadores de métrica y criterio, unidad y período compatibles, y un cruce verificable con los operadores y valores exactos. Se ensayaron las omisiones de criterios desde el XLSX sintético. Los controles focalizados de evidencia alterada y faltantes de métricas usan copias en memoria del resultado. El verificador mantiene visibles los bloqueos y coteja que las propuestas no muten el resultado de la corrida. Las reglas siguen pendientes de adopción formal y el dictamen real sigue PENDING.

La escala del informe se interpreta con el aporte inicial agregado como denominador, el factor exacto y los aportes posteriores por separado. El total de aportes modelados y un compromiso contractual de equity son cantidades con soportes diferentes. Las cifras y el documento privado del proyecto quedan en el VPS.

## Reproducción

Con el [runtime OCR fijado configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_professional_proposals_D218
```
