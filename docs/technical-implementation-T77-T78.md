# T77–T78 — gastos durante la tenencia y retorno hasta venta

## T77: recorrido completo con detalle de gastos

Se reproduce el paquete T75 de compra/obra, continuidad de deuda, operación y venta, incluido su retorno T74. Un manifiesto nuevo liga los bytes exactos de ese paquete y de cada detalle T76. El inventario ordenado debe contener todos los períodos del manifiesto operativo, sin extras. Cada prueba T76 se reconstruye con las fuentes NOI/caja de ese mismo período; no se permite adjuntar otra conciliación compatible en apariencia. Contexto, moneda, inventario completo y bases de continuidad/clasificación son expresos.

El perfil mantiene el mismo inventario de conceptos durante toda la tenencia, incluidos ceros explícitos. La identidad de cada concepto comprende su ID de detalle, clase y el ID de gasto de la fuente NOI, o el objetivo único de impuesto calculado. Cambiar el orden de filas no cambia su significado; sustituir un concepto o reclasificarlo requiere otro perfil/revisión. No se infiere un cero para un gasto omitido.

Por concepto, el saldo final por pagar/prepagado de un período debe igualar su apertura siguiente. Se prohíbe reutilizar IDs o referencias de pago entre períodos en este perfil sin particiones. Que cuadren los saldos agregados no demuestra continuidad por concepto. T76 conserva además sus controles individuales, fechas, inventarios y pagos. Los saldos en la compra/obra y liquidación de venta permanecen sujetos al alcance reducido T73/T63: este bloque no inventa devengos históricos o liquidaciones faltantes.

Sólo cuando el recorrido T74 y todos los detalles/continuidades son compatibles se expone su ledger y retorno: exactamente los ya reproducidos, sin restar otra vez impuestos/seguros, sumar prepagos a cobros ni añadir financiación. Se conserva el resultado negativo, todas las raíces/intervalos de IRR y el alcance de equity agregado. Un detalle bloqueado retira los retornos exportables en este nuevo camino aunque el cálculo agregado anterior cuadre; el paquete anterior se conserva como evidencia histórica, sin aprobar inversión. Capital, CoC, equity retenido y reparto personal conservan sus pendientes.

El paquete portable JSON, acotado a 24 MiB, contiene el paquete histórico exacto, manifiesto y resultado. Se verifican versiones y reproducción completa de todas las fuentes y resultados; recomputar hashes de una falsificación no basta. Casos compatibles y bloqueados se recuperan sin ejecutar instrucciones o buscar fuentes externas.

## T78: vigencia e informe interno

El control actual requiere todo el inventario de fuentes T75 más el manifiesto de gastos, cada detalle de período y el transporte nuevo. No sustituye las fuentes viejas por la fecha de un manifiesto reciente. Exige T46 reproducido al mismo instante UTC explícito, contexto e inventario exactos de ID/hash/localizador. Todos deben estar vigentes según las declaraciones sintéticas y todos los cálculos deben ser compatibles antes de exponer cifras actuales.

La vista interna reutiliza el formato T56 para aportes/cobros, normalización, EM/IRR y riesgos; agrega el puente de gastos/pagos por período. Ante vencimiento, revisión pendiente, estimación, sustitución, cambio de contexto o fallo de cálculo, retira las cifras actuales conservando hashes, motivos y evidencia histórica recuperable. No adopta TTL, reloj vivo, monitor, autoridad documental, política de inversión o revisión profesional por declarar una fecha o aceptación de prueba.

Ambos componentes son optativos y sintéticos, sin modificar fuentes/paquetes anteriores, criterios vacíos ni I01. No acreditan contratos, cobertura del seguro, reglas/vencimientos fiscales, pagos, saldos o financiación reales; tampoco un cierre completo de activos/devengos/TDC, retorno personal, aceptación financiera o PDF externo. PENDING, sin despliegue ni decisiones reales.
