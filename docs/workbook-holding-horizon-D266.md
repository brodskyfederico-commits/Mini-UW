# D266 · Horizonte integrado desde estabilización

El perfil optativo `miniuw.synthetic-integrated-holding-horizon.v1` conecta las planillas Base y Downside con compra, obra, estabilización, cinco años completos de operación y venta. Produce cuatro historias de caja por USD 10 iniciales: con y sin refinanciación en cada escenario. Es un ensayo sintético; el dictamen real y el retorno personal sin reparto documentado siguen PENDING. No habilita despliegue.

## Contrato de entrada

Se declara `rent_inputs.holding_horizon`, con perfil, referencia, inventario de reglas y ambos escenarios. Cada escenario necesita `holding_months`, fuente, aporte inicial positivo con fuente, inventario de supuestos de caja, política de fondeo del cierre y alcance de la ruta sin refi. Los meses se reciben como entero explícito de 12 a 60 en años completos: **no hay un default financiero de cinco años**. La venta H07 debe coincidir con estabilización más ese plazo.

El aporte inicial proviene del nuevo contrato. No se sustituye por el importe del fixture: los ensayos incluyen otros aportes respaldados. Un importe que no cubra la compra y comisión de apertura bloquea; un exceso documentado se conserva como caja libre y se concilia en el cierre, sin inventar un aporte negativo. Los perfiles históricos conservan su contrato y resultados.

El calendario soportado tiene compra y pagos en el primer día del trimestre, obra C46 en múltiplos de tres meses, TCO al terminar la obra y estabilización después de C47. La refi ocurre al estabilizar. Se exige operación comercial plenamente reconocida o ausencia documentada de usos comerciales. Una brecha de TCO sin fondeo o un primer año comercial parcial no se aproxima en silencio.

La tasa, frecuencia, amortización, principal, LTV, DSCR, debt yield, vencimiento y cotización de cada deuda tienen su respaldo del expediente. La ruta sin refi retiene la misma deuda de obra sólo cuando su vencimiento documentado cubre la venta; una extensión no se presume. El plazo largo usado en el fixture es un supuesto bancario sintético, no una propuesta de mercado.

## Conexiones y fórmulas

| Dato / requisito | Definición aplicada | Productor y ubicación | Evidencia de validación |
|---|---|---|---|
| D252 #15–16, TEC-01 de D265 | Venta = estabilización + meses documentados. Cinco años son cinco anualidades completas y 20 cierres trimestrales. | `worksheet_holding_horizon_D266.horizon_calendar`; despacho en `worksheet_project_calendar_D145.project_calendar`. | Calendario independiente desde TCO/C47; rechazo de fecha de venta contradictoria, duración ausente y brecha sin presupuesto. |
| Aporte inicial y USD 10 | Factor = 10 / primer aporte verificado. Cada aporte posterior conserva importe y fecha; no se netea con un cobro del mismo día. | `configuration`, `investor_story`; D143, D144 y D146 reciben el importe sólo en el perfil nuevo. | Otras bases iniciales, caja excedente, ceros explícitos y sumas brutas de eventos. |
| Obra y lease-up | Usos, desembolsos, comisión y cada interés hasta estabilización permanecen conciliados por fecha. | D143–D146; `construction_rows`, `verify_rows`. | Ecuación de fuentes/usos por fila y continuidad entre saldos. |
| Rentas, gastos y NOI | C75/C76 se componen en aniversarios de estabilización; C13 permanece plano; fees mantienen su propia base. El impuesto usa el mayor de proxy y comparables del perfil D150. | `worksheet_growth_D154.project_window`; `worksheet_rental_inputs_D140` construye cada año. | Cotejo desde literales XLSX de cinco NOI anuales y el NOI forward del año posterior a la salida. |
| Caja operativa | Bajo regla sintética explícita: NOI anual / 4 − servicio trimestral − reserva anual / 4. Déficits son aportes brutos; superávits son cobros brutos. | `operation_rows`, `annual_aggregate`, `yearly_cash`; conciliación T19/T25. | Fechas y netos de las 20 cuotas, sumas de ingresos/gastos y conciliación de caja libre/restringida. |
| Reservas | C60 se deposita trimestralmente, se acumula sin uso intermedio y se liquida con su fracción documentada. La reserva permanente C74 sigue separada. | D149, `sale_close`, `append_sale`; D153 para reserva permanente. | Total de cinco depósitos anuales, liberación/transferencia sin duplicar el cobro. |
| Deuda permanente y capacidad | Cuota regular con tasa C69/4 y C70×4 períodos. Capacidad = menor límite aplicable. Cancelación del saldo después de la última cuota, una sola vez. | D152 y motores de servicio/capacidad; `calculate`. | 20 intereses, amortizaciones y saldos recalculados independientemente. Préstamo sobre capacidad y vencimiento temprano → PENDING en refi. |
| Venta y deuda sin refi | Precio = NOI del año posterior / C67. Costos = precio×C68 + fijo documentado. Deuda de obra se mantiene sólo hasta su vencimiento acreditado. | `without_refinance`, `sale_close`; D151/T68 y conciliación de cierre. | Cotejo de precio, costos, cancelación única y efectivo neto. Vencimiento corto bloquea sólo esa alternativa. |
| TIR, múltiplo y caja no recuperada | TIR anual sobre todos los flujos fechados; múltiplo = cobros/aportes; no recuperado = máximo(0, aportes−cobros). | `horizon_irr` usa el solver exacto D179 y aislamiento existente; `investor_story`. | Ambos extremos del intervalo de TIR se sustituyen en el polinomio de caja; historias brutas de ambas rutas cotejadas. |
| CoC y criterios | CoC del primer año completo post-refi, con NOI después de reservas y equity aún invertido. TIR/múltiplo usan todo el horizonte. YoC/spread, ocupación y RLV conservan bases documentadas D193. | D181 `collect_metrics`; D193 y `verify_annual_coc`. | Revisión de criterios distinta y ligada al nuevo período; criterio ausente → dictamen PENDING sin borrar caja respaldada. Banda → PENDING. |
| Fuente vigente y entrega | Se registra cada fuente; se construye y reproduce el expediente antes de entregar su PDF. | D198, B16 y `render_horizon`. | Cotización discordante, fuente/revisión anterior y entrega bloqueada; sólo sale el PDF íntegro vigente de una página. |

La referencia independiente está en `check_worksheet_holding_horizon_D266.independently_verify`; sus entradas son las celdas literales y los términos declarados, no los NOI o saldos publicados por el motor. Las pruebas están en `tests/test_worksheet_holding_horizon.py`. La constancia final y sus hashes se guardan en `review/MiniUW_Validacion_D266.json`.

## Alcance preciso y pendientes

TEC-01 queda implementado y cotejado para el perfil trimestral explícito de D266, con cinco años y una duración alternativa documentada de tres años. Eso no certifica todos los calendarios o las 33 políticas. Un calendario irregular, frecuencia mensual, comercial parcialmente estabilizado o duración fuera del contrato requiere una implementación específica; el perfil rechaza esos casos.

La caja uniforme por trimestre, impuesto proxy liquidado en cuatro cuotas, capital de trabajo sin cambios, inventario de ceros y ausencia de capex adicional son supuestos **declarados del ensayo**, no valores por defecto para un deal. El calendario fiscal M2/Florida por padrones no se mezcla con este perfil: su conexión plurianual continúa pendiente. El tope fiscal legal, beneficios condicionales y su orden de aplicación no se infieren de este proxy. La entrada D266 acepta únicamente el esquema técnico v31; extender el horizonte al esquema fiscal v32 y al auditor de datos críticos v33 requiere su conexión y validación específica. Esos perfiles se rechazan con PENDING; no se les atribuye la cobertura de este ensayo.

Permanecen abiertos TEC-02 (orquestador universal y autorización de shocks), TEC-03 (renta regulada), las definiciones de área/materialidad, reglas condicionales y aprobaciones detalladas en D265, además de validación empírica y documentación real. No se reemplazan por nuevas hipótesis sintéticas. La implementación de este horizonte no cambia los umbrales vigentes ni las reglas pendientes, y no activa producción.

## Reproducción

Con las dependencias de `requirements-reference.txt`, Tesseract y el entorno OCR configurado:

```sh
PYTHONPATH=src:tests:tools python -m unittest -v test_worksheet_holding_horizon
PYTHONPATH=src:tests:tools python tools/check_worksheet_holding_horizon_D266.py --output /tmp/miniuw-d266
```

El segundo comando genera fuentes de prueba identificadas como sintéticas, planillas, registro, expediente, cotejo y PDF vigente. No lee documentos de clientes ni exporta una decisión real. La documentación y el manifiesto se actualizan sólo después de comprobar las validaciones del corte publicado.
