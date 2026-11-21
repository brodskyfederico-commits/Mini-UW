# D276 · Integración mensual y revisión del corte D275

La revisión original se conserva en `docs/review/MiniUW_Revision_D275_Original.pdf` (SHA-256 `ed7b412fdc3df144629ee673b6fb4d8b7ee05775b8b455d45db3e6e625898767`). Sus propuestas son evidencia; no son criterios vigentes, autenticación de un aprobador ni autorización de despliegue.

## Perfil optativo y fuentes

`miniuw.synthetic-native-rental-inputs.v37` conecta los 55 campos originales con `miniuw.synthetic-native-monthly-integration.v1`. Los perfiles anteriores no cambian de calendario. La presencia de claves de extensiones mensuales en un esquema anterior produce bloqueo explícito, en vez de devolver caja trimestral sin utilizar las claves.

La entrada requiere dos XLSX, el plano y las cotizaciones PDF, el workbook de criterios separado y el inventario de referencias. Además requiere contratos explícitos por escenario para:

- Compromiso de obra, costo elegible y fechas de facturas / desembolsos; una enmienda sintética citada vincula la convención de días y el calendario al PDF bancario correcto.
- Prima y plazo de builder’s risk, y exclusiones de GC / soft. Si se declara incluida en GC, la prueba de inclusión debe corresponder al mismo GC, escenario y deal.
- Inventario de locales, superficies conciliadas, contrato, free rent, escalones, pérdidas, gastos, recuperos y destino de cada TI/LC.
- NOI operativo, bancario, de refi y de salida; base antes/después de reservas de cada cap.
- Todas las ventanas fiscales del vendedor y del comprador. Falta de un año, cita o base: PENDING, nunca cero.
- Equity inicial, regla de aportes posteriores, pagos de impuestos / interés / caja, préstamo solicitado por escenario, deuda permanente y vencimientos.

Los criterios comienzan con `investment_criteria: null` y la planilla de confirmación vacía. No hay préstamo global ambiguo ni ajuste automático del solicitado para obtener capacidad. C80–C82 y caps por uso sin un contrato de asignación compatible se bloquean; no se ignoran.

## Conexiones y cálculos

1. B01–B04 inventarían, enlazan y validan las fuentes y los 55 campos. B05–B07 concilian el plano; B08 lee cotizaciones antes de B09, que cruza cantidades y bases de precio.
2. M3 mantiene terreno `P × (1+C33)`, obra directa, contingencia, soft, TI/LC y déficit residencial prefinanciado separados. Servicios C25–C28 están incluidos en C57 según su contrato; no se suman dos veces.
3. El calendario se arma por meses enteros desde compra: fin de obra = compra+C46; estabilización = fin+C47; salida = estabilización+60 meses en este perfil.
4. M2 genera renta, gastos e impuesto de cada mes. La enmienda fiscal y la retasación pertenecen al perfil documental existente; el ejemplo no certifica su aplicabilidad legal a un deal real.
5. M5 devenga `Σ saldo_del_intervalo × tasa_nominal × fracción_de_días`. ACT/360 y 30E/360 deben estar declarados. Las liquidaciones se agrupan por fecha antes de calcular aportes; no se inventa un orden intradía.
6. Fuentes y usos concilian `equity + draws + ingresos comerciales preoperativos = TDC + caja libre`. La prima de obra entra una sola vez; el seguro operativo conserva su base independiente.
7. Comercial reconoce cada local y su free rent; TI/LC M3 entra en presupuesto, TI/LC operativo entra en caja y no se descuenta otra vez del NOI. El modo C20 porcentual conserva exactamente la base histórica de renta cobrada.
8. M6 calcula la menor capacidad de LTV, DSCR y debt yield si aplica. Solicitud superior: sólo la refi queda PENDING; sin refi puede continuar si la retención y el vencimiento de la deuda están documentados.
9. La deuda permanente mantiene frecuencia trimestral explícita mientras operación puede liquidar cada mes o cada trimestre declarado. Amortización, intereses, balloon y reservas se conservan separados. C60 mantiene su cadencia trimestral original.
10. M7 cierra la venta con NOI forward, cap compatible, gastos, deuda y liberaciones autorizadas. Venta insuficiente genera un aporte adicional documentado; no se oculta ni se recorta a cero.
11. Cada ruta conserva aportes y cobros brutos fechados. Factor USD10 = `10/equity inicial verificado`; los aportes posteriores no redefinen esa base. EM usa todos los aportes. TIR mensual anualizada = `z^-12−1`, con inventario de raíz única probado. Equity fuera del primer día mensual deja la TIR PENDING, sin redondear fechas.
12. B14 compara sólo bases, períodos y criterios compatibles; sin criterio permanece PENDING. B15/B16 generan y auditan exclusivamente el PDF de la revisión vigente. Una fuente crítica pendiente impide la entrega aunque otro resultado parezca correcto.

## Casos fijos y cotejo

`templates/golden_case_v1` permanece byte por byte igual, con sus 662 celdas de cotejo externo D275. No se reescribe su terreno distinto ni se inventa su GSF faltante.

`templates/golden_case_v2` es otro ejemplo, íntegramente sintético: 26 unidades, 3.000 m² de GBA compartida, mismo terreno USD1,1M; draws del 62,5% de obra directa, LTV aproximado 61–62% y DSCR aproximado1,252. El porcentaje de deuda/TDC es distinto y está rotulado aparte. Las solicitudes se fijaron al crear las cotizaciones sintéticas; el motor no redimensiona deuda.

`check_monthly_oracle_D276.py` construye la referencia desde los números literales de los XLSX y los contratos fuente, sin usar los módulos de cálculo de NOI, impuestos, comercial, financiación o amortización del motor. Comprueba 1.828 valores exactos y los flujos brutos por fecha y estrategia. Las expectativas están congeladas en `expected_financials.json`. No constituye revisión profesional independiente de un proyecto.

El control trimestral usa los mismos términos financieros y fiscales, sin free rent, misma fecha de inicio de locales, prima cero explícita y todas las liquidaciones trimestrales: las cuatro rutas de aportes y cobros coinciden exactamente con el perfil conservado. Una prima cero explícita de prueba no representa falta de seguro ni un default del modelo.

## Ensayos matemáticos y presentación

`worksheet_monthly_experiments_D276.py` amplía los rangos de estrés de la revisión. Cada punto se coteja aritméticamente. Distingue rangos adversos y favorables, capacidad bloqueada, dominio físico inválido y recuperación en la grilla. Un límite favorable inválido en Base no oculta un Downside válido. No afirma monotonía global ni disponibilidad bancaria a una tasa hipotética.

La extracción PDF/OCR se audita en el caso original. Los contrafactuales son ensayos matemáticos explícitos, no una nueva lectura OCR de una cotización real estresada. Tampoco amplían las evidencias de mercado ni aprueban sus supuestos. La grilla de precio usa TIR anual≥15% como meta hipotética del ejemplo, nunca como criterio nuevo de Lorena ni como RLV de la casa; mantiene deuda y demás eventos futuros fijos.

La hoja muestra EM con dos decimales, TIR con uno cuando el intervalo lo permite, unidades enteras, spread en bps, dependencia de venta y bases distintas de LTC. El intervalo completo de TIR se conserva en el expediente. YoC y spread se agrupan en un hallazgo sólo con una causa vigente citada; ambas comparaciones y todos los criterios aplicables del RLV permanecen intactos.

## Ejecución y límites

Desde un entorno con las dependencias locales de PDF/OCR disponibles:

```
PYTHONPATH=src:tools:tests python3 tools/check_monthly_native_D276.py /ruta/nueva/al/expediente
PYTHONPATH=src:tools:tests python3 tools/check_monthly_release_D276.py /ruta/nueva/a/la/aceptacion
PYTHONPATH=src:tools:tests python3 -m unittest test_monthly_native_D276 test_monthly_integration_D276 test_monthly_price_D276 test_review_D276 -v
```

El arnés necesita las versiones de runtime registradas; sin OCR disponible, no sustituye sus resultados. La revisión vigente se designa fuera del paquete auditado. La aceptación conserva los intentos fallidos y no sobreescribe una entrega existente.

La constancia de D276 distingue pruebas dirigidas, aceptación, controles históricos y batería general. Una corrida interrumpida no se presenta como completada. T10/T11 tienen herramientas; faltan proyectos reales y etiquetas humanas. Criterios, identidad/autoridad, fuentes reales y autorización continúan pendientes. Sin despliegue; dictamen real e histórico PENDING; retorno personal PENDING sin reparto.


El cotejo de CoC incluye un cierre de refi con aporte adicional: equity remanente = aportes pre-refi − refi neta **con signo**. Una refi neta negativa aumenta ese capital; no se recorta a cero. El control trimestral confirma la misma métrica y conserva idénticos los cuatro flujos brutos. La constancia actual amplía a1.828 comparaciones el cotejo inicial del v2 sin modificar sus fuentes o expectativas congeladas.
