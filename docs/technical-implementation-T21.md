# Productor residencial y gastos operativos sintéticos

T21 calcula renta residencial desde cantidades y bases expresas, y gastos desde partidas configuradas. Es un perfil sintético acotado de M2: no interpreta planos, selecciona renta de mercado, determina asequibilidad o adopta reglas comerciales/fiscales. Los datos y referencias de política son declaraciones de prueba sin validación financiera.

## Renta y descuentos

Cada grupo identifica unidades enteras no negativas, renta y base mensual. Para renta por unidad no hace falta un área que no interviene; para renta por SF rentable se exige el área explícita. No se convierte GSF a área rentable. La cantidad por período multiplica unidades, renta mensual por unidad y meses expresos.

El factor de pérdida se aplica a renta potencial. La concesión declara si su base es renta potencial o renta después de esa pérdida; ambos cálculos se mantienen distintos. Si la renta se declara neta de concesiones, exige concesión cero explícita y la base `already_in_rent`: cualquier otro descuento bloquea el grupo. No se adivina si una renta ya incorpora concesiones ni se carga cero ante una celda vacía.

Las fracciones de pérdida/concesión fuera de [0,1], unidades fraccionarias o negativas y renta negativa están fuera de este perfil y bloquean el cálculo. Una fórmula declarada que produzca renta efectiva negativa conserva el resultado firmado: no se recorta a cero ni se decide FAIL económico. La admisibilidad financiera de esa fórmula sigue sin acreditarse.

## Gastos y período

Cada partida declara uno de tres tipos: importe fijo del período, importe por unidad y año regular, o fracción de la renta residencial efectiva calculada. La última base excluye otros ingresos y comercial: no se amplía automáticamente al EGI total. Cada partida necesita fuente y referencia de política declaradas; no basta un porcentaje sin base.

Meses del período y conversión de doce meses por año se declaran expresamente dentro de este perfil regular. Esto no acredita fechas, año fiscal, lease-up, TCO, devengo diario o caja. El importe por unidad/año se convierte proporcionalmente bajo esa convención seleccionada. Otros calendarios necesitan otro contrato validado.

Un inventario vacío no implica cero. Si falta renta o unidades, se bloquean los gastos que dependen del ingreso o número de unidades, mientras una partida fija independiente puede conservar su importe. La agregación requerida continúa bloqueada. Un cero explícito es distinto de ausencia. Identidades repetidas se rechazan; identidades distintas no prueban que sus unidades o alcances económicos sean independientes.

## Evidencia y límites

`produce_rental_operations(raw)` conserva resultados por grupo, pérdidas, concesiones, renta efectiva, partidas de gasto, ubicaciones JSON, fuentes declaradas y bloqueos. Límites de inventario y tamaño racional previenen cálculos incompletos presentados como válidos. Los resultados son de devengo; no acreditan cobros o pagos.

El paquete `miniuw.synthetic-rental-bundle.v1` guarda fuente y resultado y reproduce con versiones compatibles y documentos de definición. No altera el esquema de almacenamiento anterior; las bases runtime quedan excluidas del backup documental.

16 pruebas nuevas cubren bases por unidad/SF, concesiones sobre dos bases, renta neta, meses expresos, cero, signo, dependencias bloqueadas, dominios, moneda/política/fuente, inventarios, duplicados, contexto sintético, presupuesto racional, copias y archivo con reapertura, falsificación, fallo transaccional, versión y evidencia ausentes. Esto no cierra M2 ni certifica una política de management, renta o concesiones para un deal real.
