# Si invierto USD 10, ¿cuánto cobro y cuándo?

La reproducción del expediente sintético D181 conserva estos importes y fechas. Son flujos de equity agregado del proyecto, antes de impuestos personales.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aporte inicial · 30/03/2027 | USD 10,00 | USD 10,00 |
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro operativo al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Total cobrado | USD 18,06 | USD 6,08 |
| Sin recuperar al cierre | USD 0,00 | USD 12,11 |

El [PDF de una página](review/MiniUW_Informe_USD10_D181.pdf) se reprodujo byte por byte. El dictamen real, el reparto personal y la aprobación de las definiciones siguen PENDING.

## Bases comparables y ocupación

| Requisito | Fuente exacta | Definición ensayada y parte afectada | Evidencia y estado |
| --- | --- | --- | --- |
| NOI_uw para YoC y CoC | Devolución SRC-02/SRC-03, p. 1, «Reservas de reposición». Confirmación posterior, «YoC con NOI_uw» y mapa de bases | B13 calcula un NOI de underwriting con C60 × unidades elegibles y factores C76 de la ventana. Divide el NOI anual por el TDC conciliado para YoC. Para CoC usa el NOI y las reservas del tramo posrefi, menos servicio del tramo, sobre equity remanente. | JSON, `performance`. Comparación exacta contra el expediente y prorrateo sintético. Adopción PENDING. |
| Spread con la misma base de NOI | Confirmación posterior, «La condición: el spread» | B13/B14 conservan el YoC de underwriting. Si el cap usa NOI antes de reservas, el spread usa el YoC antes de reservas sólo en esa comparación. Una base ausente deja PENDING el spread. | JSON, `performance/*/spread_by_basis`. Se prueban ambas bases y una base ausente, por escenario. |
| NOI bancario y valoraciones | Confirmación posterior, «Las valoraciones no se tocan» | M6 conserva NOI bancario según el término bancario y su tratamiento de H08 y reservas. La refi y la venta usan la base de evidencia de su cap. | El ensayo lee fuentes y reproduce los resultados D181 de caja, deuda y valoración. Registra sus referencias junto a las métricas candidatas. |
| Ocupación económica y física | Devolución, p. 1, «Reservas», «Servicio de deuda» y «Conversión a física». Confirmación posterior, último caso de borde | M2-08 compara NOI después de reservas con servicio amortizante anual. Bajo la base fiscal antes de reservas del ensayo, el objetivo previo a la reserva es deuda más reserva. Conversión física sólo con pérdida de crédito y concesiones separadas. | JSON, `occupancy`. Cinco casos, con piso fiscal, rama proporcional, cero explícito, C14 sin desglose y física superior a 100 %. SRC-02 PENDING. |

El ensayo usa factores mensuales derivados de las ventanas de D181 para aplicar C76. Distribuye la reserva anual entre los meses cubiertos para construir el NOI candidato. Es una convención sintética de medición. La reserva descontada de la métrica y el depósito de caja restringida se registran por separado. Cuando el coeficiente de impuesto opera sobre NOI **antes** de reservas, se usa `X = servicio + reserva` y el impuesto en el cruce es `max(piso, k × X)`. El ensayo coteja el cruce con la solución de NOI y un punto inmediatamente inferior.

| Métrica candidata | Base | Downside |
| --- | ---: | ---: |
| NOI_uw anual | USD 408.737,68 | USD 199.068,85 |
| YoC con NOI_uw | 9,72 % | 3,94 % |
| CoC del tramo posrefi con NOI_uw, sin anualizar | 10,22 % | 0,26 % |
| Spread con cap sintético del 7 % después de reservas | +272,47 pb | −305,92 pb |
| Spread con cap sintético del 7 % antes de reservas | +347,81 pb | −200,66 pb |
| Spread con base del cap ausente | PENDING | PENDING |

El 7 % es un valor de prueba declarado por base. No se aplica como cap de mercado ni como conversión entre bases. En el ensayo separado de ocupación, C14 combinado permite mostrar 48 % de ocupación económica y deja la física PENDING con motivo `C14_sin_desglose`. El cálculo sintético usa servicio amortizante fijo. El tratamiento de interés solo y tasa variable requiere la evidencia anual del préstamo.

## RLV en una grilla sintética con deuda fija

La devolución, pp. 1–2, y la confirmación posterior especifican el criterio conjunto, el cierre de terreno y las fronteras. En la grilla se ajustan TDC y equity por `ΔP × (1 + C33)`. Se comparan simultáneamente YoC o spread, TIR, múltiplo de equity y máximo de equity/TDC. DSCR, debt yield y ocupación permanecen fuera de la búsqueda de precio de este perfil. El valor de Downside es informativo. Es una grilla independiente de los flujos D181 y sus precios son USD sintéticos de terreno.

| Ensayo | Máximo en PASS | Último precio antes de FAIL | Evidencia |
| --- | ---: | ---: | --- |
| Base con C33 = 0 % | USD 200 | USD 266 | Equity/TDC es vinculante. USD 201 queda PENDING en la banda. |
| Base con C33 = 5 % | USD 195 | USD 258 | La deuda queda fija. USD 196 queda PENDING en la banda. |
| Equity/TDC más restrictivo | −USD 37 | −USD 16 | Resultado firmado con bandera. Precio pedido/RLV queda sin valor. |
| Ningún punto cumple | PENDING | PENDING | No alcanzable en la grilla declarada. |
| TIR vinculante | USD 148 | USD 157 | El criterio de TIR deja USD 149 en la banda. |
| Cap después / antes de reservas | USD 133 / USD 166 | USD 171 / USD 207 | Dos casos con spread vinculante y base declarada. |
| Downside informativo con C33 = 5 % | USD 183 | USD 236 | Conserva los criterios del ensayo y usa sus flujos. |

La prueba guarda el punto anterior, el límite y el siguiente punto para cada frontera disponible. Al cruzar el máximo PASS puede aparecer PENDING. Al cruzar el límite previo a FAIL debe fallar al menos una métrica. Se verifica el orden de los estados por métrica en todos los puntos de la grilla. Para TIR se exige un solo cambio de signo de negativo a positivo, con equivalencia trimestral exacta de las tasas anuales del ensayo. Una serie con más de un cambio de signo o un cap sin base bloquean su cálculo de RLV. Un límite en el extremo superior queda sin resolver. Los máximos corresponden a una grilla acotada con paso de USD 1. La aprobación SRC-03 y su activación en el dictamen siguen PENDING.

## Reproducción y fuente

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_performance_policy_D184.py
```

[Resultados exactos y trazabilidad](review/MiniUW_Verificacion_D184.json). Fuente documental «MiniUW_Definiciones_SRC02_SRC03.pdf», pp. 1–2, SHA-256 `1f81b2cf28a81e6e91404e901eec40b7dd6ea1ea63cce7ab7429611345efb931`, y confirmación posterior de la condición de consistencia, las bases y los casos de borde. Ver [pendientes SRC-02 y SRC-03](requirements-conflicts.md) y [política de banda intermedia](pending-band-policy-decision.json).
