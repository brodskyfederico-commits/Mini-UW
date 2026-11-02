# Continuidad de caja durante la tenencia y retornos encadenados

T27 concilia un calendario explícito de planes operativos consecutivos, reproduciendo NOI y caja de cada período antes de usar sus saldos. T28 incorpora en una sola compilación los aportes y repartos conciliados a movimientos vacíos expresamente vinculados del inversor y recalcula los retornos. Un período omitido, saldo discontinuo o dato requerido ausente bloquea la cadena completa; no se reinicia caja en cero ni se elimina un año sin reparto.

El alcance es la continuidad matemática del plan operativo declarado. No acredita completitud económica, saldos iniciales, derechos de distribución, pagos reales, calendario bancario o caja de todo el proyecto. Refinanciación, venta, construcción y otros flujos fuera del enlace operativo conservan evidencia y pendientes propios.

## Ejemplo sintético de tres años

| Año de cobro | Caja operativa | Reparto propuesto | Caja libre final | Reserva final |
|---|---:|---:|---:|---:|
| 2027 | 955 | 100 | 410 | 230 |
| 2028 | 0 | 0 | 410 | 230 |
| 2029 | 1.280 | 200 | 995 | 360 |

La caja operativa suma 2.235 y los repartos propuestos 300. El año 2028 es una afirmación cero explícita, con sus saldos conservados; no se deduce que un documento ausente significa cero. Los seis saldos coinciden en ambas fronteras, produciendo doce comprobaciones exactas de continuidad.

El plan inicia con caja libre 50 y restringida 100, cobra 3.090 y paga 855 de operación. También declara principal 400, interés 200, fees 10, inversión 100 y otros pagos 20. Los depósitos de reservas suman 300 y las liberaciones 40: son transferencias internas, no ingresos o retornos adicionales. La conservación total se verifica sin duplicarlas:

`50 + 100 + 3.090 = 855 + 400 + 200 + 10 + 100 + 20 + 300 + 995 + 360 = 3.240`.

El ledger del inversor declara aporte inicial 1.000 al 2026-12-31, refi suministrada 500 al 2027-12-31 y venta suministrada 900 al 2029-12-31. Los tres repartos operativos se conectan a caja: 100, 0 y 200. Normalizando sobre el aporte inicial expresamente elegido: aporte 10; refi 5; operación 1, 0 y 2; venta 9; cobros 17; ganancia de caja 7; EM 1,7x. La TIR conserva un intervalo anual certificado, sin seleccionar una tasa redondeada para decidir.

El vector neto completo es `[-1.000, 600, 0, 1.100]`: se mantiene el cero central para respetar el tiempo. La caja libre/reservada final y el valor retenido declarado permanecen separados de los cobros del inversor. No se propone distribuir esos saldos automáticamente ni se interpreta su suma como capital aún invertido.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_holding_cash_returns.py
```

## Calendario, fuentes y saldos

El manifiesto necesita contexto sintético, moneda, horizonte, referencia de base temporal, inventario declarado completo y lista ordenada de períodos. Cada período lleva identidad, inicio/final, fecha de cobro y hashes exactos de fuente/ejecución NOI y especificación/ejecución de caja. Las fechas definen intervalos semiabiertos; primer inicio y último final deben cubrir el horizonte declarado y cada inicio posterior debe coincidir con el final anterior. No hay ordenamiento, interpolación, compresión de ceros o crecimiento supuesto.

`reconcile_holding_cash` reproduce todos los paquetes suministrados, incluso los adicionales no incluidos en el calendario. Faltan o sobran períodos: bloqueado. Un paquete alterado con hash nuevo se rechaza si no reproduce sus fuentes. El inventario no se considera acreditado por marcarlo completo.

En cada frontera compara exactamente cuatro saldos de trabajo —cuentas por cobrar, ingresos anticipados, cuentas por pagar y gastos anticipados— y caja libre/restringida. Conserva ambas afirmaciones, referencias y su igualdad. Literales racionales equivalentes se comparan por valor sin tolerancia inventada. Los bloqueos locales conservan su causa y dejan la continuidad pendiente; no se usan importes disponibles para emitir una cadena parcial como completa.

Sólo una cadena conciliada permite sumar recibos, pagos, aportes, repartos y otros movimientos del perfil y comprobar conservación global con las aperturas/cierres extremos. No suma saldos de cierre de distintos años como si fueran cobros. El transporte admite hasta 65 períodos y 8 MiB de fuentes de períodos, además del manifiesto acotado; los cálculos conservan el límite racional de 4.096 bits. Agotarlo bloquea la exportación incluso si cada período aislado era válido.

## Compilación de retornos y recuperación

`assemble_holding_returns` reproduce T27 y verifica hashes del manifiesto, ejecución y ledger original, contexto, moneda e inventario de bindings. Cada período necesita su propio movimiento operativo vacío, incluso cuando el reparto es cero. Un aporte positivo necesita un movimiento bruto adicional independiente; no se netea contra el reparto. Los targets deben coincidir en clasificación, fecha, moneda y punto de la cuadrícula del inversor.

Todos los targets se validan antes de cambiar la copia en memoria. Un target ya poblado, repetido, faltante o incompatible impide toda la compilación. También se bloquean movimientos operativos/aportes adicionales dentro del horizonte que no estén vinculados; no se dejan cifras operativas sin reconciliar como si pertenecieran al conjunto validado. Otros eventos se conservan expresamente fuera de este enlace, incluida la refi/venta suministradas. Su presencia no acredita conciliación de toda la caja del proyecto.

La fuente compilada conserva procedencia por hash de ejecución de caja y JSON Pointer del importe de cada evento. El original permanece intacto. T23–T24 recalculan aportes/cobros brutos, ganancia, EM, caja anual y TIR sobre el ledger completo, manteniendo pendientes de otros campos/criterios y sin elegir una tasa favorable.

Los archivos locales nuevos capturan manifiesto, todas las fuentes NOI/caja, ejecuciones, binding y compilación en una transacción por paquete. Al reabrir, verifican bytes, versiones, definiciones y reproducción completa, incluyendo períodos con cero. El ejemplo recupera ambos paquetes y verifica el enlace entre sus hashes. Son capturas separadas, sin atomicidad distribuida o publicación financiera; las bases temporales quedan excluidas de GitHub y ZIP. Los productores anteriores a un NOI compilado, como T22 residencial, requieren sus propios paquetes enlazados.

## Evidencia y límites vigentes

21 pruebas T27 y 18 T28, 39 nuevas y 541 técnicas en total. Incluyen conservación independiente, doce comprobaciones de saldos, ceros, reinicios de las seis familias, igualdad racional exacta, huecos/solapamientos/orden, fuentes faltantes/adicionales, hashes/contexto, dato faltante, límites técnicos reales, compilación sin cambios parciales, aportes brutos, paridad con T26 de un período, intervalos de TIR verificados contra el polinomio y recuperación con fallos/alteraciones.

La matriz incremental acompaña cada regla con ubicación exacta, definición, módulo, pruebas y pendientes. La matriz original de 398 filas y los 16 originales permanecen intactos. No se cierran los 36 casos financieros originales ni los 56 escenarios de diseño D02/D03.

Pendientes independientes: liquidación de refinanciación y venta con obligaciones de deuda a fecha, financiación/presupuesto de construcción, conciliación de caja contractual frente a pagos, escenarios/riesgos e integración de la salida final del inversor. Políticas reales, LP/JV/waterfall, fiscalidad y aprobación profesional conservan su evidencia pendiente. Decisión PENDING; sin despliegue o cierre financiero.
