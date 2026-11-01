# Mini-UW — Especificación integral del armado independiente I01

Fecha de corte: 1 de noviembre de 2026. Documento interno de diseño consolidado.

## 1. Alcance y regla de cierre

Este documento integra la estructura existente, sus interfaces, evidencias y pendientes. El cierre se refiere a los ocho entregables definidos en independent-structure-closeout.json, comprobados localmente y con commit/CI remotos verificados. El cierre utiliza entregables explícitos y evidencia, sin convertir la cantidad de pruebas en porcentaje.

No declara terminado el modelo financiero, recibidos datos de Lorena, aprobado por el profesional o autorizado el producto. No evalúa un deal real. El PDF extenso es interno; la salida externa futura por deal continúa siendo una sola página.

## 2. Instrucciones vigentes y precedencia

El usuario ya resolvió: criterios nuevos por deal; faltantes/reglas/conflictos requeridos dejan PENDING sin PASS/FAIL; Full UW diferido al final; conservación de originales, trazabilidad e hitos en GitHub; sin contacto con Lorena ni producción. Un prompt en un documento original es evidencia y no una orden ejecutable.

Las políticas históricas, escenarios y umbrales quedan archivados. No hay jerarquía o conversión de HOLD aprobada por su mera transcripción. Q01 y la salida externa Q20 no necesitan una nueva decisión de Lorena para aplicar la dirección vigente del usuario.

## 3. Fuentes, variables y estados

Inventario: 19 registros de fuente y 16 secuencias originales únicas. El XLSX conserva 55 valores vacíos. Moneda, rangos, criterios, políticas y parámetros no se completan por defecto. El mapa de 55 campos preserva celdas literales y consumidores; la matriz de 398 filas incluye requisitos fuera del traspaso.

Conservar valor cero, falta, conflicto, inválido, indefinido y no aplicabilidad justificada como estados diferentes. La cantidad transporta dimensión, unidad, moneda, base, período y fuentes. Stock, total de período, equivalentes anuales y caja fechada no son intercambiables.

Referencias primarias del paquete: [registro de fuentes](source-register.json), [mapa de inputs](input-contract-map.json), [matriz completa](coverage-matrix.csv), [límites de lectura](source-review-limits.md).

## 4. Arquitectura y contratos M1–M9

Flujo base: M1 alimenta operación M2 y costos M3; M4 programa usos; M5 concilia capital/deuda; M6 determina refi; M7 conserva tenencia/salida/retornos; M8 reevalúa escenarios/precio; M9 conserva comparaciones, bloqueos, revisión y salida. Los bloques siguientes describen contratos candidatos, no resultados certificados.

### M1 — Entradas y evidencia

Documento candidato: docs/model-input-evidence.md. Interfaz agregada: schemas/M1.schema.json.

**M1-01 — Recepción y procedencia**

Master §1; Manual p.16/p.38. Conservar original/hash, nombre, versión declarada, tipo, páginas y ubicación; extracción no prueba autenticidad.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Master §1; Manual p.16/p.38. Contrato candidato: docs/model-input-evidence.md, línea 7. Estado financiero: abierto.

**M1-02 — Programa y grupos de unidades**

Master §2; Manual p.7. Conteos explícitos por unit type/dormitorio, mercado/asequible; reconciliar totales sin contar etiquetas.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Master §2; Manual p.7. Contrato candidato: docs/model-input-evidence.md, línea 8. Estado financiero: abierto.

**M1-03 — Áreas y unidades físicas**

Master §3 Areas; Manual p.7. GSF, NRSF, áreas unitarias/comerciales, parking y sitio separados; no usar ratios de eficiencia inventados.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Master §3 Areas; Manual p.7. Contrato candidato: docs/model-input-evidence.md, línea 9. Estado financiero: abierto.

**M1-04 — Input Sheet original**

Inputs A/B/C/D/E/F, 55 filas. Literal, valor normalizado, unidad/base, obligatoriedad, nota y fuente preservados. Rangos y semántica pendientes donde no aprobados.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Inputs A/B/C/D/E/F, 55 filas. Contrato candidato: docs/model-input-evidence.md, línea 10. Estado financiero: abierto.

**M1-05 — Estados y aplicabilidad**

Manual p.15; traspaso §3. Cero explícito, faltante, inválido, conflicto y no aplicable justificado distintos; sin default financiero.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Manual p.15; traspaso §3. Contrato candidato: docs/model-input-evidence.md, línea 11. Estado financiero: abierto.

**M1-06 — Lecturas y conciliación**

Manual pp.38–39; traspaso §7. Citas y afirmaciones alternativas, correcciones enlazadas; coincidencia no demuestra independencia de lectores ni verdad.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Manual pp.38–39; traspaso §7. Contrato candidato: docs/model-input-evidence.md, línea 12. Estado financiero: abierto.

**M1-07 — Normalización y consumidores**

Manual pp.7–14; traspaso §§3/5. Contrato por campo con tipo/currency/unit/período/base y módulos; no asumir moneda o formato porcentual de un símbolo.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; Manual pp.7–14; traspaso §§3/5. Contrato candidato: docs/model-input-evidence.md, línea 13. Estado financiero: abierto.

**M1-08 — Cierre de paquete y revisiones**

C1; traspaso §§6–7. Mapear dependencias/faltantes por alcance; cada revisión invalida descendientes y preserva historia sin mezclar runs.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§1–3; C1; traspaso §§6–7. Contrato candidato: docs/model-input-evidence.md, línea 14. Estado financiero: abierto.

### M2 — Operación y NOI

Documento candidato: docs/model-operations-contract.md. Interfaz agregada: schemas/M2.schema.json.

**M2-01 — Renta mensual de tipo i: r_i por unidad o s_i × área_i por SF**

C7, C8:C11; área y conteos explícitos de planos | Q11; dormitorio no equivale a unit type; no convertir GSF a NRSF

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Revenue. Contrato candidato: docs/model-operations-contract.md, línea 15. Estado financiero: abierto.

**M2-02 — Renta residencial potencial mensual = Σ n_i × r_i**

M2-01, unidades mercado/asequibles documentadas | No duplicar las unidades asequibles dentro del conteo de mercado

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Revenue. Contrato candidato: docs/model-operations-contract.md, línea 16. Estado financiero: abierto.

**M2-03 — Ingreso residencial efectivo: potencial menos pérdidas/concesiones más otros ingresos definidos**

C13:C15; perfiles por período y reglas de base | No decidir si vacancia afecta other income; no aplicar concesión otra vez si renta ya es neta

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Revenue. Contrato candidato: docs/model-operations-contract.md, línea 17. Estado financiero: abierto.

**M2-04 — Comercial histórico: SF × renta NNN anual × (1−vacancia) × (1−no recuperable)**

C16:C21, usos y áreas documentados | Definir inicio pos-TCO y si no recuperable reduce ingreso o es gasto; no descontarlo por ambos lados

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Revenue. Contrato candidato: docs/model-operations-contract.md, línea 18. Estado financiero: abierto.

**M2-05 — Gastos sin impuesto = controlables + management + seguro + reservas según inclusión aprobada**

C57:C60; management histórico sobre EGI residencial C58 | No aplicar fee al ingreso comercial sin regla; distinguir reserva como gasto NOI y movimiento de caja

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Expenses. Contrato candidato: docs/model-operations-contract.md, línea 19. Estado financiero: abierto.

**M2-06 — A = ingresos efectivos − gastos operativos sin impuesto**

M2-03:M2-05 con mismo período | A no equivale a caja distribuible, ni incluye deuda por defecto

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Expenses. Contrato candidato: docs/model-operations-contract.md, línea 20. Estado financiero: abierto.

**M2-07 — NOI e impuesto simultáneos bajo ecuación documentada**

A; comparables C62 × unidades si procede; C61; millage, exención, cap y sus fuentes | Q2, ley/coeficientes/valoración no aprobados; comparar montos totales del mismo período

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Expenses. Contrato candidato: docs/model-operations-contract.md, línea 21. Estado financiero: abierto.

**M2-08 — Ocupación de equilibrio como conjunto de q factibles con NOI(q) ≥ servicio de deuda aplicable**

Ingresos/costos dependientes de q; reglas fiscales; deuda M6 | Q12; definición de ocupación física/económica; no elegir ratio bruto/efectivo del conflicto SRC-02

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3, Refinance and metrics, Break-even occupancy. Contrato candidato: docs/model-operations-contract.md, línea 22. Estado financiero: abierto.

### M3 — Presupuesto y alcance

Documento candidato: docs/model-budget-schedule.md. Interfaz agregada: schemas/M3.schema.json.

**M3-01 — Normalizar hard vertical según base: GSF×precio/GSF, unidades×precio/unidad o total explícito**

C34/C35 y programa. Tres bases alternativas, no sumables. No sustituir GSF por NRSF.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 9. Estado financiero: abierto.

**M3-02 — Registro de inclusiones: cada alcance económico tiene ID, fuente, monto/base, categoría, incluido/excluido/no determinado y vínculo a contrato**

Manual p.58 exige definición C35; R1–R4 pp.59. Parking, site, fee, seguros, GC/general conditions y contingencia pueden venir dentro del precio. No sumarlos de nuevo.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 10. Estado financiero: abierto.

**M3-03 — Contingencias: separar dueño/contratista/escalamiento, base de aplicación, inclusión en precio, control y uso**

C39; GC pp.56/58/59. Un porcentaje sin base no determina monto. Una contingencia es presupuesto, no gasto desembolsado automáticamente.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 11. Estado financiero: abierto.

**M3-04 — Soft y TI/LC: porcentaje por base hard aprobada más TI/LC comercial si corresponde**

C40/C41. Definir si base incluye contingencia, parking/site y fees. Un monto GC excluido debe tener cobertura documentada; no se inventa precio.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 12. Estado financiero: abierto.

**M3-05 — Compra evaluada más gastos de cierre explícitos**

C32/C33. Asking y precio evaluado son variables separadas. Precio ausente no se convierte en cero; precio de búsqueda M8 no es dato aportado.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 13. Estado financiero: abierto.

**M3-06 — Presupuesto antes de financiación = suma de alcances exclusivos, incluyendo ajustes documentados**

M3-01:M3-05. Mantener presupuesto, devengo, pago y saldo pendiente separados. TDC all-in requiere financiación M5; no cerrarlo antes.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC. Contrato candidato: docs/model-budget-schedule.md, línea 14. Estado financiero: abierto.

### M4 — Calendario

Documento candidato: docs/model-budget-schedule.md. Interfaz agregada: schemas/M4.schema.json.

**M4-01 — Hitos con fechas/índices separados: compra, inicio obra, TCO, fin obra, estabilización, refi y venta**

C46/C47; PAR-04. No asumir equivalencia TCO/estabilización ni adoptar obra+lease-up+1 como fecha aprobada.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 24. Estado financiero: abierto.

**M4-02 — Pesos explícitos por partida y período w_jt: pago asignado B_j×w_jt**

Para presupuesto totalmente programado, Σw_jt=1 y pesos no negativos; no normalizar una curva incompleta silenciosamente. Para programación parcial se conserva saldo sin asignar y bloqueo de financiación.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 25. Estado financiero: abierto.

**M4-03 — Perfil histórico sin² y soft upfront meses 1–3**

C42; Master Timing. Pendientes discretización, fase, denominador, pesos primeros meses, obra menor a tres meses y calendario de pagos; no elegir una curva por conveniencia.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 26. Estado financiero: abierto.

**M4-04 — Devengo y caja separados; cuentas por pagar y anticipos conciliados**

Un costo incurrido no es necesariamente draw del banco ni aporte de equity; M5 financia eventos de caja bajo reglas propias. Retainage, anticipos y liberaciones necesitan condiciones explícitas.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 27. Estado financiero: abierto.

**M4-05 — Escenario de retraso modifica fechas, curva y costos sólo mediante políticas explícitas**

Q4/Q5, Manual pp.22–23; política 23. Repartir costo fijo en más meses no crea por sí solo costo adicional; costos mensuales requieren importe y período. No inventar shocks.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 28. Estado financiero: abierto.

**M4-06 — Puente hacia M5: usos por período y saldo no programado, fuentes y versiones**

Si Σ pagos≠presupuesto, la diferencia se explica (reserva/saldo/alcance/ajuste) o bloquea C2. No forzar caja final a cero. Cambios de calendario invalidan interés/deuda/retornos aunque total de costo no cambie.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Timing. Contrato candidato: docs/model-budget-schedule.md, línea 29. Estado financiero: abierto.

### M5 — Capital y construcción

Documento candidato: docs/model-construction-finance.md. Interfaz agregada: schemas/M5.schema.json.

**M5-01 — Base elegible de costo y capacidad del préstamo**

C51 es LTC; Master §3 Timing relaciona LTC/TDC. Falta alcance de costo elegible y base contractual; no equiparar automáticamente elegible con TDC.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 9. Estado financiero: abierto.

**M5-02 — Compromiso, monto disponible, draws acumulados y saldo de deuda separados**

Manual p.32 term sheet pendiente; ledger de caja actual. No suponer que todo préstamo comprometido se desembolsa.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 10. Estado financiero: abierto.

**M5-03 — Interés por período según saldo y convención documentados**

C52; PAR-03/04, Manual p.53. Fecha, tasa nominal/efectiva, día-base, saldo inicial/promedio/final, floor y cambios de tasa requieren definición. No dividir siempre la tasa anual por doce.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 11. Estado financiero: abierto.

**M5-04 — Fee de originación: porcentaje por base y fecha explícitos**

C53; Master Costs and TDC. Compromiso, saldo, draw y préstamo aprobado son bases diferentes; fee pagado, retenido o financiado necesita contrapartida.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 12. Estado financiero: abierto.

**M5-05 — Aplicación de capital: equity requerido y aportes reales por fecha**

Master Timing equity-first; Q7/Q8 Manual p.23. No confundir requerido, comprometido, disponible y aportado. Equity-first no fija el origen de cada déficit posterior.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 13. Estado financiero: abierto.

**M5-06 — Conciliación por préstamo: saldo inicial + principal recibido + interés capitalizado + ajustes documentados − principal repagado**

Contrato DEBT-01 y Master §3 financiación. Separar caja prestada de capitalización sin caja; no contar ambos como cobros de deuda.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 14. Estado financiero: abierto.

**M5-07 — Uso de NOI/caja operativa durante lease-up**

Master Timing: NOI paga interés primero; Q6 abierto Manual p.23. NOI devengado no prueba cobro. Destino del excedente y déficits no se inventa.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 15. Estado financiero: abierto.

**M5-08 — TDC y costo financiero circular**

Master Costs and TDC / Manual p.13. Cerrar fórmula, bases, perfiles, convergencia, residuales y dominio; solución algebraica reducida no certifica motor mensual.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 16. Estado financiero: abierto.

**M5-09 — Control de factibilidad por fecha**

Contratos M4/M5 y C2. Capacidad contractual excedida, vencimiento sin financiación o faltante de caja no se cubren con draws/aportes ficticios. Clasificación queda PENDIENTE por información/reglas ausentes; no convertir en FAIL automáticamente.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 17. Estado financiero: abierto.

**M5-10 — Estado de salida para M6**

Master Refinance: payoff de construcción; Q13 otra deuda. Entregar saldo, interés devengado pendiente, fees, reservas restringidas, vencimiento y alcance del payoff; no asumir saldo = liquidación total.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Costs and TDC / Timing / Refinance and metrics. Contrato candidato: docs/model-construction-finance.md, línea 18. Estado financiero: abierto.

### M6 — Refinanciación

Documento candidato: docs/model-refinance-contract.md. Interfaz agregada: schemas/M6.schema.json.

**M6-01 — Estrategia y fecha del refi**

Master §3 Timing/Refinance; Manual p.20 y Q12 p.24. La aplicabilidad y el calendario son entradas expresas. Si la estrategia no requiere refi, justificar no aplicable; no inventar un préstamo.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3 Timing/Refinance; Manual p.20 y Q12 p.24. Contrato candidato: docs/model-refinance-contract.md, línea 9. Estado financiero: abierto.

**M6-02 — NOI y valor para sizing**

Master §3, Value = NOI / refi cap; Inputs C66. Usar NOI admisible y cap de mismo período/alcance; definir si difiere del NOI del inversor. Cap cero o dato faltante bloquea; NOI negativo no produce por sí solo un préstamo negativo.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3, Value = NOI / refi cap; Inputs C66. Contrato candidato: docs/model-refinance-contract.md, línea 10. Estado financiero: abierto.

**M6-03 — Límite bancario por LTV**

Master §3; Inputs C71. Valor admisible × LTV explícito. No confundir con LTC ni tratar límite como desembolso aprobado.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3; Inputs C71. Contrato candidato: docs/model-refinance-contract.md, línea 11. Estado financiero: abierto.

**M6-04 — Constante de deuda y servicio**

Master §3 annual constant; Inputs C69/C70. Especificar tasa periódica, capitalización, pagos/año, amortización, pagos vencidos/anticipados e interest-only si existe. No inferir términos del dato tasa.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3 annual constant; Inputs C69/C70. Contrato candidato: docs/model-refinance-contract.md, línea 12. Estado financiero: abierto.

**M6-05 — Límite bancario por DSCR**

Master §3, min DSCR; Inputs C72. NOI bancario / (DSCR mínimo × constante anual) bajo denominadores positivos. No confundir DSCR bancario con criterio de inversión de Lorena.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3, min DSCR; Inputs C72. Contrato candidato: docs/model-refinance-contract.md, línea 13. Estado financiero: abierto.

**M6-06 — Préstamo seleccionado y restricciones activas**

Master §3 MIN LTV/DSCR; Estándares políticas 26/30. Menor capacidad de restricciones aplicables y documentadas. Empate conserva ambas como vinculantes; otras restricciones contractuales pueden limitar. Capacidad no equivale a aprobación.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3 MIN LTV/DSCR; Estándares políticas 26/30. Contrato candidato: docs/model-refinance-contract.md, línea 14. Estado financiero: abierto.

**M6-07 — Amortización, vencimiento y balloon**

Inputs C70; traspaso §5 distinciones de préstamo. Saldo posterior a pagos depende del calendario. Vencimiento menor a amortización exige saldo residual exigible; no inventar refinanciación futura ni extensión.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Inputs C70; traspaso §5 distinciones de préstamo. Contrato candidato: docs/model-refinance-contract.md, línea 15. Estado financiero: abierto.

**M6-08 — Liquidación de construcción y otras deudas**

Master §3 net cash-out; M5-10; Q13 Manual p.24. Payoff = obligaciones expresas a fecha: principal, interés pendiente, fees y otras partidas aplicables, sin duplicar capitalización. Ausencia de campo otra deuda no demuestra monto cero.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3 net cash-out; M5-10; Q13 Manual p.24. Contrato candidato: docs/model-refinance-contract.md, línea 16. Estado financiero: abierto.

**M6-09 — Costos y reservas de refinanciación**

Inputs C73/C74; Estándares políticas 9/10. Costo porcentual requiere base y fecha. Reservas nuevas y liberación de reservas previas se registran por separado; fondos restringidos no son distribución.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Inputs C73/C74; Estándares políticas 9/10. Contrato candidato: docs/model-refinance-contract.md, línea 17. Estado financiero: abierto.

**M6-10 — Caja neta, cash-out/cash-in y estado para M7**

Master §3; Estándares políticas 9/10/12; Q7/Q8. Distribución posible y aporte adicional se determinan después de liquidación, costos y fondos restringidos. Equity recuperado, equity remanente y valor patrimonial son conceptos distintos; bases pendientes.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics; Master §3; Estándares políticas 9/10/12; Q7/Q8. Contrato candidato: docs/model-refinance-contract.md, línea 18. Estado financiero: abierto.

### M7 — Tenencia, venta y retornos

Documento candidato: docs/model-hold-exit-returns.md. Interfaz agregada: schemas/M7.schema.json.

**M7-01 — Estrategia, horizonte y fechas**

Master §3 Hold; Estándares política 16; Manual p.20/Q12 p.24. Horizon explícito por deal; distinguir TCO, estabilización, refi y venta. Cinco años es referencia histórica, no valor activo por defecto.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Master §3 Hold; Estándares política 16; Manual p.20/Q12 p.24. Contrato candidato: docs/model-hold-exit-returns.md, línea 11. Estado financiero: abierto.

**M7-02 — Operación y crecimiento durante tenencia**

Inputs C75:C76; Master §3 Hold; Manual pp.11/14. Rentas y gastos crecen por componentes y fechas expresos. No aplicar crecimiento de rentas a todo el NOI ni suponer impuesto constante.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Inputs C75:C76; Master §3 Hold; Manual pp.11/14. Contrato candidato: docs/model-hold-exit-returns.md, línea 12. Estado financiero: abierto.

**M7-03 — Caja operativa, deuda y fondos restringidos**

Master §3 CoC/Hold; Estándares política 12. Cobros/pagos, devengo, servicio de deuda y reservas separados; no distribuir NOI automáticamente ni usar caja restringida.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Master §3 CoC/Hold; Estándares política 12. Contrato candidato: docs/model-hold-exit-returns.md, línea 13. Estado financiero: abierto.

**M7-04 — Capital adicional y distribuciones brutas**

Estándares políticas 9/10/15/16; traspaso §5. Registrar aportes/distribuciones de cada evento, aunque ocurran en el mismo período. Requerimiento de equity no prueba capital disponible.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Estándares políticas 9/10/15/16; traspaso §5. Contrato candidato: docs/model-hold-exit-returns.md, línea 14. Estado financiero: abierto.

**M7-05 — NOI forward y valor de salida**

Master §3 Hold; Estándares política 31; Inputs C67. NOI del período forward y exit cap compatibles. Definir ventana, estabilización, impuestos y fecha; valoración no es cobro realizado.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Master §3 Hold; Estándares política 31; Inputs C67. Contrato candidato: docs/model-hold-exit-returns.md, línea 15. Estado financiero: abierto.

**M7-06 — Costos y liquidación de venta**

Master §3 Hold; Inputs C68; Q16. Precio bruto, costos, impuestos aplicables documentados, ajustes, liberación de reservas y caja previa sin doble cuenta. No presumir reglas fiscales.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Master §3 Hold; Inputs C68; Q16. Contrato candidato: docs/model-hold-exit-returns.md, línea 16. Estado financiero: abierto.

**M7-07 — Deuda y obligaciones pendientes a salida**

Master §3 Hold, loan balance; contrato M6-07/M6-08. Usar saldo a fecha de venta y obligaciones adicionales. No descontar otra vez principal ya amortizado ni inventar extensión/refi para cubrir maturity.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Master §3 Hold, loan balance; contrato M6-07/M6-08. Contrato candidato: docs/model-hold-exit-returns.md, línea 17. Estado financiero: abierto.

**M7-08 — Proceeds al inversor y caja terminal**

Estándares políticas 15/16; traspaso §5. Separar venta neta, distribución, aporte y caja retenida. Un residual negativo exige clasificación y fuente, no una distribución negativa encubierta.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Estándares políticas 15/16; traspaso §5. Contrato candidato: docs/model-hold-exit-returns.md, línea 18. Estado financiero: abierto.

**M7-09 — Equity Multiple**

Estándares política 16; Master §3 Equity Multiple. Distribuciones/proceeds incluidos sobre aportes brutos incluidos. Definir alcance y excluir doble cuenta de valor terminal/venta.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Estándares política 16; Master §3 Equity Multiple. Contrato candidato: docs/model-hold-exit-returns.md, línea 19. Estado financiero: abierto.

**M7-10 — IRR regular y anualización**

Estándares política 15; Master §3 monthly IRR annualized. Calendario, frecuencia, dominio y raíces explícitos. No seleccionar una raíz conveniente; no inferir raíces del número de cambios de signo.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Estándares política 15; Master §3 monthly IRR annualized. Contrato candidato: docs/model-hold-exit-returns.md, línea 20. Estado financiero: abierto.

**M7-11 — Fechas irregulares y retorno corriente**

Traspaso §5; Estándares políticas 12/15. XIRR requiere fechas y fracción de año aprobada. CoC requiere período/base de capital remanente; denominador cero permanece indefinido.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Traspaso §5; Estándares políticas 12/15. Contrato candidato: docs/model-hold-exit-returns.md, línea 21. Estado financiero: abierto.

**M7-12 — Nivel proyecto, LP/JV y salida a M8/M9**

Estándares políticas 2/15/16; Manual p.20. Mantener retornos agregados del equity del proyecto. LP, fees/promote/waterfall sólo con estructura documentada y ledger conciliable separado.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: §3 Refinance and metrics / Hold; Estándares políticas 2/15/16; Manual p.20. Contrato candidato: docs/model-hold-exit-returns.md, línea 22. Estado financiero: abierto.

### M8 — Escenarios y precio

Documento candidato: docs/model-scenarios-price.md. Interfaz agregada: schemas/M8.schema.json.

**M8-01 — Inventario de escenarios requeridos**

Traspaso §6; Master §4. ID, propósito, aplicabilidad, escenarios requeridos/excluidos y regla de agregación explícitos; nada requerido se omite silenciosamente.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Traspaso §6; Master §4. Contrato candidato: docs/model-scenarios-price.md, línea 11. Estado financiero: abierto.

**M8-02 — Entradas completas y aisladas**

Traspaso §6; Master §4 change vs Base. Compartir hechos de fuente sólo mediante referencia explícita a la misma versión; sin herencia automática de supuestos o criterios.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Traspaso §6; Master §4 change vs Base. Contrato candidato: docs/model-scenarios-price.md, línea 12. Estado financiero: abierto.

**M8-03 — Transformación y unidad de cada driver**

Master §4 tabla; Estándares políticas 18–33. Distinguir cambio relativo, puntos porcentuales, bps, meses y reemplazo absoluto. Base, delta, unidad, orden y fuente explícitos.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Master §4 tabla; Estándares políticas 18–33. Contrato candidato: docs/model-scenarios-price.md, línea 13. Estado financiero: abierto.

**M8-04 — Downside integrado y dependencias**

Estándares política 3/33; Manual p.17. Aplicar drivers autorizados conjuntamente y recalcular dependientes, no sumar sensibilidades individuales como resultado integrado.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Estándares política 3/33; Manual p.17. Contrato candidato: docs/model-scenarios-price.md, línea 14. Estado financiero: abierto.

**M8-05 — Sensibilidad individual y ranking**

Master §4 Single-driver; Manual p.14. Mantener iguales los hechos/políticas no afectados con referencias explícitas; reportar métrica de ranking, signo, empate y aplicabilidad.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Master §4 Single-driver; Manual p.14. Contrato candidato: docs/model-scenarios-price.md, línea 15. Estado financiero: abierto.

**M8-06 — Overrides y condicionales**

Estándares políticas 5/33; Manual pp.20/27. Fuente, justificación, alcance, vigencia y autorización; no resolver con confianza de OCR o papel nominal del autor.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Estándares políticas 5/33; Manual pp.20/27. Contrato candidato: docs/model-scenarios-price.md, línea 16. Estado financiero: abierto.

**M8-07 — Controles y vigencia por escenario**

Manual pp.17/29; traspaso §§6–7. C1/C2 completos por escenario requerido; versiones de fuentes/fórmulas/criterios coherentes y comparación sólo con resultados vigentes.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Manual pp.17/29; traspaso §§6–7. Contrato candidato: docs/model-scenarios-price.md, línea 17. Estado financiero: abierto.

**M8-08 — Robustez y Upside**

Master §4 Robustness; política 17/33. Upside no rescata Base. Ensayo histórico de terreno cero requiere configuración expresa; no llamar robusto a un FAIL sin prueba pertinente válida.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Master §4 Robustness; política 17/33. Contrato candidato: docs/model-scenarios-price.md, línea 18. Estado financiero: abierto.

**M8-09 — Precio evaluado, asking y objetivos**

Master §3 RLV; Estándares política 13; Q3 p.22. Definir conjunto de restricciones de precio; soporte bajo dos objetivos no es RLV completo aprobado de la casa.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Master §3 RLV; Estándares política 13; Q3 p.22. Contrato candidato: docs/model-scenarios-price.md, línea 19. Estado financiero: abierto.

**M8-10 — Dominio, factibilidad y extremos**

Traspaso §5; PRICE-01. Distinguir máximo alcanzado, supremo no alcanzado, conjunto vacío, no acotado o indeterminado. Tramos/discontinuidades y desigualdades explícitos.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Traspaso §5; PRICE-01. Contrato candidato: docs/model-scenarios-price.md, línea 20. Estado financiero: abierto.

**M8-11 — Método y cotización discreta**

Traspaso §§5/8; Master §3 RLV. No asumir monotonía global; verificar candidato y siguiente incremento permitido si hay grilla explícita; ni tick ni tolerancia inventados.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Traspaso §§5/8; Master §3 RLV. Contrato candidato: docs/model-scenarios-price.md, línea 21. Estado financiero: abierto.

**M8-12 — Entrega y comparaciones dependientes**

Traspaso §6; Master §§5–7. Entregar estado de soporte, restricciones activas, alcance validado y pendientes. Cambiar criterios recalcula objetivos dependientes; asking/RLV exige fórmula vigente.

Fuente original: Fuentes de Lorena/Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt; ubicación: Master §§3–6; Traspaso §6; Master §§5–7. Contrato candidato: docs/model-scenarios-price.md, línea 22. Estado financiero: abierto.

### M9 — Decisión, revisión y salida

Documento candidato: docs/model-decision-audit.md. Interfaz agregada: schemas/M9.schema.json.

**M9-01 — Paquete vigente y completo**

Traspaso §§6–7; C1/C2 Manual pp.17–18. Datos, aplicabilidad, fuentes, reglas y escenarios requeridos deben estar completos; sin dictamen parcial ante bloqueos.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §§6–7; C1/C2 Manual pp.17–18. Contrato candidato: docs/model-decision-audit.md, línea 11. Estado financiero: abierto.

**M9-02 — Criterios de Lorena por deal**

Master §5/Estándares §2; instrucción actual. Valores expresos, definición/unidad/período/escenario, operador, igualdad y revisión separados de términos bancarios. No heredar umbrales.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Master §5/Estándares §2; instrucción actual. Contrato candidato: docs/model-decision-audit.md, línea 12. Estado financiero: abierto.

**M9-03 — Comparación de cada métrica**

Estándares §2; traspaso §3. Comparar valor válido sin redondeo decisorio; preservar no aplicable justificado, indefinido, faltante y conflicto como estados diferentes.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Estándares §2; traspaso §3. Contrato candidato: docs/model-decision-audit.md, línea 13. Estado financiero: abierto.

**M9-04 — Bandas y agregación**

Master §6/política 17; confirmaciones del usuario. El objetivo binario no resuelve la banda entre PASS y FAIL histórica. Agregación y prioridades requieren regla explícita; si falta, PENDIENTE.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Master §6/política 17; confirmaciones del usuario. Contrato candidato: docs/model-decision-audit.md, línea 14. Estado financiero: abierto.

**M9-05 — Invalidación y reutilización**

Traspaso §§6–7; Manual prueba 14 p.29. Cambios de fuentes/datos/fórmulas invalidan descendientes; criterio solo permite conservar caja independiente pero recalcula comparaciones y precio objetivo.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §§6–7; Manual prueba 14 p.29. Contrato candidato: docs/model-decision-audit.md, línea 15. Estado financiero: abierto.

**M9-06 — Instantánea y concurrencia**

Traspaso §7. Resultados y decisión vinculados a una revisión inmutable, con registro atómico de vigencia; evitar mezcla entre corridas, reintentos y guardados interrumpidos.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §7. Contrato candidato: docs/model-decision-audit.md, línea 16. Estado financiero: abierto.

**M9-07 — Hoja externa de una página**

Traspaso §2; D1 p.1; Master §7. Render desde resultados enlazados; cifras, unidades, limitaciones y criterios legibles; exactamente una página PDF por deal.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §2; D1 p.1; Master §7. Contrato candidato: docs/model-decision-audit.md, línea 17. Estado financiero: abierto.

**M9-08 — Auditoría y discrepancias**

C4 Manual p.18/pp.39/50; PAR-08. Independencia de revisión y diferencias persistentes requieren evidencia; corregir render o escalar sin publicar; no afirmar auditoría sólo por cotejo de texto.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; C4 Manual p.18/pp.39/50; PAR-08. Contrato candidato: docs/model-decision-audit.md, línea 18. Estado financiero: abierto.

**M9-09 — Revisión humana auténtica**

Traspaso §§2/3/7. Identidad acreditada, alcance, versión, vigencia, decisión y revocación; nombre/casilla/approved:true insuficientes.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §§2/3/7. Contrato candidato: docs/model-decision-audit.md, línea 19. Estado financiero: abierto.

**M9-10 — Puerta al Full UW**

Traspaso §2; política 17. PASS aplicable y vigente más aprobación final auténtica. No significa aprobación final de inversión; Full UW diferido al final.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §2; política 17. Contrato candidato: docs/model-decision-audit.md, línea 20. Estado financiero: abierto.

**M9-11 — Registros internos separados**

Traspaso §7. Preservar originales/lecturas, entradas/supuestos, cálculo, comparaciones, revisión y PDF con relaciones claras; hash no prueba autenticidad.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §7. Contrato candidato: docs/model-decision-audit.md, línea 21. Estado financiero: abierto.

**M9-12 — Hito/release y límites**

Traspaso §§8/10/11. Versionar, verificar SHA remoto completo y exclusiones; no liberar producción por conteo de pruebas, prototipo o referencias sintéticas.

Fuente original: Pasted text.txt; ubicación: Traspaso §§2/3/6/7; Traspaso §§8/10/11. Contrato candidato: docs/model-decision-audit.md, línea 22. Estado financiero: abierto.

## 5. Integración de puertos y adapters

Los envelopes contienen 33 salidas agregadas. Son una interfaz mínima: los desgloses, conjuntos de raíces y demás resultados de los 84 contratos conservan sus registros/evidencias específicos. El registro no promete wiring ejecutable completo. Ningún consumidor convierte implícitamente unidades, bases, períodos, equivalentes o estados.

**M1.program_units → M2, M3, M4**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M1.building_gsf → M3**

GSF no se convierte en NRSF ni se reconstruye con ratio supuesto.

**M1.residential_nrsf → M2**

NRSF y GSF son bases distintas aun compartiendo dimensión física.

**M1.commercial_sf → M2, M3**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M1.parking_spaces → M2, M3**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M2.effective_income → M4, M7, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M2.operating_expenses → M4, M7, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M2.property_tax → M4, M7, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M2.noi → M6, M7, M8, M9**

NOI devengado no es cobro, caja distribuible ni NOI bancario por defecto; exigir período/base y ajustes expresos.

**M3.budget_before_financing → M4, M5**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M3.unallocated_scope_cost → M4, M5, M9**

Residual no asignado, incluso conocido distinto de cero, bloquea completitud del presupuesto afectado.

**M4.scheduled_uses → M5**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M4.unscheduled_uses → M5, M9**

Saldo no programado no se reparte ni convierte en cero; bloquear la financiación dependiente.

**M5.tdc → M8, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M5.construction_principal → M6, M7**

Principal no es payoff total; intereses/fees/otras obligaciones y corte requieren registros propios.

**M5.construction_payoff → M6, M7**

Exigir desglose, fecha, completitud y contrapartidas; no sumar de nuevo capitalización ya en principal.

**M5.equity_required → M6, M7, M9**

Necesidad de capital no acredita aporte recibido o capital disponible; M7 requiere movimientos brutos.

**M6.permanent_loan → M7**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M6.annual_debt_service → M7, M9**

Distinguir cuota equivalente anualizada y servicio efectivamente fechado. El equivalente de sizing no alimenta caja M7 sin calendario/amortización; tampoco se divide por 12 implícitamente.

**M6.construction_payoff → M7**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M6.restricted_reserves → M7**

Fondos restringidos no son distribución; exigir liberación/regla y movimientos separados.

**M6.refi_distribution → M7**

M7 recibe distribución bruta registrada; no sumar otra vez valor o proceeds del mismo refi.

**M6.refi_contribution → M7**

M7 conserva aporte bruto aunque coincida con distribución en el período.

**M7.gross_contributions → M8, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M7.gross_distributions → M8, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M7.equity_multiple → M8, M9**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M7.irr → M8, M9**

Si hay raíces múltiples/sin raíz/indeterminación, el agregado queda indefinido o bloqueado con causa y evidencia del conjunto de raíces; nunca exportar primera raíz como cantidad conocida sin política aplicable.

**M7.terminal_distribution → M8, M9**

Distinguir distribución realizada, valoración y escenario de liquidación; no duplicar valor terminal y venta.

**M8.supported_price_bound → M9**

Transportar dominio, objetivos, escenario, revisión y evidencia junto al importe. Soporte reducido no es RLV completo.

**M8.bound_kind → M9**

Máximo alcanzado, supremo no alcanzado, vacío probado, no acotado e indeterminado no son intercambiables; búsqueda parcial conserva indeterminación.

**M9.decision → external_one_page_report_design**

Faltantes/reglas/conflictos requeridos mantienen PENDING sin PASS/FAIL; faltan política completa y aprobación auténtica para uso real.

**M9.aggregation_rule_ref → internal_audit_design, external_one_page_report_design**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

**M9.comparisons → internal_audit_design, external_one_page_report_design**

Exigir misma definición y contexto, unidad/base/período compatibles y evidencia de cálculo vigente; adapter explícito si difieren.

## 6. Pasadas y ciclos que la lista de etapas no oculta

**LOOP-FINANCE** — Costo/base, calendario y financiación capitalizada/TDC: bloque circular explícito.

No certifica convergencia un grafo de etapas; método y tolerancias quedan explícitos/pending, solver futuro.

**PASS-BREAKEVEN** — M2-08 ocupación de equilibrio utiliza servicio de deuda de M6 después de su cálculo.

Pasada diagnóstica posterior a M6, separada de outputs base de M2. No retroalimentar NOI base sin dependencia y fórmula expresas.

**LOOP-SCENARIO-PRICE** — M8 reevalúa dependencias bajo escenario/precio.

Contextos aislados y cierre transitivo; no sumar sensibilidades ni inferir monotonía global.

**PASS-CRITERIA** — Cambio de criterios altera comparaciones y precio dependiente.

Invalidar dependientes. Conservar caja sólo si su independencia se acredita; publicación/registro atómico futuro.

## 7. Registros y referencias integradas

El vocabulario común y los registros detallados conservan contexto/versiones y afirmaciones originales. La normalización por unidades no autentica el dato. Cada perfil es una hipótesis recibida con dominio limitado; si no aplica, no se extrapola.

Perfiles disponibles: evidencia literal; inclusiones/alcance de costos; calendario y ledger de caja/principal/obligaciones; presupuesto a pagos; devengo operativo a caja; cierre bruto/refi/venta; cronología/disponibilidad/maturity; caja del equity a TIR; comparación por intervalos; trazabilidad por contenido; catálogo finito de precio; ranking con signo; soporte afín de dos objetivos; capacidad bancaria reducida.

**references/integrated-bridge-validation.json** — 14 controles declarados. One scoped M2-to-M7 cash/debt/equity bridge under declared synthetic assumptions. Not independent validation, original acceptance golden case, full circular-financing solver, production integration or product release.

**references/m2-validation.json** — 186 controles declarados. Isolated synthetic algebra; not approved tax policy, recovered product, historical reference reproduction, independent audit or deal validation.

**references/m34-validation.json** — 22 controles declarados. Isolated synthetic allocation algebra, not approved sin-squared schedule, actual construction scope, production or independent audit.

**references/m5-validation.json** — 36 controles declarados. Reduced synthetic algebra and explicitly assumed opening-balance capitalization; not production finance, actual loan terms, independent audit, global convergence or recovery of historical references.

**references/m6-validation.json** — 128 controles declarados. Synthetic regular end-period fixed-rate amortization, isolated loan sizing and unconstrained distributable cash. Not approved bank terms, independent audit, stable floating-point implementation, production or real-deal validation.

**references/m7-validation.json** — 65 controles declarados. Synthetic exit cash, gross equity ledgers, regular compounding and factored IRR examples only. No general root-isolation solver, XIRR, real-deal validation, independent audit, production or recovery of historical application.

**references/m8-validation.json** — 99 controles declarados. Isolated synthetic transformations, two-objective affine-cost/single-return branch, discrete/open domain examples and nonmonotone counterexample. Not production scenarios, global price solver, approved RLV, general IRR or independent audit.

**references/m9-validation.json** — 46 controles declarados. Isolated comparator truth tables and hypothetical explicit aggregation; not activated house decision policy, authentication, transactional publication, independent audit or production.

**references/revision-integrity-validation.json** — 29 controles declarados. Pure in-memory synthetic graph, snapshot identity and input-slot checks. Not actual financial dependency discovery, database atomicity, race-condition proof, authentication, persistent review or production integration.

**references/interface-contracts-validation.json** — 75 controles declarados. Candidate interface shapes and isolated arithmetic/block propagation. No financial defaults, full dependency/model integration, expert approval, authenticated identity or production release.

**references/calendar-ledger-validation.json** — 60 controles declarados. Explicit-date period-aggregate synthetic cash/principal/declared-interest-fee/gross-equity reference. Not bank conventions, intraday liquidity proof, complete bank/legal obligations, authentic statements, independent audit or production.

**references/cost-scope-validation.json** — 29 controles declarados. Declared synthetic economic-scope allocation and document-claim consistency only; no inferred inclusions, source authority, actual construction completeness, expert policy, TDC financing or production.

**references/evidence-locators-validation.json** — 21 controles declarados. Literal location/byte-integrity only on supplied originals and explicitly synthetic workbook fixtures. Not semantic extraction, independent readers, legal/official authenticity, financial interpretation, approval or production.

**references/budget-payment-bridge-validation.json** — 41 controles declarados. Exact explicit synthetic budget-schedule-payment linkage and underlying scoped references only. Not incurred-cost accounting, payable/retention certification, schedule-curve choice, bank eligibility, complete financial integration, real deal, independent audit or production.

**references/calculation-lineage-validation.json** — 48 controles declarados. Explicit synthetic dependency slots, local deterministic JSON digests, transitive content freshness and blocker preservation only. Not completeness of actual economic dependencies, recomputation of outputs, external-file validation, authentication, persistent immutability, concurrency/atomic publication or production.

**references/periodic-irr-isolation-validation.json** — 64 controles declarados. Isolated periodic rational-net-flow polynomial root counting/isolation on declared synthetic cases. Not XIRR, calendar-to-return integration, root-selection policy, annualization convention, global price optimization, independent financial audit, real-deal screening or production.

**references/investor-return-bridge-validation.json** — 43 controles declarados. Explicit synthetic aggregate-equity event/grid/gross-multiple/periodic-root bridge only. Not ledger completeness, real-deal economics, terminal valuation, LP/JV waterfall, automatic timing/annualization, XIRR, root-selection policy, expert review or production.

**references/return-metric-bridge-validation.json** — 31 controles declarados. Synthetic ledger-to-IRR interval/condition and declared calendar-month compounding only. Not root-selection/aggregation policy, threshold authority, actual frequency approval, XIRR, financial audit, publication or real-deal PASS/FAIL.

**references/operating-cash-bridge-validation.json** — 26 controles declarados. Declared synthetic M2 accrued-income/expense/working-balance to recorded operating cash reconciliation only. Not approved NOI/reserve/accounting/tax definitions, authentic balance inventory, automatic cash distribution, independent audit or production.

**references/settlement-bridge-validation.json** — 43 controles declarados. Explicit synthetic last-period gross-cash full-payoff settlement/ledger reconciliation only. Not actual obligation completeness, valuation/sizing approval, escrow/net-withheld counterpart inference, intraday order, distribution entitlement, tax/legal policy, independent audit or production.

**references/financing-timeline-validation.json** — 50 controles declarados. Explicit synthetic ordered atomic-record groups, nonnegative cash/debt/due snapshots, declared capacity/window/maturity and restriction-claim diagnostics only. Not discovered bank terms, legal interpretation, authority of documents, real intraday execution, complete commitments/covenants, solver, independent audit or production.

**references/price-grid-catalogue-validation.json** — 52 controles declarados. Exact finite uniform grid enumeration/intersection of explicitly supplied scenario-specific normalized-polynomial claims only. Not actual financial dependency recalculation, authenticated criteria/exclusions, continuous/global price optimization, approved RLV, economic feasibility, independent audit or production.

**references/sensitivity-ranking-validation.json** — 33 controles declarados. Declared synthetic numeric-input preservation, compatible measured-metric signed deltas, explicit direction/ties and separation of joint experiments only. Not actual perturbation generation, financial recomputation, authenticated ranking policy, causal/probabilistic inference, real-deal screening, independent audit or production.

**references/affine-price-support-validation.json** — 42 controles declarados. Typed declared positive affine-cost/price-independent NOI/single-initial-contribution-single-terminal-distribution profile; derived finite-grid two-objective conditions and exact candidate cash/linear-root checks only. Not full M1–M7 financial engine, approved price goals/Q3, calendar/annualization/bank/tax policy, general IRR selection, RLV, independent audit or production.

**references/refinance-capacity-bridge-validation.json** — 46 controles declarados. Declared synthetic annual-NOI/cap valuation, regular fixed nonnegative-rate arrears amortization, explicit capacity inventory and full selected-principal gross-closing comparison only. Not authentic bank underwriting/commitments, annual-rate conversion, dated debt service, funding/distribution rights, tax/valuation approval, complete financial integration, independent audit or production.

Estas referencias son aisladas o puentes sintéticos. No constituyen una única corrida financiera completa ni auditoría independiente. Las 36 especificaciones de aceptación siguen sin ejecutarse contra producto.

## 8. M9: decisión, revisión y página externa

Cada comparación requiere definición, valor/criterio, unidades, base, período, escenario y revisiones compatibles. Un intervalo que cruza umbral conserva pendiente de refinamiento; múltiples raíces no se reducen a una tasa conveniente. Un dato requerido ausente conserva PENDING aun cuando otra métrica incumpla una condición.

El diseño del PDF externo incluye identidad/estado/motivo, capital y plazos, métricas y criterios, sensibilidad/precio, riesgos y trazabilidad. Toda cifra debe enlazar a snapshot/cálculo vigente; exactamente una página legible. El PDF I01 de este paquete es documentación interna, no salida de un deal.

Autenticación de revisor, alcance/versión/vigencia/revocación, idempotencia y publicación atómica son requisitos futuros de implementación. Nombre o approved:true no acreditan revisión. Un PASS de screening no es aprobación de inversión ni admisión automática a Full UW.

## 9. Inventario final de dependencias externas

El registro final mantiene una disposición por cada una de las 398 filas, sin reescribir su estado o pendiente original; incluye los 35 temas existentes y separa requisitos del usuario de elecciones externas. No crea solicitudes de contacto.

**REVIEW-Q01 — Tratamiento de faltantes**

El usuario ya confirmó PENDING ante faltantes, sin PASS/FAIL. No esperar una nueva elección de Lorena para esta regla; aceptación del producto sigue futura. Estado de este índice: current_user_direction_effective. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q02 — Porcentaje/elegibilidad de exención**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q03 — Objetivos que definen RLV**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q04 — Costo de cada mes extra de obra**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q05 — Curva del hard cost bajo retraso**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q06 — NOI de lease-up excedente**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q07 — Equity hasta estabilización**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q08 — Definición de Equity/TDC**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q09 — Apalancamiento con equity bajo**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q10 — Impuesto durante obra**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 17 de R02.

**REVIEW-Q11 — Renta dormitorio o unit type**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q12 — Estrategia como entrada**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q13 — Otra deuda**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q14 — Tolerancia golden case**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q15 — Impuestos de cierre**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q16 — Impuesto a salida**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q17 — Desglose seguro**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q18 — Tasa fija/flotante**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q19 — Assessments no ad valorem**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-Q20 — Entregables**

Usuario exige un PDF externo de una página; archivos internos permitidos y Full UW diferido. No reinstalar el paquete histórico por la pregunta sin responder. Estado de este índice: current_user_external_output_direction_effective. Fuente: docs/professional-feedback-register.json; página 18 de R02.

**REVIEW-PAR-01 — Rangos por campo y reglas de aceptación**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-02 — Representación decimal/porcentual**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-03 — Convención de intereses**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-04 — Momento de flujos y TCO**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-05 — Convergencia de costo financiero**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-06 — Precisión/redondeo/comparación auditora**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-07 — Dominios oficiales aprobados**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-08 — Máximo de iteraciones redactor/auditor y escalamiento**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-PAR-09 — Reglas/diferencias toleradas de control cruzado GC**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página 19 de R02.

**REVIEW-SRC-01 — See requirements-conflicts.md finding SRC-01**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página None de R02.

**REVIEW-SRC-02 — See requirements-conflicts.md finding SRC-02**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página None de R02.

**REVIEW-SRC-03 — See requirements-conflicts.md finding SRC-03**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página None de R02.

**REVIEW-SRC-04 — See requirements-conflicts.md finding SRC-04**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página None de R02.

**REVIEW-SRC-05 — See requirements-conflicts.md finding SRC-05**

Registro sin respuesta profesional ni adopción de política. No contactar a terceros. Estado de este índice: external_evidence_or_applicable_rule_needed. Fuente: docs/professional-feedback-register.json; página None de R02.

**REVIEW-SRC-06 — See requirements-conflicts.md finding SRC-06**

DRAFT v5.2 y comparación de 40 diferencias no recuperados; no bloquear el diseño del input original verificado ni inventar esa comparación. Estado de este índice: historical_material_not_recovered. Fuente: docs/professional-feedback-register.json; página None de R02.

Adicionales: datos de cada deal y fuentes GC/banco; reglas financieras/fiscales aplicables y validación independiente; recuperación histórica ausente; conciliación Full UW diferida al final. No se exige que todo provenga de Lorena: su hoja/criterios son una parte del expediente.

## 10. Entregables para una futura implementación autorizada

**IMP-01 — Ingesta de fuentes y normalización completa**

Implementar lectores, versiones, rangos/aplicabilidad aprobados y evidencia por campo; no evaluar macros ni usar cache como fórmula propia. Módulos: M1.

**IMP-02 — Motor financiero completo y dispatcher de perfiles**

Implementar los 84 contratos y reglas aplicables; no sustituir ramas generales por fixtures o perfiles reducidos. Módulos: M2, M3, M4, M5, M6, M7.

**IMP-03 — Calendarios, servicio fechado y liquidaciones**

Integrar cronología real, pagos parciales, fees retenidos/escrow, vencimientos y obligaciones con contrapartidas; adapters expresos. Módulos: M4, M5, M6, M7.

**IMP-04 — Solvers y validación numérica**

Implementar métodos aprobados, convergencia, residual/error, ramas múltiples/indefinidas, XIRR y dominio de precio; no inferir precisión de ejemplos. Módulos: M5, M7, M8.

**IMP-05 — Escenarios y estado de decisión**

Aplicar inventarios/criterios por deal, política explícita de agregación/bandas y completitud; sin herencia o FAIL por datos ausentes. Módulos: M8, M9.

**IMP-06 — Persistencia y procedencia**

Snapshots inmutables persistidos, dependencias completas, invalidación, reintentos/idempotencia y registro atómico de vigencia. Módulos: M1, M8, M9.

**IMP-07 — Revisión y publicación**

Autenticación, alcance/vigencia/revocación de revisión; generar exactamente una página externa legible desde un snapshot vigente y publicación atómica. Módulos: M9.

**IMP-08 — Aceptación integrada e independiente**

Ejecutar los 36 setups contra producto y expected results independientes con tolerancias aplicables; controles sintéticos no los certifican. Módulos: M1, M2, M3, M4, M5, M6, M7, M8, M9.

**IMP-09 — Runtime, operación y recuperación**

Después de autorización: despliegue, observabilidad, backups de datos/runtime, restauración comprobada. GitHub actual preserva fuentes/especificaciones/referencias. Módulos: M9.

## 11. Aceptación futura y casos frontera

Los casos siguientes son especificaciones, no pruebas de producto pasadas. Las referencias matemáticas asociadas aportan evidencia acotada y no sustituyen expected results independientes.

**ACC-01 — Golden case against independent model**

Fuente: Manual v2.2 physical p.28, case 1. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-02 — Required blank**

Fuente: Manual v2.2 physical p.28, case 2. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-03 — Explicit zero**

Fuente: Manual v2.2 physical p.28, case 3. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-04 — TBD numeric**

Fuente: Manual v2.2 physical p.28, case 4. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-05 — Percentage scaling under approved representation**

Fuente: Manual v2.2 physical p.28, case 5. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-06 — Conflicting original documents**

Fuente: Manual v2.2 physical p.28, case 6. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-07 — Exact criterion equality**

Fuente: Manual v2.2 physical p.28, case 7. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-08 — Conditional exemption dependency**

Fuente: Manual v2.2 physical p.28, case 8. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-09 — Deterministic identical snapshot**

Fuente: Manual v2.2 physical p.28, case 9. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-10 — 1101 source-reader regression**

Fuente: Manual v2.2 physical p.29, case 10. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-11 — Missing applicable expert rule**

Fuente: Manual v2.2 physical p.29, case 11. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-12 — Citation absent in original**

Fuente: Manual v2.2 physical p.29, case 12. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-13 — Official number absent in retained copy**

Fuente: Manual v2.2 physical p.29, case 13. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-14 — Changed source invalidation**

Fuente: Manual v2.2 physical p.29, case 14. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-15 — Financing nonconvergence**

Fuente: Manual v2.2 physical p.29, case 15. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-16 — Sources/uses mismatch in a scenario**

Fuente: Manual v2.2 physical p.29, case 16. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-17 — DSCR binding**

Fuente: Manual v2.2 physical p.29, case 17. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-18 — Upside cannot rescue Base**

Fuente: Manual v2.2 physical p.29, case 18. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-19 — Configured robustness before FAIL**

Fuente: Manual v2.2 physical p.29, case 19. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-20 — Manual/unlinked PDF number**

Fuente: Manual v2.2 physical p.29, case 20. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**ACC-21 — Unresolved audit after allowed retries**

Fuente: Manual v2.2 physical p.29, case 21. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-01 — Zero remaining equity produces undefined CoC**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-02 — Gross contributions/distributions survive same-month netting**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-03 — IRR multiple/tangent/no-root/all-zero cases**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-04 — Irregular dates do not silently become monthly IRR**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-05 — Maturity before sale without documented financing**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-06 — Reserve restriction and fee/payoff double-count prevention**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-07 — Scenario input/criterion isolation**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-08 — Open price supremum not permitted maximum**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-09 — Nonmonotone/disconnected price feasibility**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-10 — Discrete quote and next tick under explicit grid**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-11 — Stale/revoked or fabricated reviewer identity**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-12 — Concurrent edit between preparation and atomic publication**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-13 — Interrupted save/retry must not duplicate current decision**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-14 — PDF one-page/legibility/units tied to current snapshot**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

**NEW-ACC-15 — Historical HOLD-to-binary band remains pending without policy**

Fuente: Current handoff §§3–7 and M1–M9 proposed contracts. Estado: specified, not executed against product. Evidencia independiente/producto: no aportada.

## 12. Comprobación de los ocho entregables de esta fase

**D01 — Fuentes y entradas**

16 originales preservados, 19 ocurrencias, 55 campos y 10 criterios vacíos indexados. Evidencia: docs/source-register.json, docs/input-contract-map.json, templates/project-draft-empty.json.

**D02 — Contratos M1–M9**

84 contratos con documento/línea y fuente original/ubicación; nueve envelopes candidatos. Evidencia: docs/structural-integration-register.json.

**D03 — Rutas y dependencias**

33 puertos agregados con consumidor, requisitos de transporte y cuatro bucles/pasadas explícitos. Evidencia: docs/structural-integration-register.json, docs/module-execution-design.json.

**D04 — Tipos y referencias acotadas**

33 schemas y 25 suites previas inventariadas con sus límites; ningún perfil reducido certifica el modelo general. Evidencia: schemas/README.md, docs/reference-runner-map.json, docs/package-readiness.json.

**D05 — Decisión y salida**

Contrato M9 conserva PENDING, revisión auténtica, PDF externo de una página y puertas futuras. Evidencia: docs/model-decision-audit.md, docs/decision-input-contract.md.

**D06 — Pendientes y aceptación**

35 temas y 398 filas indexados, 36 setups sin certificar y nueve entregables de implementación futura. Evidencia: docs/final-dependency-register.json, docs/acceptance-case-contracts.json.

**D07 — Especificación integral I01**

Documento español y PDF nuevos; R01/R02 preservados sin atribuir revisión profesional. Evidencia: docs/Especificacion_Integral_Armado_I01.md, docs/review/MiniUW_Especificacion_Integral_Armado_I01.pdf.

**D08 — Verificación y respaldo**

Validador de consistencia, suites en copia temporal, workflow y comprobante externo de commit/CI/ZIP. Evidencia: references/structure-closeout-validation.json, tools/check_reference_package.py, .github/workflows/model-reference-checks.yml.

La comprobación estructural exige concordancia de IDs/documentos/puertos, referencias locales resolubles, inventarios completos y guardas conservadas. Un comprobante externo identifica SHA completo, verificación de blobs remotos y resultado CI del commit exacto; el ZIP incluye ese comprobante.

## 13. Límites finales y control de cambios

R01 y R02 permanecen intactos. La revisión pendiente sigue vinculada a R02; I01 no atribuye aprobación al profesional ni altera su formulario vacío. Las nuevas observaciones deberán indicar corte, contrato y evidencia.

El armado independiente queda publicable cuando pasan sus verificaciones locales y remotas. El modelo financiero completo, la implementación, las decisiones reales, la recuperación original y las aprobaciones conservan sus estados pendientes. Evidencia o alcance nuevo puede requerir una versión posterior del diseño, sin convertir el corte actual en una afirmación universal de completitud.
