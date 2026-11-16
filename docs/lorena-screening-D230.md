# Criterios de Lorena · ensayo de dictamen D230

La revisión `SYNTHETIC-Lorena-D230.v1` compila las diez métricas y los 29 umbrales definidos en la sección 2 del DOCX original. La receta fija el SHA-256 del DOCX y conserva su fecha literal. Cada umbral compilado incluye operador, valor racional, unidad, base de cálculo y ubicación exacta de su celda. La corrida exige la revisión y el SHA-256 exactos de la configuración compilada.

Los ensayos aplican las bandas de la Política 17 a observaciones ficticias de Base y Downside. PASS se prueba en la igualdad de cada umbral aplicable. FAIL exige cruzar estrictamente un umbral de Base. El RLV aplica a Base en esta configuración conforme a la Política 13. Se compara la prima sobre un RLV positivo. La prueba deja fuera de dictamen las métricas que la estrategia declara inaplicables y conserva los ceros documentados. Upside queda fuera de la comparación conforme a la Política 33.

| Caso ejecutado en el VPS | Dictamen simulado |
| --- | --- |
| Cumplen las 19 comparaciones aplicables | PASS |
| Downside queda debajo de un umbral de PASS con evidencia completa | HOLD · economía insuficiente |
| Falta una métrica material en Downside | HOLD · requiere diligencia adicional |
| Base cruza un umbral de FAIL con evidencia completa | FAIL |
| Base cruza un umbral de FAIL y falta otra métrica material | PENDING · la precedencia sigue por confirmar |

El dictamen operativo y el retorno histórico del 1101 siguen PENDING. El ensayo recibe métricas declaradas en sus unidades y bases. El motor de caja y el PDF por USD 10 conservan el flujo vigente. La adopción de los criterios y la conexión con métricas calculadas requieren validar sus bases y períodos. Por ejemplo, la Política 10 mide el aporte de refi como porcentaje del equity hasta estabilización y la Política 12 pide CoC anual. El ensayo de FAIL cubre el cruce de umbrales. La evaluación independiente de viabilidad al precio o estructura JV actuales requiere una regla aprobada.

## Reproducción

Desde la raíz del repositorio, compilar la receta versionada y ejecutar la batería de criterios.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/lorena_screening.py prepare --output /tmp/criterios-lorena.v1.json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest -v test_lorena_screening test_threshold_rehearsal test_scenario_threshold_rehearsal
```

El SHA-256 de la configuración compilada en el VPS es `784a7fbde15f4eff7e2c098468422a8b55cda61a9f19651cc46ea50c611544db`. Para probar un caso sintético puntual, pasar la configuración compilada y el caso JSON al subcomando `rehearse`. La función `fixture` de la prueba genera los campos requeridos y fija la huella de la configuración. GitHub conserva la receta y su reproducción. La configuración con los valores compilados y los registros de prueba se guardan en el VPS.
