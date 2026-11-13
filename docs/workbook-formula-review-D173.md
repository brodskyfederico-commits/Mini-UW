# Si invierto USD 10, ¿cuánto cobro y cuándo?

Con impuestos del comprador y datos sintéticos, Base cobra **USD 18,10** y Downside **USD 6,08**. El aporte inicial de USD 10 es el 30/03/2027. El PDF de una página muestra los aportes y cobros fechados.

| Por USD 10 iniciales de equity del proyecto | Base | Downside |
|---|---:|---:|
| Aportes adicionales | USD 4,87 | USD 8,19 |
| Refi neta | USD 2,85 · 30/09/2028 | USD 2,45 · 30/03/2029 |
| Operación al cierre | USD 1,43 · 30/12/2028 | USD 0,55 · 30/06/2029 |
| Venta neta | USD 13,82 · 30/12/2028 | USD 3,08 · 30/06/2029 |
| Cobro total | **USD 18,10** | **USD 6,08** |
| Múltiplo sobre todos los aportes | **1,22x** | **0,33x** |
| Saldo sin recuperar al cierre | USD 0,00 | USD 12,11 |

Las cifras se redondean después del cuadre. El caso conserva FAIL simulado por múltiplo de equity en Downside. Decisión y retorno personal reales PENDING.

## Revisión del catálogo D170

Fuente revisada «MiniUW_Revision_Formulas_D170.pdf», pp. 1–3, SHA-256 `f84794a326bb2c5723dd3178744992ccd476d202e30adb777635d8319bbe6c0a`. La revisión coteja el catálogo. D173 ejecuta el código, el XLSX y la reconstrucción B16.

| Hallazgo y ubicación | Definición del perfil D173 | Validación y pendiente |
|---|---|---|
| CoC posrefi · p. 1, ítem 1 · M7-11 / estándares de la casa, política 12 · diagnóstico D167 | `(NOI del tramo posrefi − servicio programado de deuda del tramo) ÷ capital que sigue invertido al refinanciar`. El NOI y el saldo de capital vienen de fuentes explícitas. En este perfil el servicio es la cuota regular hasta la venta, sin payoff. | Base 11,46 % y Downside 1,79 % en sus respectivos tramos trimestrales, sin anualizar. Faltantes, ventana incompatible o saldo de cero dejan PENDING. D167 es una comparación histórica de cobros operativos sobre aportes brutos. El CoC D173 todavía carece de términos y umbrales reales compatibles, y el ensayo de screening conserva el múltiplo como métrica. |
| Impuesto del comprador en la salida · p. 2, ítem 2 · M7-05 / Inputs!C67 · motor T41 | `NOI forward comprador = ingresos forward − gastos forward sin impuesto − impuesto escolar comprador − impuesto no escolar comprador`. `Precio bruto = NOI forward comprador ÷ cap de salida`. Cada componente fiscal se declara para la misma ventana y con fuente vinculada a la revisión del caso. | Base y Downside concilian exactamente precio, costo variable y venta neta. La operación del vendedor, el NOI bancario y la capacidad de refi conservan sus bases. Si falta evidencia del impuesto del comprador, la venta del escenario queda PENDING. Un cero fiscal explícito se respeta. |
| Lectura del cobro LP/GP · p. 2, «Riesgo de presentación» · D170 | El PDF de ese ejemplo muestra cada cobro junto al múltiplo calculado sobre todos los aportes y al total aportado. Identifica el FAIL simulado del expediente de origen. | En el ejemplo D170, por USD 10 propios de cada rol, Base cobra USD 19,10 sobre USD 14,87 (1,28x) y Downside cobra USD 6,80 sobre USD 18,19 (0,37x). Son flujos archivados del ejemplo original de reparto. |
| Florida · p. 3 · C61–C62 / M2 y M7-05 | Los importes escolares y no escolares se conservan por separado en la interfaz de salida. D173 usa importes sintéticos ya calculados para el comprador. | PENDING para un inmueble real hasta verificar su régimen, jurisdicción, avalúos imponibles, millages, fecha efectiva y prorrateo del período. |
| Interés de obra y preferente · p. 2 | En D146, el interés simple trimestral se aplica al saldo de apertura más los desembolsos del trimestre. El ejemplo D169/D170 devenga el preferente simple sobre el capital LP al inicio del trimestre y el saldo impago no capitaliza. | Convenciones sintéticas declaradas. Queda pendiente cotejar cada una con los términos reales. |
| Ocupación de equilibrio y debt yield · p. 2 | M2-08 conserva el cálculo sintético por componentes. La fórmula simple de ocupación sigue en el conflicto SRC-02. El sizing del piloto usa LTV y DSCR. | PENDING hasta resolver la definición de ocupación y recibir la definición, base y mínimo de debt yield del banco aplicable. |

## Fuentes fiscales

El Department of Revenue de Florida indica que la Enmienda 3 se aplica desde el padrón fiscal 2027. El texto distingue gravámenes escolares y no escolares. La sección 193.1555 describe la retasación tras determinados cambios de propiedad o control al 1 de enero siguiente y contempla excepciones. El cálculo D173 no presupone que la base imponible sea el precio de venta ni adopta automáticamente el tope del 5 % como tasa de impuesto. [Boletín PTO 26-21](https://floridarevenue.com/property/Documents/PTO_BUL_26-21.pdf) · [Texto de la Enmienda 3](https://www.flsenate.gov/Session/Bill/2026F/1F/BillText/er/PDF) · [Florida Statutes §193.1555](https://www.flsenate.gov/Laws/Statutes/2026/193.1555)

## Reproducción

D173 usa el esquema sintético de planilla v25. B16 verifica la salida desde la planilla, el PDF de evidencia y la revisión vigente. Las versiones históricas siguen identificadas por sus propios esquemas y fuentes. Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md).

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_formula_review_D173.py --output /tmp/miniuw-d173
```
