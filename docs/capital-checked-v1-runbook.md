# Capital declarado y pendientes en la salida Mini-UW

T98 integra la vista de capital, el PDF de una página, el paquete local y su recuperación. Es el flujo sintético recomendado cuando se aportan cortes de capital. Los CLI T95/T97 conservan sus versiones anteriores para reproducir los hitos históricos.

Desde la raíz del repositorio, con las dependencias de `requirements-reference.txt` ya instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/capital_miniuw_v1.py run \
  templates/miniuw-v1-capital-pending-basis-case.json --output /tmp/miniuw-capital-pendiente
PYTHONDONTWRITEBYTECODE=1 python tools/capital_miniuw_v1.py audit /tmp/miniuw-capital-pendiente
```

El ejemplo conserva un corte anterior de1.300 con metadatos y un corte posterior declarado de1.000/900 cuya base está ausente. El PDF presenta el último corte como pendiente: no usa1.300 del corte anterior, no muestra1.000/900 como cifras actuales y no usa622 de déficit de caja como capital remanente. La evidencia interna conserva todas las declaraciones. Los aportes1.400, cobros778 y resultado−622 permanecen iguales.

| Estado del corte suministrado | Vista actual y PDF | Evidencia |
| --- | --- | --- |
| Campos y metadatos completos en el perfil sintético | Valores declarados, sin derivar capital ni sumarlo a cobros | Fuente, base, moneda, fecha y valores conservados |
| Cero explícito con metadatos completos | Cero; no se convierte en ausencia | Declaración cero conservada |
| Capital/valor o base/fuente/moneda incompatibles según T23 | Ambos valores del corte y sus normalizaciones pendientes | Valores originales y bloqueos separados de la vista actual |
| Último corte pendiente y otro anterior con datos | El último sigue pendiente; sin sustitución automática | Historia de ambos cortes conservada |
| Proyección padre retirada por vigencia/cálculo | Todas las cifras actuales retiradas | Recuperación conserva el bloqueo |

Las declaraciones con metadatos completos siguen siendo hipótesis sintéticas. Una cadena de texto como base/fuente no autentica una política, un valor de mercado o una revisión profesional. No se adopta definición financiera de capital; la fecha visible es el corte declarado, sin extrapolarlo al fin del horizonte. Capital remanente, valor retenido, déficit de caja y cobro del inversor mantienen significados separados. CoC, reparto personal y decisiones reales conservan sus pendientes.

`results.json` contiene la vista actual y `capital_source_claims`, que preserva las afirmaciones previas al control. `capital_visibility` explica cada bloqueo; `latest_capital_snapshot_index` identifica el corte presentado. El resultado financiero padre queda ligado por su SHA y es reproducible desde el contenedor. No se deben usar las declaraciones de auditoría como si fueran cifras actuales desbloqueadas.

El directorio contiene exactamente los ocho artefactos del flujo: `case.json`, `results.json`, `execution-evidence.json`, `MiniUW_v1_Resumen.pdf`, `report-manifest.json`, `audit.json`, `schedule-review.txt` y `package.json`. Hay un solo PDF externo; los demás son evidencia interna. Recuperación con código compatible:

```python
from pathlib import Path
from miniuw_foundation.capital_checked_output import recover_capital_checked_bundle

recovered = recover_capital_checked_bundle(
    Path('/tmp/miniuw-capital-pendiente/execution-evidence.json').read_bytes())
assert recovered.run.payload['latest_capital_state'] == 'PENDING'
```

La API requiere `miniuw_foundation` instalado o `src` en `PYTHONPATH`. No se renueva evidencia automáticamente. Los reintentos idénticos se verifican; una salida distinta o incompleta exige otro directorio y no sobrescribe la anterior. El ámbito es local sin concurrencia productiva, con fuente/resultado/PDF reproducidos; no es recuperación de la infraestructura histórica ni auditoría financiera independiente.

[PDF del caso pendiente](review/miniuw-v1-capital-checked-example/MiniUW_v1_Resumen.pdf) · [Validación reproducida](review/capital-output-validation-T98.json) · [Alcance T98](technical-implementation-T98.md).
