# Si invierto USD 10, ¿cuánto cobro y cuándo?

## D265 · Cierre de regresión del Mini-UW v1 y preparación del piloto

**Las 1.715 pruebas unitarias del corte D264 pasaron, sin fallos, errores ni omisiones.** Pasaron también los controles de vacíos/cero, las 26 suites de referencia, la corrida integral y la aceptación técnica de punta a punta. La verificación se realizó en el VPS con datos sintéticos y sobre una copia limpia cuya integridad se comprobó antes y después.

El motor probado muestra aportes y cobros por fecha, refi, operación, venta y caja sin recuperar por cada USD 10 de equity inicial. No se recibió un nuevo proyecto para esta verificación. No se publican sus cifras sintéticas como retorno de un caso real ni como retorno personal del inversor sin términos de reparto.

**Resultado de cierre:** el perfil implementado queda con regresión verificada y preparado para recibir un expediente en un piloto asistido. **No equivale a haber implementado o aprobado todas las 33 políticas.** Permanecen las brechas que se detallan abajo; no se ocultan bajo un porcentaje de avance. La decisión real y el retorno histórico siguen PENDING. No hubo despliegue ni activación de reglas financieras pendientes.

### Corte comprobado

- Código: [`ff4e823117ec4543d9754cda4ef9ccfb0789359a`](https://github.com/brodskyfederico-commits/Mini-UW/commit/ff4e823117ec4543d9754cda4ef9ccfb0789359a).
- Manifiesto SHA-256: `70210942c62c039178cea9db1827144a2da2c72786cc22288cbe7c1a021fe35b`; 2.042 archivos enumerados más el propio manifiesto.
- Inicio: 2026-11-19T19:36:20Z. Fin: 2026-11-19T22:01:08Z. Duración total: 144.80 minutos.
- Unitarias: 8037.037 segundos. El tiempo de esta batería corresponde a verificar el código y sus expedientes de ensayo; no es una medición del tiempo de análisis de cada deal.
- [Constancia con comandos, resultados y hashes de logs](MiniUW_Validacion_D265.json). La evidencia local conserva los logs completos y la copia comprobada.

### Qué pasó la batería

| Control | Resultado y alcance |
|---|---|
| 55 campos, Base y Downside | 440 vacíos con valor nulo: 436 PENDING y 4 N/A declarados, sin convertirlos en cero. 98 ceros numéricos explícitos preservados; 12 ceros rechazados en campos no numéricos. |
| Batería unitaria | 1.715/1.715; salida `OK`, sin omisiones. Incluye las conexiones D253–D264 y los controles anteriores de fuentes, caja, deuda, retornos, criterios, revisiones y entrega. |
| Referencias | 26 suites, integridad de 2.043 archivos, fuentes originales y 398 filas de cobertura histórica. Ese inventario no constituye una nueva certificación de cobertura financiera total. |
| Corrida integral D102 | Caja por USD 10, recuperación, fondeo, venta sin refi, bloqueos y un PDF de una página. |
| Aceptación D200 | Checklist técnico 16/16. Caso completo PASS simulado; adverso FAIL simulado; incompleto PENDING; corregido PASS simulado. El dictamen real de todos continúa PENDING. |
| Conciliaciones D200 | Cotejo independiente de NOI, deuda, venta, aportes, cobros y TIR; fuentes/usos por período, caja libre/restringida, reparto sintético y vecinos del RLV. |
| Vigencia de la entrega | Las pruebas rechazan revisiones anteriores, respaldo o PDF alterado, cambios entre auditoría y publicación y caja incompleta. Sólo se entrega la revisión auditada vigente del perfil probado. |
| Integridad final | El manifiesto y los 2.042 archivos de la copia y del origen coinciden después de la batería. |

Después de la batería se reprodujo además con B16 el expediente archivado D263 `precision-v11`: VIGENTE para su revisión sintética designada, PDF sin cambios y decisión real PENDING. Es una comprobación de compatibilidad histórica, no una aprobación del expediente para uso real. La constancia adicional y el hash de su log están en el JSON de validación.

### Conexiones verificadas en el bloque D254–D264

Cada grupo tiene cambios individuales y conjuntos compatibles, entradas y respaldos explícitos, conciliaciones y controles PENDING. No constituyen por sí solos el escenario automático universal de las 33 políticas.

| Entrada | Propagación y evidencia |
|---|---|
| Renta, vacancia, comercial y crecimiento | C8–C11, C14–C19 y C75–C76 a renta, gastos, NOI, capacidad y caja. [D254](../workbook-operating-sensitivities-D254.md). |
| Presupuesto y calendario | C37–C42 y C46–C47 a usos, anticipos, aportes, draws, intereses y fechas. [D255](../workbook-budget-sensitivities-D255.md), [D256](../workbook-calendar-sensitivities-D256.md). |
| Deuda de obra | C51–C53 a compromiso, giros, interés, comisión y cierre, con cotización PDF por variante. [D257](../workbook-construction-sensitivities-D257.md). |
| Gastos y reservas | C57–C60 a gastos, depósitos, caja restringida y liquidación. [D258](../workbook-expense-sensitivities-D258.md), [D259](../workbook-reserve-sensitivities-D259.md). |
| Impuesto | C61–C62 a impuesto, NOI y capacidad, preservando el tratamiento de salida del perfil. [D260](../workbook-tax-sensitivities-D260.md). |
| Refi y venta | C66–C68 a valor, precio, costo porcentual, capacidad y cierre. [D261](../workbook-pricing-sensitivities-D261.md). |
| Deuda permanente | C69–C72 a cuota, saldo, capacidad LTV/DSCR/debt yield y retorno. Respaldo bancario y anexo por revisión. [D262](../workbook-permanent-sensitivities-D262.md). |
| Precisión y entrada original | Transporte exacto optativo hasta 1.300 dígitos, sin redondear cálculos, con algoritmos fijados por hash y sin modificar sus variables globales. C69 = 5,01 %/6,51 % llega desde XLSX y PDF hasta caja y comparador integrado. [D263](../workbook-exact-cash-D263.md), [D264](../workbook-integrated-transport-D264.md). |

### Pendientes reales que esta batería no cierra

La [auditoría D252](../worksheet-policy-implementation-audit-D252.md) ya distinguía componentes existentes de políticas parciales. Los grupos nuevos amplían la propagación probada, pero no resuelven automáticamente los siguientes puntos. [Registro estructurado con fuentes y efectos](MiniUW_Alcance_y_Pendientes_D265.json).

| ID | Falta / efecto | Qué lo cierra |
|---|---|---|
| TEC-01 | Perfil integrado general de cinco años desde estabilización y otra duración documentada. Los calendarios ensayados conservan sus ventanas; tener un motor de TIR u horizonte largo separado no completa esta conexión. | Implementar y cotejar operación, deuda, reservas, NOI forward, venta, TIR y múltiplo del mismo expediente a ese horizonte, sin imponer un default no aprobado. D252 #15–16. |
| TEC-02 | Orquestador único de todos los drivers, excepciones y Upside. Los grupos probados no equivalen a derivar automáticamente los 15 shocks desde Base. | Integración de todos los grupos y autorización de defaults/excepciones frente a CUR-01 y REQ-06. D252 #3 y #18–33. |
| TEC-03 | Renta asequible regulada con AMI, tope y utility allowance. Los gastos por servicios no sustituyen ese cálculo. | Productor y evidencias de regla, vigencia, unidad, elegibilidad y comparables. Observación adicional D252. |
| POL-01 | GBA derivado y materialidad con conflicto de autoridad SRC-01. | Resolver fuente/método autorizado y después implementar el takeoff auditable; mientras falte área respaldada, PENDING. |
| POL-02 | Beneficios fiscales condicionales, materialidad y stress/orden de reglas con incertidumbre. | Evidencia aplicable y política aprobada, seguida de la implementación correspondiente. D252 #5, #6 y #29. No se asume un beneficio. |
| POL-03 | Criterios por revisión, RLV por estrategia, control específico de equity bajo y precedencia ante faltantes. | Confirmaciones con alcance y versión más conexiones aún pendientes. D252 #11, #13, #14 y #17. La banda intermedia conserva PENDING. |
| PIL-01 | Datos y términos reales, responsables y cotejo del caso. | El expediente que aporte el usuario, las confirmaciones aplicables y la revisión financiera independiente. No es un nuevo ejercicio sintético. |
| VAL-01 | Confiabilidad empírica del OCR y del análisis sobre expedientes reales. | Medir falsos verdes por dato crítico, backtest y corridas en paralelo. Las pruebas sintéticas no certifican cero falsos verdes en cualquier PDF real. |

TEC-01 y parte de TEC-02 son trabajo técnico; no se presentan como simples datos que deba completar Lorena. Las condiciones fiscales, de área derivada y de criterios tienen además decisiones o evidencias previas. No se trasladan estos requisitos a Full UW como si se hubieran cerrado.

### Cómo sigue el caso real

1. Inventariar los archivos aportados y sus huellas; distinguir hechos documentados, supuestos autorizados y faltantes. Mantener los originales intactos y fuera de los commits de código.
2. Mapear unidades/áreas, rentas, costos, calendario, deuda, impuestos y salida. Localizar cada dato en su fuente. Un vacío sigue vacío; un cero necesita respaldo y dominio válido.
3. Comprobar que la estrategia, horizonte, frecuencia de deuda y formatos estén soportados. Una rama no implementada queda identificada como tal; no se completa con aproximaciones silenciosas.
4. Ejecutar Base/Downside para lo calculable y conciliar cada aporte y cobro en USD del proyecto. Normalizar después por `10 / aporte inicial verificado`, con aportes posteriores separados, fechas, refi, operación, venta y caja sin recuperar.
5. Aplicar sólo criterios documentados y vigentes para ese expediente, separados de condiciones bancarias. Si falta un criterio, el dictamen afectado sigue PENDING; la caja con respaldo puede seguir visible. Sin reparto real, el retorno personal sigue PENDING.
6. Cotejar de forma independiente y entregar un único PDF de la revisión vigente. PRELIMINAR no emite PASS formal; los faltantes mínimos o la capacidad excedida impiden el ranking cuando corresponde. Ningún PASS simulado autoriza inversión o despliegue.

El [paquete del piloto D190](piloto-real-D190/README.md) conserva el checklist de fuentes, criterios, responsables y cotejo. El Full UW sigue separado y su workbook no se exige como condición para avanzar con el Mini-UW autorizado.

Esta constancia documenta el corte probado. El commit de cierre incorpora documentación y resultados de prueba; conserva los bytes del código D264. Excluye credenciales, expedientes reales, runtimes, logs completos y paquetes de ejecución generados. La copia y los logs locales permiten auditar esta corrida.
