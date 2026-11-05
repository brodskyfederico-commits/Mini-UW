# Contratos de cálculo para las conexiones financieras prioritarias

Para conectar los valores de la hoja al retorno del proyecto hay que identificar cantidades, bases, períodos y fuentes antes de transformar una celda en dinero. Este bloque detalla ocho conexiones que abarcan 19 campos de renta, costo, operación, deuda y venta. Los otros 36 campos conservan el mapa del [expediente por proyecto](MiniUW_Expediente_y_Conexiones_D08.md).

Las relaciones siguientes se aplican bajo sus condiciones documentadas. Cada vínculo con la hoja permanece PENDING hasta contar con su definición, fuentes, perfil compatible y validación. La implementación T111 conserva sus entradas y casos; este detalle no activa nuevos vínculos financieros ni completa valores.

## Conexiones y condiciones de uso

| Conexión | Celdas | Relación condicionada | Información que debe quedar explícita |
|---|---|---|---|
| F01 Renta por grupo | C7 a C11 | Unidades × renta mensual por unidad; o unidades × área rentable unitaria × renta mensual por SF. | Identidad de cada grupo, disponibilidad, áreas, moneda, período, definición de renta y pérdidas/concesiones. |
| F02 Costo vertical | C34 a C36 | GSF × tarifa/GSF; o unidades × tarifa/unidad; o total vertical suministrado. Se elige la rama de la base declarada. | GSF o conteo con fuente, alcance vertical e inclusiones de la cotización. |
| F03 Gastos y administración | C57 y C58 | Gasto anual por unidad con cantidad/período compatibles; comisión × EGI residencial elegible del período. | Conteo elegible y composición de EGI, incluidos otros ingresos cuando corresponda. |
| F04 Seguro | C59 | Estimación anual por unidad sólo con cantidad asegurada y período definidos; conciliación separada con pólizas, gasto, cuotas y pagos. | Unidades aseguradas, cobertura, primas, asignaciones, cuotas, pagos y saldos. |
| F05 Reservas | C60 | Tratamiento según clasificación documentada de gasto, obligación, depósito o saldo. | Inclusión en NOI, caja libre/restringida, ajustes, depósitos, liberaciones y saldo final. |
| F06 Valoración | C66 y C67 | NOI anual compatible / cap positivo, separando refi y salida. | NOI de valoración/bancario/forward, ventana, fecha y fuente del cap; hipótesis de venta a valor cuando proceda. |
| F07 Deuda y capacidad | C69 a C72 | Cuota del perfil contractual y capacidades por límites aplicables, con principal seleccionado aparte. | Tasa por intervalo, amortización en pagos, frecuencia, maturity/fechas, NOI bancario y restricciones. |
| F08 Costos de venta | C68 | En el perfil fijo/fracción del bruto: fijos incluidos + precio bruto × fracciones incluidas. | Base, inventario de cargos, clasificación, aplicabilidad, impuestos y no solapamiento. |

La [matriz de los 19 campos](MiniUW_Conexiones_Prioritarias_D09.csv) conserva ubicación y unidad originales. El [registro completo](MiniUW_Contratos_Financieros_Prioritarios_D09.json) añade requisitos, fuentes documentales exactas, interfaces existentes y condiciones de comprobación por conexión. Las interfaces observadas corresponden a perfiles concretos; no acreditan una adaptación general de la hoja.

## Renta y cantidad de unidades

La nota original de C7 distingue renta mensual por unidad y por SF. La rama por SF requiere el área rentable de la unidad. GSF total, NRSF total o número de dormitorios no sustituyen esa identidad. Studio, 1BR, 2BR y 3BR deben vincularse a grupos documentados, incluidos los otros unit types que correspondan; no se emparejan grupos por posición en una lista.

El [productor residencial T21](../../src/miniuw_foundation/rental_operations.py) admite las dos bases bajo sus parámetros expresos. El calendario T82 necesita además disponibilidad y fracciones de reconocimiento suministradas. Sus referencias de renta exigen gastos explícitamente cero: seguro, administración y otras partidas operativas necesitan sus fuentes y conciliaciones separadas.

Una renta ya neta de concesiones debe conservar esa definición. Aplicar nuevamente una concesión o pérdida requiere una base que lo justifique; la igualdad entre dos importes no demuestra que tengan el mismo alcance.

## Costo vertical y alcance de la cotización

C34 selecciona la base; C35 aporta tarifa o total según esa base. La nota de C35 identifica construcción vertical excluyendo parking y site. Una cotización GC que incluya esos conceptos requiere conciliación de alcance antes de conectarse. No se descompone por estimación ni se agregan otra vez partidas que ya estén incluidas.

Se conserva la condición original de C36: aplica al usar base por GSF cuando los planos muestran GBA como TBD. No se convierte en una sustitución universal del área de planos ni en autorización para reconstruirla. Los contratos de [presupuesto y calendario](../model-budget-schedule.md) mantienen separadas base de costo, inclusiones, presupuesto y desembolso.

La referencia algebraica M3/M4 comprueba equivalencias bajo cantidades suministradas. Sigue pendiente un vínculo integrado desde estas celdas al presupuesto y a su calendario; la equivalencia matemática no valida una cotización real.

## Base de administración y conteo para gastos

C58 está etiquetada como fracción de EGI residencial. La rama `fraction_of_residential_effective_rent` de T21 usa renta residencial efectiva y declara excluir otros ingresos y comercial. Es necesario conciliar la composición de esas bases antes de vincularlas. Otros ingresos cero documentados pueden permitir demostrar igualdad en un caso; esa igualdad no se extiende automáticamente a otro proyecto.

C57 requiere un conteo elegible y un período. El perfil anual por unidad de T21 utiliza la cantidad aportada en sus grupos y un año regular de 12 meses declarado expresamente. Si el gasto requiere otro conteo, calendario o asignación, debe utilizarse un perfil compatible. No se toma por defecto la cantidad disponible para renta como base de todos los gastos.

## Seguro y reservas

La tarifa C59 puede sustentar una estimación cuando se documentan cantidad asegurada y cobertura. El costo de póliza, la asignación del gasto, las cuotas nominales, los pagos y el saldo contable conservan sus propias fuentes. En T111 el costo nominal y las pólizas se reciben estructurados; no se calculan desde C59. La [ruta de liquidación](../technical-implementation-T110.md) mantiene la comprobación de pagos operativos y de la liquidación ya incluida en venta.

C60 necesita una clasificación aplicable antes de incorporarse al NOI o a la caja. El [puente operativo](../../src/miniuw_foundation/operating_cash.py) tiene depósitos, liberaciones y saldos restringidos explícitos. Eso permite representar movimientos; no decide la política financiera de la reserva. Si un mismo concepto aparece como gasto y depósito, la conciliación debe explicar su tratamiento. No se inventa un ajuste, addback o liberación para hacer cuadrar el resultado.

## Valoración y financiación

El cap de refi C66 y el cap de salida C67 son entradas distintas. El [perfil de sizing](../refinance-capacity-bridge.md) separa NOI de valoración y NOI bancario; el [perfil de salida](../technical-implementation-T41-T42.md) exige su NOI forward y ventana. Un dato fuera del dominio del perfil, como cap cero o ventana incompatible, deja pendiente el cálculo; no se convierte en FAIL financiero ni se reemplaza por cero.

Un valor calculado sólo puede servir como precio de una venta mediante una hipótesis explícita y un cierre conciliado. La venta de T111 recibe proceeds brutos suministrados; no los obtiene de C67 ni agrega el valor del activo como un segundo cobro al inversor.

C69 dice decimal y C70 dice años. El [productor de deuda](../../src/miniuw_foundation/debt_service.py) requiere tasa efectiva por intervalo, pagos de amortización, frecuencia, maturity y fechas explícitas, dentro de su perfil fijo y regular. Esas dos celdas no suministran por sí solas el contrato temporal. No se divide una tasa anual por 12 ni se transforma años en pagos o fechas con una convención por defecto.

LTV y DSCR limitan capacidad bajo las condiciones suministradas; el préstamo seleccionado y el desembolso se reciben aparte. Las condiciones bancarias no rellenan los diez criterios de inversión, ni prueban aprobación crediticia, disponibilidad de fondos o una distribución personal.

## Costo de venta y retorno

C68 necesita base y alcance: puede representar una tasa agregada o un componente, según la fuente. El [productor de costos T43](../technical-implementation-T43-T44.md) admite un inventario explícito de cargos fijos y fracciones del precio bruto. No se suma una tasa agregada a sus mismos componentes ni se omite un impuesto o cargo no resuelto para publicar un subtotal como total.

El costo calculado, el monto pagado al cierre y los cargos del payoff deben conciliarse por identidad, moneda y fecha. T111 recibe el costo pagado como una fuente independiente; el vínculo de C68 a ese importe continúa pendiente.

El efecto final debe seguirse hasta aportes y cobros brutos, fechas, caja anual, venta, Equity Multiple, TIR y riesgos. Capital remanente, equity retenido, CoC y atribución personal conservan sus bases y términos propios, como establece el [contrato de salida del inversor](MiniUW_Salida_Inversor_D07.md).

## Registro de definición y revisión

La [lista de definiciones pendientes](MiniUW_Definiciones_Pendientes_D09.csv) indica qué falta resolver por conexión. La [plantilla de revisión vacía](../../templates/financial-link-review-D09-empty.json) conserva fuentes, identidades, unidades/períodos, aplicabilidad, clasificación, perfil y comprobación independiente sin completarlos por defecto. Es documentación de diseño; el ejecutor actual no acepta esa plantilla como entrada operativa.

Los planes de comprobación se mantienen especificados y sin ejecutar como aceptación financiera de estos nuevos vínculos. Este refinamiento conserva código, casos y las 1.619 pruebas existentes de T111. Se activan cero vínculos financieros, cero criterios y cero valores de negocio nuevos. Continúan pendientes las fuentes y definiciones aplicables, sin contacto con Lorena, despliegue, decisiones reales o ampliación de Full UW.
