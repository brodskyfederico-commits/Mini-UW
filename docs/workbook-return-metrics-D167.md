# Si invierto USD 10, ¿cuánto cobro y cuándo?

D167 · TIR anual y CoC verificados sobre los flujos fechados de D166. El ejemplo usa el equity agregado del proyecto. Ambos escenarios comienzan con USD 10 el 30/03/2027.

| Por USD 10 iniciales | Base | Downside |
|---|---|---|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Cobro neto de refinanciación | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Cobro de operación | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Cobro neto de venta | USD 14,82 · 30/12/2028 | USD 3,81 · 30/06/2029 |
| Total cobrado | USD 19,10 | USD 6,80 |
| Ganancia o déficit de caja | +USD 4,23 | −USD 11,39 |
| Múltiplo sobre todos los aportes | 1,28x | 0,37x |
| Sin recuperar al cierre | USD 0,00 | USD 11,39 |
| TIR anual | 17,58 % a 17,59 % | −42,32 % a −42,31 % |
| CoC posrefi del tramo, sin anualizar | 9,63 % · 30/09/2028–30/12/2028 | 3,02 % · 30/03/2029–30/06/2029 |
| Retorno personal | PENDING | PENDING |

El PDF de una página lista las fechas de cada aporte y cobro positivo. Los totales usan importes sin redondear.

## Cómo se verifica

- **TIR.** Usa la grilla trimestral declarada por D166 y suma los movimientos del mismo día con su signo. Conserva los trimestres sin caja. El motor aísla una sola raíz trimestral para cada escenario y la anualiza con `(1 + tasa trimestral)^4 − 1`. Un cálculo de VAN exacto comprueba los signos en los extremos de cada intervalo. Los extremos publicados redondean hacia afuera. Fechas fuera de la grilla dejan la TIR PENDING.
- **CoC sintético del tramo.** Divide los cobros de operación registrados después de la refinanciación y hasta la venta por todos los aportes brutos acumulados hasta la refi, incluidos los del mismo día. Excluye los cobros de refi y venta del numerador. Las bases por USD 10 son USD 14,87 en Base y USD 18,19 en Downside. La convención se declara para esta verificación. La base profesional de capital remanente y el CoC anual siguen pendientes. El cobro operativo se registra al cierre y puede incluir caja acumulada antes de la refi. Una base sin importe positivo o un cobro operativo ausente dejan el CoC PENDING. Un cero documentado se conserva.
- **Vigencia y reparto.** B16 reproduce los archivos y resultados de D166 y coteja la revisión vigente antes de aplicar las métricas. El informe de D167 registra las huellas del resultado y de la revisión, el intervalo TIR y las filas del numerador y del denominador del CoC. El retorno personal permanece PENDING por falta de términos de reparto documentados. La decisión real sigue PENDING.

## Reproducción en el VPS

El script regenera y audita D166 con el [runtime OCR del piloto](workbook-plan-scan-D131.md). Para cotejar una corrida guardada de D166, agregar `--package` con la ruta de su carpeta.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_return_metrics_D167.py --output /tmp/miniuw-d167
```

## Vigencia del indicador

El cociente D167 queda como diagnóstico histórico de cobros operativos registrados sobre aportes brutos. Para la definición de CoC sobre capital que sigue invertido y una ventana de NOI específica, usá el [perfil D173](workbook-formula-review-D173.md). Los porcentajes D167 no se comparan con umbrales del CoC de la casa.
