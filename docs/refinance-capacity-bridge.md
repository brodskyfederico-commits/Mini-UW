# Valoración, capacidad, principal elegido y desembolso — contrato candidato

`schemas/refinance-capacity-bridge.schema.json` y `references/validate_refinance_capacity_bridge.py` conectan una rama explícita de valoración/sizing con el cierre bruto existente. Se mantiene separada de criterios de inversión, aprobación bancaria y disponibilidad auténtica de fondos. El perfil no configura un préstamo real.

## Entradas separadas

El NOI de valoración y el NOI admisible para sizing bancario son cantidades distintas, con períodos/bases explícitos. El cap divide el primero para obtener valor calculado; no se sustituye el segundo por ese NOI ni se identifica el valor con caja. La referencia requiere coincidencia de fecha de sizing y cierre; otras vigencias o actualizaciones necesitan un contrato separado, sin afirmar que una valoración anterior sea inválida por sí misma.

El paquete declara tasa efectiva por intervalo, pagos regulares vencidos iguales a tasa fija no negativa, número de pagos de amortización, frecuencia y número de pagos hasta el vencimiento. No se deriva una tasa mensual de una tasa anual ni se transforma un préstamo interest-only, flotante o irregular en este perfil. Términos desconocidos/conflictivos conservan sus afirmaciones y no producen una cuota supuesta.

## Cuota y servicio para sizing

Para n pagos y tasa i, el pago por unidad es `1/n` cuando i=0 explícito; con i>0 es `i/[1−(1+i)^(-n)]`. El perfil exige además una convención expresa de sizing anual: `m × cuota regular`. El resultado se etiqueta **equivalente anualizado de la cuota regular**. No se presenta como el efectivo pagado en un año fechado; años parciales, stubs y fechas requieren otro contrato.

El control usa fracciones exactas y contrasta la cuota con el valor presente de sus pagos y el saldo por recurrencia con la expresión cerrada. Esto no acredita estabilidad de un futuro algoritmo de punto flotante o redondeo contractual. El presupuesto técnico recibido limita el número de pagos permitido para esta referencia, no todas las operaciones ni el tamaño de los números; si es insuficiente, queda pendiente.

## Capacidades y selección

Las dos capacidades de la rama son `LTV × valor` y `NOI bancario / (DSCR mínimo × constante anual declarada)`. Los parámetros deben estar expresamente suministrados y en el dominio matemático del perfil; un dato inválido no se convierte en FAIL financiero. No se recorta un LTV a 100% por una regla supuesta.

El inventario de otros límites necesita declaración y evidencia. Cada límite adicional participa en el mínimo; un monto ausente no equivale a ilimitado. Un inventario declarado completo no prueba que todos los covenants o compromisos reales hayan sido leídos. Los empates conservan todas las restricciones vinculantes, sin prioridad automática entre fuentes.

El principal elegido se recibe aparte. Puede quedar por debajo de la capacidad calculada; no se aumenta para utilizar el tope ni se reemplaza por el cash recibido. Bajo el perfil de desembolso completo declarado, se compara contra proceeds y principal nuevo del cierre bruto. Diferencias, capacidad excedida o una valoración afirmada distinta de NOI/cap se preservan con sus residuales. Desembolsos parciales o netos y ajustes no monetarios requieren contratos adicionales.

## Saldo, vencimiento y cero

El saldo tras k pagos es un residual programado bajo las hipótesis de la rama. k<n puede producir balloon, mientras k=n amortiza completamente. No se calcula la fecha de maturity desde k ni se extiende el contrato hasta n; el contrato temporal previo sigue siendo necesario para enlazar fechas reales.

Un préstamo/capacidad cero es un valor conocido. Un cierre con financiación de deuda cero debe conservar las otras fuentes efectivamente declaradas; la referencia no añade equity para hacerlo cuadrar. Con servicio cero, el DSCR calculado queda indefinido, incluso si NOI es cero: no se muestra infinito ni cero.

## Evidencia y límites

Se retienen 46 controles sintéticos: límites LTV/DSCR y adicionales, empates, principal inferior/superior a la capacidad, diferencias de valoración/caja, tasa cero/diminuta, amortización/balloon, financiación cero con equity explícito, datos ausentes y convención anualizada separada de caja fechada.

El ejemplo usa NOI de valoración 10/cap 1/20 para valor 200; NOI bancario 12 y los demás términos declarados producen dos límites empatados en 100. Se seleccionan y registran proceeds 100; la distribución del cierre sigue siendo 20, no 100 o 200. Son cantidades sintéticas sin aplicación a un deal ni valores de Lorena.

Toda salida conserva PENDING y publicación desautorizada, con aprobación crediticia, disponibilidad de fondos y autoridad de términos sin verificar. No se acredita tasación, crédito concedido, servicio de deuda fechado, derecho a distribución, integración financiera completa o auditoría independiente. Originales, R02 y plantilla real vacía permanecen intactos.
