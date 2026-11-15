# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el perfil integral sintético v33, la caja, los escenarios de calendario y el dictamen consumen resultados que pasaron el [cotejo D219](workbook-critical-evidence-audit-D219.md). La revisión registra la huella del inventario independiente de 48 datos. D219 coteja las lecturas de los bots y los vínculos efectivamente usados por cada cálculo candidato antes de que sus resultados pasen a las métricas, el dictamen o el informe.

| Cotejo | Cálculo y entrega |
| --- | --- |
| Los 48 datos tienen respaldo | Base y Downside conservan montos y fechas del perfil fiscal v32. B16 reproduce la corrida y el comando de entrega puede publicar el PDF de una página de la revisión designada. |
| Un falso verde en el DSCR de Downside | Se detecta la cita faltante de B08. Se retiran la capacidad, el NOI, la venta, el retorno por USD 10 y las métricas dependientes de Downside. Base conserva su caja íntegra. El dictamen simulado y la entrega quedan PENDING. |
| Una cita inválida de área compartida entre ambos escenarios | Se retiran los resultados dependientes en ambos escenarios. El auditor conserva los motivos por dato y por bot. |
| Respaldo incompleto o revisión incompatible | Los cálculos afectados quedan PENDING. Cambiar la huella registrada del inventario requiere una nueva revisión. |

El expediente interno conserva el registro critical_evidence_review, con sus hallazgos y escenarios afectados. Si el cálculo queda PENDING, el expediente guarda una página interna de diagnóstico. El comando de entrega vuelve a ejecutar el cotejo con B16 y sólo publica el PDF integral cuando la revisión está vigente, el cotejo documental pasa y ambos flujos por USD 10 están disponibles.

El perfil v33 usa el inventario sintético documentado por D219. Para otras muestras se requiere un inventario de referencia independiente. Los perfiles archivados v31 y v32 conservan su reproducción original. El dictamen real y el retorno histórico siguen PENDING.

## Reproducción

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio:

~~~bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_critical_evidence_gate_D220
~~~

Para el ingreso desde archivos, usar la [configuración sintética D203](../templates/synthetic-florida-tax-settings-D203.json) con el esquema miniuw.synthetic-native-rental-inputs.v33. El comando run de worksheet_intake_D198.py registra la huella del inventario D219 al armar el expediente. El uso de audit y deliver con una revisión designada fuera del expediente sigue el [flujo integral](worksheet-technical-acceptance-D200.md#entrega-vigente-del-informe-integral).
