# Si invierto USD 10, ¿cuánto cobro y cuándo?

Con los límites bancarios del caso sintético principal, Base y Downside conservan los flujos de D176. El 30/03/2027 ambos parten de un aporte inicial de USD 10. Las fechas de cada aporte adicional quedan en el expediente de cálculo.

| Por USD 10 de equity inicial del proyecto | Base | Downside |
|---|---:|---:|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Refi neta | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Operación al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Venta neta | USD 13,78 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Cobro total | **USD 18,06** | **USD 6,08** |
| Múltiplo sobre todos los aportes | 1,21x | 0,33x |
| Sin recuperar al cierre | USD 0,00 | USD 12,11 |

Importes antes de impuestos personales, redondeados después del cuadre. Retorno personal y decisión real PENDING.

## Control bancario de refinanciación

El PDF «MiniUW_Revision_Flujo_Dots_y_Bots.pdf», p. 3, ítem 5, identifica *debt yield* como pendiente de M6. La copia aportada coincide con la de D176 (SHA-256 `809a3446998c449e0bab0ead28f27832ea46eda26018f211c9e24f4eda1aa2b6`).

El perfil sintético v28 agrega un anexo bancario estructurado por escenario. B08 coteja el identificador del term sheet y la huella del PDF. La revisión del expediente vincula el anexo exacto. La condición se calcula sobre el NOI bancario anual de M6 y el principal bruto solicitado. El mínimo debe ser positivo cuando aplica. Una declaración de no aplicabilidad requiere fuente y mínimo vacío.

- **Debt yield** = NOI bancario anual ÷ principal bruto.
- **Principal máximo por debt yield** = NOI bancario anual ÷ mínimo documentado.
- **Capacidad bancaria** = menor de LTV, DSCR y debt yield cuando aplica. La igualdad con el límite admite el importe solicitado. El informe retiene los límites vinculantes en caso de empate.

La prueba usa un préstamo solicitado de USD 1.400.000 en cada escenario. Base registra 29,87 % de debt yield frente a un mínimo sintético de 10 %. Downside registra 16,75 % frente a un mínimo sintético de 15 %. Con un mínimo de 18 % en la variante Downside, el tope baja a USD 1.302.945,03. La corrida retira los flujos de ese escenario y conserva Base. La misma corrida deja **PENDING** la simulación. Los mínimos del ensayo pertenecen al anexo sintético. Un caso real necesita la regla y la fuente vigentes del banco.

B16 reproduce el expediente y el PDF de una página. Se comprueban igualdad, no aplicabilidad explícita, falta de anexo o mínimo, mínimo cero, cotización incompatible, base errónea y revisión desactualizada. El texto del anexo viene del JSON sintético y no forma parte del OCR del term sheet.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_debt_yield_D178.py --output /tmp/miniuw-d178
```
