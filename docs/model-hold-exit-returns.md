# M7 — Tenencia, venta y retornos del inversor

Estado: doce contratos candidatos, referencias matemáticas propias y sintéticas. No es producción, auditoría independiente, aprobación de inversión ni modelo bancario validado. Full UW continúa diferido hasta el final. Los umbrales de Lorena siguen vacíos por deal; datos/reglas faltantes dejan PENDIENTE sin PASS/FAIL.

## Fuentes y contratos

Originales: Reglas de la casa v5.1, §3 Refinance and metrics (SHA-256 95a304fd3e535f16ebd5eb6abf0b223c211f9f596727c878de720779f7ceb701); Estándares políticas 2,12,15,16,31, texto DOCX política 15 párrafo 133 y política 16 párrafo 134 (38b78d40013b9338511d2917de6c4347be1ec812712b4b4b18e7308bb6c28ab9); Input Sheet Inputs!C67:C68/C75:C76 (b433468ec6cb2ebf6b9950325fef212dc9df365ac9adbca4895ca1df39234600). Manual físico pp.11–14/20/23–24 y traspaso actual §5. No se aprueban por copia las reglas numéricas históricas.

| ID | Salida | Fuente / definición pendiente |
|---|---|---|
| M7-01 | Estrategia, horizonte y fechas | Master §3 Hold; Estándares política 16; Manual p.20/Q12 p.24. Horizon explícito por deal; distinguir TCO, estabilización, refi y venta. Cinco años es referencia histórica, no valor activo por defecto. |
| M7-02 | Operación y crecimiento durante tenencia | Inputs C75:C76; Master §3 Hold; Manual pp.11/14. Rentas y gastos crecen por componentes y fechas expresos. No aplicar crecimiento de rentas a todo el NOI ni suponer impuesto constante. |
| M7-03 | Caja operativa, deuda y fondos restringidos | Master §3 CoC/Hold; Estándares política 12. Cobros/pagos, devengo, servicio de deuda y reservas separados; no distribuir NOI automáticamente ni usar caja restringida. |
| M7-04 | Capital adicional y distribuciones brutas | Estándares políticas 9/10/15/16; traspaso §5. Registrar aportes/distribuciones de cada evento, aunque ocurran en el mismo período. Requerimiento de equity no prueba capital disponible. |
| M7-05 | NOI forward y valor de salida | Master §3 Hold; Estándares política 31; Inputs C67. NOI del período forward y exit cap compatibles. Definir ventana, estabilización, impuestos y fecha; valoración no es cobro realizado. |
| M7-06 | Costos y liquidación de venta | Master §3 Hold; Inputs C68; Q16. Precio bruto, costos, impuestos aplicables documentados, ajustes, liberación de reservas y caja previa sin doble cuenta. No presumir reglas fiscales. |
| M7-07 | Deuda y obligaciones pendientes a salida | Master §3 Hold, loan balance; contrato M6-07/M6-08. Usar saldo a fecha de venta y obligaciones adicionales. No descontar otra vez principal ya amortizado ni inventar extensión/refi para cubrir maturity. |
| M7-08 | Proceeds al inversor y caja terminal | Estándares políticas 15/16; traspaso §5. Separar venta neta, distribución, aporte y caja retenida. Un residual negativo exige clasificación y fuente, no una distribución negativa encubierta. |
| M7-09 | Equity Multiple | Estándares política 16; Master §3 Equity Multiple. Distribuciones/proceeds incluidos sobre aportes brutos incluidos. Definir alcance y excluir doble cuenta de valor terminal/venta. |
| M7-10 | IRR regular y anualización | Estándares política 15; Master §3 monthly IRR annualized. Calendario, frecuencia, dominio y raíces explícitos. No seleccionar una raíz conveniente; no inferir raíces del número de cambios de signo. |
| M7-11 | Fechas irregulares y retorno corriente | Traspaso §5; Estándares políticas 12/15. XIRR requiere fechas y fracción de año aprobada. CoC requiere período/base de capital remanente; denominador cero permanece indefinido. |
| M7-12 | Nivel proyecto, LP/JV y salida a M8/M9 | Estándares políticas 2/15/16; Manual p.20. Mantener retornos agregados del equity del proyecto. LP, fees/promote/waterfall sólo con estructura documentada y ledger conciliable separado. |

## Horizonte, crecimiento y fronteras de período

Debe existir un calendario que identifique primer/último período operativo, momento de cada aporte/distribución, refi, madurez de deuda y fecha de venta. La ventana de tenencia desde estabilización no es necesariamente igual al período de flujos del inversor, que puede comenzar en compra/obra. No omitir sus aportes preestabilización al calcular retornos.

Para crecimiento anual efectivo constante g, aplicar importe base × (1+g) elevado a años sólo cuando la convención, fecha base y periodicidad lo permitan. Fechas mensuales/irregulares, escalas contractuales y cambios de supuestos requieren contrato propio. El crecimiento de gastos no implica crecimiento igual del impuesto, reserva o fee porcentual; M2 recalcula sus componentes y bases. Cero de crecimiento documentado difiere de una celda vacía. No aplicar crecimiento previo a estabilización si la fuente exige rentas de hoy hasta ese hito.

El NOI forward usado en valoración no se agrega como caja efectivamente cobrada tras la venta. La operación del período de cierre se incluye sólo hasta el corte definido; su prorrateo no se inventa ni se mezcla con un año operativo completo adicional.

## Puente de salida y ausencia de doble cuenta

Bajo estrategia de venta y modelo de valoración aprobados: precio candidato = NOI forward / exit cap, con cap positivo y período/unidades compatibles. NOI negativo o cap cero no habilitan automáticamente una venta a precio negativo/cero; conservar el problema de dominio y política.

Fuentes de salida = precio cobrado + caja libre previa autorizada + liberaciones efectivas no contadas antes. Usos = costos/ajustes/impuestos documentados + payoff vigente de deudas + reservas/caja retenida requerida + otros pagos expresos. El excedente disponible sólo se distribuye si las restricciones lo permiten. Bajo ese caso limitado, con Z=fuentes−usos: distribución=max(Z,0), aporte=max(−Z,0). Conciliar fuentes+aporte=usos+distribución.

No confundir valor de venta con proceeds netos ni sumar ambos. No restar otra vez principal pagado antes del cierre: el payoff parte del saldo vigente más conceptos pendientes. Reservas liberadas, devolución de depósitos y escrow requieren evidencia de disponibilidad y una sola imputación. Si se retiene caja, registrarla aparte en usos/saldo, sin afirmar que se distribuyó.

Un maturity anterior a venta sin solución documentada es una incompatibilidad temporal a resolver; no mantener artificialmente viva la deuda. Responsabilidad por déficit y fuente de aporte no se presuponen de un escenario de liquidación.

## Ledger del inversor y Equity Multiple

Preservar por evento aportes A y distribuciones D brutos con fecha, ID único, origen y destino; agregar por período sólo después de conciliar. Flujo neto para retorno = D−A. Deuda recibida, principal repagado, transferencias a reservas y valoración patrimonial no son aportes/distribuciones del inversor por sí mismos.

EM candidato = suma de distribuciones/proceeds incluidos / suma de aportes incluidos, con denominador positivo. El contrato debe establecer si hay terminal realizado, liquidación hipotética o activo retenido; no llamar realizado a una valoración ni agregar un valor terminal y su venta como dos distribuciones. Si los aportes son cero, EM queda indefinido; no asignar infinito ni cero. La magnitud neta acumulada de equity no es automáticamente capital aún invertido aprobado para CoC o recuperación (Q7/Q8 abiertos).

Un aporte y una distribución simultáneos pueden dejar el mismo flujo neto que una transacción menor, con distinto EM por los brutos. Por eso no reconstruir EM sumando sólo partes positivas y negativas del neto mensual. No cancelar brutos por conveniencia ni crear transacciones circulares: todos necesitan evidencia económica.

## IRR regular: contrato de dominio y raíces

Para intervalos regulares y tasa efectiva por intervalo r, resolver valor presente neto de la serie neta igual a cero. En la referencia aislada se usa factor de acumulación positivo (r>−1), con q=1/(1+r)>0: el valor presente es un polinomio en q. Es un dominio explícito del ejercicio, no una política experta adoptada por defecto. Con m intervalos regulares por año, tasa anual equivalente=(1+r) elevado a m −1. No multiplicar simplemente por m.

Registrar: dominio examinado, raíz/intervalo y evidencia de aislamiento, multiplicidad si corresponde, inexistencia o indeterminación y residual. Una raíz exacta de un ejemplo no demuestra que un solver general encuentre todas. Múltiples cambios de signo no prueban varias raíces distintas; una raíz tangente puede no cambiar signo y escapar a un método que sólo busque cruces. Si existen varias raíces admisibles, no elegir la mayor, la positiva o la más próxima sin política aprobada. La serie toda cero es indeterminada, no IRR cero.

Las referencias incluyen polinomios sintéticos factorizables: dos raíces distintas; raíz triple única pese a varios cambios de signo; raíz doble tangente; y ausencia de raíz. Sus conclusiones son de esos casos algebraicos concretos, no certificación de todo el dominio de flujos del producto.

## Fechas irregulares, CoC y niveles de retorno

XIRR requiere fechas y fracción de año explícita; no asumir base 365 ni equipararla a IRR mensual. Agrupar eventos de una misma fecha para valor presente no elimina sus brutos del ledger. Orden y prorrateo de eventos simultáneos para caja/deuda deben quedar definidos.

CoC usa caja distribuible del período aprobado y capital remanente bajo definición aprobada. Si ese denominador es cero, mantener resultado indefinido/no aplicable según regla; un valor de mercado positivo no lo repara. El período de CoC no se deduce del dato anual de NOI ni del año de venta.

El retorno a nivel proyecto corresponde al equity agregado bajo deuda explícita, no a una proyección sin deuda por interpretar literalmente “all equity”. Si la terminología histórica es ambigua, aclarar nivel y apalancamiento. No generar retornos LP/JV ni waterfall sin contratos, fees/promote y reparto documentados.

## Aceptación, dependencia y estado

Cambios de NOI/cap/crecimiento o calendario invalidan operación/salida/retornos afectados. Cambios de deuda o payoff invalidan caja y retornos; cambios de criterio de inversión no cambian por sí solos flujos independientes, pero sí comparaciones y precio soportado dependiente. No mezclar eventos de distintas corridas/revisiones.

Prueba propia: `references/validate_m7_returns.py`, resultado `m7-validation.json`. Fracciones exactas para conservación de salida, preservación de brutos, casos indefinidos y polinomios factorizables de IRR; tasa anual equivalente regular. No ejecuta solver general, XIRR, reglas fiscales, operaciones reales ni auditoría independiente. No reproduce la aplicación original ni referencias históricas perdidas.

M7 sigue abierto: faltan cierre de estrategia/fechas, denominadores de capital, taxonomía de terminal, documentos reales y validación independiente/integrada M2/M5/M6/M8. El PDF profesional R01 conserva su corte previo; este contrato amplía su M7 preliminar sin atribuir aprobación al revisor. Siguiente bloque: M8 escenarios, sensibilidad y precio soportado, con objetivos expresos y dominio verificable.

## Ampliación matemática posterior al corte de R02

Ver [aislamiento de raíces de TIR periódica](periodic-irr-root-isolation.md) y `references/periodic-irr-isolation-validation.json`: 64 controles sintéticos de conteo/aislamiento racional y multiplicidad con precisión y trabajo expresos. Esta evidencia separada amplía los ejemplos factorizados anteriores; no resuelve XIRR, elección de raíz, políticas de anualización, integración del calendario ni revisión independiente. M7 permanece abierto.
