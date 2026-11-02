# DSCR desde NOI y servicio anual equivalente calculados

T20 conecta el productor condicional de NOI T19 con el productor de servicio de deuda T10. Reproduce ambos desde sus fuentes exactas antes de calcular el cociente. El NOI deja de ser únicamente un monto declarado en esta ruta, aunque las partidas y el modelo fiscal siguen siendo entradas sintéticas sin validación financiera.

El perfil `SYNTHETIC-COMPUTED-NOI-ANNUAL-DSCR-v1` consume exclusivamente el equivalente anual regular de sizing. Requiere vínculo explícito con hashes de ambas fuentes y ejecuciones, contexto común, moneda, referencias de período y declaración de que el NOI representa ese equivalente anual. Una coincidencia de etiquetas no acredita el calendario o la base económica; esa evidencia sigue declarada y no verificada.

El cociente es NOI calculado / equivalente anual regular calculado. No representa caja realmente pagada, servicio debido en una ventana fechada ni cobertura del balloon. La selección de perfil es explícita y no acepta un perfil fechado. El préstamo sintético de ejemplo vence tras tres cuotas; calcular su equivalente anual no prolonga su vencimiento ni prueba que se pagará un año de cuotas. Las ventanas y balloon conservan su tratamiento separado de T10.

Fuentes o productores distintos, monedas/períodos incompatibles, ausencia de base anual, NOI bloqueado o servicio no positivo impiden dividir. El resultado conserva los bloqueos de NOI. Un NOI negativo puede generar un cociente negativo matemáticamente definido; eso no produce por sí solo FAIL de inversión.

## Prueba de la cadena

El fixture usa NOI condicional calculado de 1.000 y servicio anual equivalente calculado de 1.200: DSCR exacto 5/6x. Se archivan ambas fuentes, ventanas, parámetros de vínculo y ambos productores junto con el resultado. Al reabrir, se reproduce toda la cadena con versiones compatibles y documentos de definición. No hay mínimo DSCR bancario cargado ni comparación con un criterio de inversión.

Los fixtures de vínculo conservan hashes de las fuentes y de las ejecuciones vigentes al crearlos. Si cambia un productor o documento, deben revisarse y renovarse explícitamente; no se actualizan silenciosamente al calcular. La referencia de base anual del fixture es una declaración sintética, no evidencia profesional.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_computed_noi_dscr.py
```

API: `calculate_operating_dscr`, con `OperatingDscrBinding`, fuente/resultado NOI y fuente/ventanas/resultado deuda. Persistencia: `save_operating_dscr` y `load_operating_dscr`. No se cambia la tabla existente. La transacción es local y las bases runtime están excluidas del repositorio y ZIP.

15 pruebas nuevas cubren el cociente exacto, NOI negativo, parámetro fiscal ausente, productores falsos, vínculos obsoletos, contexto, moneda, período, base anual, servicio ausente/cero/negativo, perfil no soportado, ausencia de aprobación/minimum bancario, recuperación, manipulación y rollback. T19/T20 agregan 36 pruebas: 390 técnicas en total. No cierran M2, M6 o los paquetes financieros, no ejecutan los 36 casos originales de aceptación financiera y no habilitan decisiones reales o despliegue.
