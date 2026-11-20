# D267 · Horizonte integrado, M2 fiscal y auditor de datos críticos

El contrato optativo `miniuw.synthetic-integrated-fiscal-holding-horizon.v2` conecta los padrones M2 con compra, obra, estabilización, operación, refinanciación y venta. Conserva cuatro historias por USD 10 de equity inicial: Base y Downside, con y sin refi. La decisión real y el retorno personal sin términos de reparto siguen PENDING; no se habilita despliegue ni se adoptan criterios históricos.

## Entrada y alcance

- El esquema fiscal v32 permite comprobar el componente M2. El esquema v33 incorpora también el auditor de datos críticos antes de exponer la caja y entregar el PDF. El fixture principal usa v33.
- `holding_horizon` conserva una duración explícita de 12–60 meses en años completos y el calendario trimestral del primer día. Se prueban cinco años y una duración alternativa de tres años. No hay un default financiero de cinco años.
- `holding_tax_cash` exige perfil, reglas, fuente y declaraciones independientes por escenario. La exclusión de impuestos previos del presupuesto debe estar documentada para agregarlos como usos: no se supone que estén incluidos ni que sean cero.
- `florida_property_tax` necesita padrón inicial, valoración escolar y no escolar, millage separado, tratamiento y fecha de cada evento y fuentes para todos los años utilizados. Los registros del ensayo son pronósticos sintéticos declarados, sin autenticación oficial o legal.
- El perfil proxy y el fiscal no se mezclan. Una fuente fiscal requerida ausente bloquea el cálculo afectado; no se vuelve al proxy ni al perfil anterior.

## Conexiones, fórmulas y evidencia

| Requisito | Definición y conexión | Código | Validación |
|---|---|---|---|
| TEC-01 de D266: horizonte fiscal | M2 calcula cada año operativo, cada trimestre de caja, la tenencia previa y la ventana forward de salida. | `worksheet_horizon_fiscal_D267.window_contract/fiscal_cash`; `worksheet_florida_tax_D203.window_taxes`. | Contraste independiente de 32 ventanas Base y 34 Downside. |
| Impuesto previo a estabilización | Cada trimestre de tenencia genera un uso adicional excluido del presupuesto, con fecha y fuente. Se fondea desde caja o aporte; no aumenta automáticamente la deuda elegible. | `worksheet_construction_financing_D146.staged_construction_financing(additional_uses=...)`. | Cotejo de usos, draws, intereses, comisión, aportes y saldos por fecha. La suma fiscal entra una vez en TDC. |
| Impuesto durante operación | Impuesto escolar = valor imponible escolar × mills / 1000 × meses / 12. El no escolar usa su propia base. Las cuatro cuotas deben sumar exactamente el impuesto anual. | D203 y `worksheet_horizon_fiscal_D267.operation_rows`. | Downside atraviesa enero dentro de su año operativo; se comprueban cuotas distintas, sin sustituirlas por el promedio anual. |
| Base de valoración y salida | Se usa el impuesto de la ventana forward bajo el perfil M2 existente. Si la ventana no alcanza el siguiente reset, no exige un padrón de comprador que no se usa. | D203 `window_taxes`; compilación de NOI D140; valoración/cierre D266 reutilizados. | Salida Base el 1 de enero y Downside en julio; reset del comprador separado de las bases escolares y no escolares. |
| Reglas M2 existentes | Se conserva el perfil sintético D203 de cap no escolar y resets explícitos. No se aplica el cap escolar ni se hereda el cap del vendedor en un reset del comprador. | D203 `assessed_value`, sin cambio de fórmula. | Bordes de cap, cambio de titularidad, mejora declarada y cruce de año. Esto no confirma vigencia o aplicabilidad legal real. |
| Caja y métricas por USD 10 | Factor = 10 / aporte inicial verificado. Aportes posteriores y cobros conservan sus fechas. Reservas y cancelación de deuda ocurren una sola vez. | Adaptador D267 y fuente D266 fijada por SHA-256. | Referencia financiera desde celdas literales: presupuesto, fondeo, seis NOI, 20 cuotas, venta, caja bruta y ambos extremos de TIR para las cuatro rutas. |
| CoC | Primer año completo post-refi: NOI después de reservas e impuesto, menos servicio, dividido por equity remanente. | D266 reutilizado con cuotas M2 fechadas; referencia D267. | Se cotejan numerador, denominador y ventana. El impuesto no se vuelve a restar. |
| Auditor fiscal | Inventario independiente versionado de valores esperados, huellas de las declaraciones fiscales y cobertura de todas las ventanas. Un verde sin respaldo bloquea la caja del escenario. | `audit_worksheet_critical_evidence_D219.audit`; D267 `critical_fiscal_fields/fiscal_source_issues`. | Se comprueban 116 datos críticos; se inyectan detalle fiscal errado, omisión de trimestre y eliminación del inventario de ventanas. |
| Auditor documental | Las citas del plano compartido y del DSCR bancario siguen siendo necesarias. Corregir una sola no habilita la otra rama. | D219/D220 y flujo D140. | Fallos conjuntos, correcciones parciales y restauración completa, con flujos por USD 10 conservados. |
| PDF y revisión | Un PDF de una página muestra los importes y las fechas reales de los trimestres calculados. Sólo se entrega la revisión reproducida vigente. | D267 `render_horizon`; B16 y entrega existente. | Antigüedad de revisión, entrega bloqueada ante falso verde y reproducción del PDF vigente. |
| Vacío y cero | Toda magnitud fiscal o fuente requerida ausente bloquea. Un cero numérico explícito permanece cero. | Guardas M2 y contrato de usos adicionales. | Millage ausente, vacío y sin fuente; millage/tasa/reserva/crecimiento cero y amortización con balloon al cierre. |

La referencia fiscal/financiera es `check_worksheet_horizon_fiscal_D267.independent_taxes/independently_verify`. Lee las declaraciones y celdas fuente; no toma los NOI, saldos o totales del motor como sus entradas. El inventario crítico `templates/synthetic-critical-evidence-D267.json` se construye desde el corpus sintético declarado y esa referencia, antes de observar el resultado del motor. No se genera desde resultados para hacerlos coincidir.

## Preservación de versiones

D266 conserva sus bytes y su perfil v1. D267 reutiliza sus funciones en un espacio aislado, exige la huella `bba535fd748b8f3fb6c982d4e8f9109e1db8dd36d64abce0ffb047a8f3b2c924` y sustituye únicamente el contrato y la liquidación fiscal trimestral. No modifica variables globales del módulo original, sus fórmulas financieras ni el presupuesto aritmético; no redondea los cálculos. Una fuente de algoritmo distinta queda PENDING, sin volver a un motor anterior.

La referencia v33 se selecciona entre rutas conocidas del repositorio. Los perfiles anteriores siguen usando el inventario D219; el corpus D267 tiene su propio inventario. No se aceptan rutas arbitrarias del deal ni se actualiza el inventario automáticamente para aprobar fuentes modificadas. Cambiar el corpus exige otra revisión de evidencia independiente.

El verificador D203 conservaba un cotejo contra el primer PDF archivado D200 (`48427ed9…`). La corrida previa de D267 reprodujo exactamente el PDF de aceptación ya verificado en D265/D266 (`ed0f2ad2…`). Se versiona esa referencia en `templates/expected-D200-pdf-D267.pdf` y se corrige el cotejo del verificador. El PDF original permanece intacto; los cálculos y umbrales no se modifican para resolver esa diferencia de referencia.

## Pendientes que este bloque no cierra

El calendario mensual/irregular, las cotizaciones y reglas de devengo fuera del contrato trimestral, el orquestador de las 15 sensibilidades, la renta regulada, beneficios fiscales condicionales/materialidad y las decisiones de autoridad/criterios conservan sus puertas abiertas. El cierre técnico de este perfil no certifica las 33 políticas, documentos reales, aprobación de inversión, falsos verdes en cualquier PDF ni producción.

## Reproducción

Con las dependencias de referencia y OCR disponibles:

```sh
PYTHONPATH=src:tests:tools python -m unittest -v test_worksheet_horizon_fiscal
PYTHONPATH=src:tests:tools python tools/check_worksheet_horizon_fiscal_D267.py --output /tmp/miniuw-d267
```

La constancia del corte probado y los límites se registran en `docs/review/MiniUW_Validacion_D267.json`. Los logs completos, expedientes generados, runtimes y datos de clientes no se incorporan al hito de GitHub.
