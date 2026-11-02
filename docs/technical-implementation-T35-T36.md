# Valoración capacidad bancaria y desembolso antes del retorno

T35 calcula valor por NOI/cap y capacidades declaradas por LTV, DSCR y otros límites. Mantiene separados NOI de valoración, NOI bancario, capacidad máxima, préstamo elegido, proceeds brutos y distribución al inversor. T36 agrega un camino de retorno que reproduce esa rama y exige que sea compatible con la refinanciación de la ventana T33–T34.

Compatibilidad aritmética no es tasación, política bancaria adoptada, crédito concedido, fondos disponibles o PASS de inversión. Los términos y bases son hipótesis sintéticas suministradas; criterios de Lorena, aprobación profesional y uso real siguen separados y pendientes.

## Cálculo condicionado y selección

`Valor = NOI de valoración / cap`.

`K = pagos por año × cuota regular por unidad de principal`.

`Capacidad LTV = LTV máximo × valor`.

`Capacidad DSCR = NOI bancario / (DSCR mínimo × K)`.

La capacidad total es el mínimo de ambas y de todos los límites adicionales expresos. Un importe adicional faltante no se omite como ilimitado. El inventario necesita declaración y referencia, incluso si está vacío; eso no acredita que se hayan leído todos los covenants reales. Todos los límites empatados se conservan como vinculantes.

El préstamo elegido se recibe aparte. Puede ser inferior al máximo; nunca se lo aumenta para utilizar la capacidad. Se compara exactamente con principal original del préstamo nuevo, principal nuevo del cierre y proceeds brutos bajo el perfil de desembolso completo. Se verifican ID y fecha de originación/cierre; diferencias, estados netos, ajustes o desembolsos parciales requieren tratamiento adicional.

K es un equivalente anualizado regular para sizing. No es prueba de servicio pagado en un año real ni extensión del vencimiento: la rama de pagos fechados T31 sigue siendo distinta. Para el cálculo se reproduce T10 y no se convierte una tasa anual en mensual por defecto.

## Ejemplos ejecutados sin alterar el proyecto anterior

El caso independiente usa NOI de valoración 10 y cap 1/20: valor calculado 200. LTV 1/2 permite 100. NOI bancario 12, DSCR mínimo 6/5 y préstamo a tasa cero con 120 cuotas y 12 por año producen K=1/10 y capacidad DSCR 100. Ambos límites quedan vinculantes. Se elige principal 100, coincidente con proceeds y principal nuevo; la distribución de su cierre es 20, no 100 o 200. Son valores ficticios, sin autoridad bancaria.

El segundo caso conserva todos los valores del proyecto T34. Sus proyecciones anuales separadas de valoración y banco declaran NOI 50, cap 1/10 y LTV 4/5: valor 500, límite LTV 400. Con los términos del préstamo nuevo a tres cuotas, su equivalente anualizado K y DSCR mínimo sintético 5/4 producen capacidad DSCR exacta `30301000/3090903`, aproximadamente 9,80. El préstamo elegido/proceeds son 303,01: superan esa capacidad declarada.

La ventana de caja anterior sigue cuadrando, pero el nuevo camino de retorno queda **PENDING por financiación** y no genera otro ledger compilado. No se modifica el proyecto, NOI, tasa, límites, préstamo ni criterios para hacerlo compatible. Los ejemplos T34 anteriores permanecen como evidencia de conciliación de caja bajo sus hipótesis; no eran aprobación de financiación.

Las proyecciones anuales son fuentes sintéticas nuevas y explícitas, no la anualización automática de los importes trimestrales de operación de T34. Su alcance/comparabilidad no está autenticado. El bloqueo aritmético no concluye que un banco real haya rechazado el proyecto ni propone cifras reales alternativas.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_refinance_capacity.py
```

## Evidencia unidades fechas y dominios

T35 recibe dos fuentes/ejecuciones NOI, fuente/ventanas/ejecución del préstamo nuevo y fuente/ejecución de cierre. Reproduce todas antes de consumirlas y comprueba ocho hashes, contexto, moneda, períodos y bases anuales expresas. No sustituye un NOI por el otro; pueden coincidir sólo mediante vínculos explícitos. El período del NOI bancario debe coincidir con el equivalente anual declarado del préstamo.

Cap debe ser positivo; DSCR mínimo positivo; LTV, NOI y límites no negativos dentro de este perfil. Un LTV mayor de uno no se recorta a 100% por una política supuesta. Un NOI negativo no genera automáticamente propiedad o préstamo negativos. Cero es conocido: capacidad cero puede compararse con préstamo cero, pero DSCR con servicio cero permanece indefinido, sin infinito o cero inventado.

La selección monetaria y cada límite llevan moneda, fecha, base y fuente. Cap/LTV/DSCR llevan valor racional, unidad, período y fuente. Los límites matemáticos se conservan aunque la selección esté ausente/incompatible, sin presentar el mínimo de un subconjunto como capacidad completa. Si hay una valoración afirmada en el cierre, debe coincidir con NOI/cap y metadatos; si no hay esa afirmación opcional, no se fabrica una tasación externa. El valor calculado no entra como ingreso de caja.

La fecha de sizing y el cierre deben coincidir en este perfil; otros desfases requieren una convención explícita. Las fuentes acotadas y racionales de hasta 4.096 bits bloquean al excederse. Los bloqueos originales de los productores permanecen visibles; un hash nuevo de un resultado alterado no permite saltar su reproducción.

## Camino de proyecto y recuperación

T36 reproduce toda la ventana NOI/caja/deuda/cierres y la rama de capacidad. Identifica la refinanciación exacta por ID y hashes de fuente/ejecución, fecha y contexto/moneda. El préstamo para sizing debe ser exactamente el mismo archivo y ejecución que aparece como deuda permanente en la venta: coincidir sólo en ID o principal es insuficiente si cambian tasa, amortización o ventanas.

Sólo si todas esas condiciones son compatibles se invoca T34 con sus controles de inventario, aportes, targets vacíos y no cambios parciales. Cualquier bloqueo de banco o caja conserva originales y no genera ledger nuevo. Los APIs anteriores siguen como componentes sintéticos aislados, no como afirmación de que verificaron capacidad bancaria.

Las capturas locales incluyen las fuentes/ejecuciones de capacidad y toda la cadena de proyecto. Cada paquete se captura en una transacción; al reabrir se comprueban bytes, versiones, definiciones y reproducción. El demo recupera tres paquetes: sizing compatible independiente, sizing bloqueado del proyecto y retorno bloqueado con todas sus fuentes. Las pruebas también recuperan un contrafactual compatible expresamente construido sólo para comprobar esa rama del código; no cambia los archivos del demo ni adopta un NOI alternativo. Bases runtime excluidas de GitHub/ZIP; sin atomicidad distribuida o autorización de publicación.

## Validación y pendientes

23 pruebas T35 y 13 T36: 36 nuevas, 688 técnicas en total. Incluyen identidades independientes, empates/mínimo adicional, selección inferior/excesiva, NOI distintos, desconocidos/cero/dominios, períodos/unidades, invariancia de originales, guardas de banco versus caja, mismo ID con términos distintos, límites técnicos reales, resultados falsificados con hash actualizado, rollback, versiones, fuentes ausentes y reapertura de ramas bloqueada/compatible.

Permanecen pendientes bases reales de NOI/cap/valor, covenants/términos bancarios, disponibilidad de fondos, perfiles parciales/netos/fuera de alcance, construcción/funding histórico, capital/equity, revisión profesional, riesgos y salida final. No se adopta mínimo bancario como criterio de inversión ni se emite decisión real. Originales/I01/matriz de 398 filas/criterios vacíos/revisión pendiente se conservan. Los 36 casos financieros originales y 56 escenarios D02/D03 siguen abiertos. Sin despliegue, decisión real o cierre financiero.
