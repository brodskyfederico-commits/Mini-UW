# Errores de conciliación y límites de la comprobación aritmética del Mini-UW

Las conciliaciones de [D13](MiniUW_Conciliaciones_D13.md) señalaron diferencias en los ocho errores deliberados introducidos en copias en memoria del ejemplo sintético. Cinco de esos errores conservaron el cuadre global de fuentes y usos. Los controles por concepto, saldo, período y traspaso son necesarios para encontrar diferencias que un total agregado puede ocultar.

Este ejercicio documenta el alcance de la comprobación aritmética de referencia. No modifica el código T111, las fuentes originales, el PDF o los resultados guardados. Los errores son inconsistencias artificiales para comprobar controles, no escenarios de inversión, propuestas financieras o cambios de supuestos para obtener PASS. La decisión permanece PENDING.

## Cómo se construyeron los casos

El punto de partida son las 24 igualdades y sus expresiones de [D13](MiniUW_Conciliacion_Sintetica_D13.json). Primero se verificaron los hashes originales. Cada caso agregó o restó un importe ya presente en esas fuentes y conservó las demás afirmaciones para observar las discrepancias resultantes.

Los importes de las alteraciones proceden del pago de seguro, principal de deuda, reservas, cobros o aporte adicional del ejemplo existente. No se eligió una tasa, límite o shock nuevo. El registro conserva la ubicación exacta del campo, el importe utilizado, la operación y el valor derivado.

La copia alterada tiene un hash distinto y permanece en memoria. Las referencias originales identifican su origen; no afirman que esa copia conserve el hash original ni que sea una fuente actual admisible. No se llamó al runtime para probar su rechazo, no se renovaron vínculos y no se publicó ninguna copia como entrada de un deal. En un proceso real, una revisión necesitaría su propia identidad y verificación de dependencias.

Se evaluaron las 24 igualdades originales y las mismas 24 en cada uno de los ocho casos: 216 evaluaciones aritméticas. Los resultados se conservan por igualdad, incluyendo su lado izquierdo, derecho, residual y unidad. Las diferencias se calculan con fracciones exactas, sin introducir una tolerancia financiera.

## Qué errores se evidenciaron

La [tabla de ocho casos](MiniUW_Casos_8_D14.csv) resume las señales. El [registro de alteraciones](MiniUW_Controles_Negativos_D14.json) conserva las fuentes y las operaciones; los [resultados completos](MiniUW_Resultados_Controles_D14.json) permiten reproducir las evaluaciones.

| Error deliberado | Diferencia observada | ¿El control global A18 dio señal? |
| --- | --- | --- |
| Seguro incluido en venta descontado dos veces | El pago al corte deja de coincidir con los usos de venta y cambia el residual frente al cobro declarado. | No |
| Seguro al corte omitido | El inventario del pago y el cierre dejan de coincidir. | No |
| Principal de venta pagado dos veces | Cambia el residual de venta frente al cobro declarado. | No |
| Payable operativo borrado con pagos sin revisar | El gasto, el pago y la caja del período dejan de conciliar. | Sí |
| Principal de cambio de fase tratado como caja nueva | La apertura operativa y el primer cierre dejan de coincidir con la financiación y caja de origen. | No |
| Reserva sumada otra vez a caja libre de venta | Se duplica caja al trasladar saldos y cambia la distribución terminal. | Sí |
| Aportes brutos sustituidos por neteo con cobros | El aporte declarado deja de coincidir con sus movimientos de origen. | No |
| Aporte adicional omitido conservando cierres anteriores | Caja, fuentes, aportes y retornos dejan de coincidir. | Sí |

Los ocho casos produjeron al menos una diferencia en las conciliaciones de referencia. Eso no demuestra detección exhaustiva de errores ni añade esos controles al producto. Tampoco una diferencia implica FAIL del deal: la fuente, el alcance, la definición y las dependencias deben resolverse, conservando las afirmaciones originales.

## Por qué puede cuadrar el total y persistir un error

El control A18 compara fuentes y usos externos del ciclo. Cuando el residual de venta se recalcula con una partida equivocada, el mayor uso puede compensarse con un menor cobro calculado del equity. El total puede seguir cuadrando aunque exista una duplicación o falte la evidencia del concepto.

En el caso del doble seguro, por ejemplo, la fuente del pago al corte sigue indicando el importe original y los usos de venta se alteran. La conciliación específica del seguro descubre la diferencia; la comparación entre residual calculado y cobro declarado también la señala. El total global, por sí solo, no establece si la partida debe existir o está repetida.

El cambio de fase muestra otro límite: agregar el principal como apertura de caja no crea un draw documentado. La continuidad entre etapas y la ecuación de caja del período señalan ese salto, aunque los totales externos originales permanezcan cuadrando. Por eso las seis fronteras de [D12](MiniUW_Dependencias_y_Traspasos_D12.md) conservan su función de revisión.

## Qué sigue pendiente aunque las 24 igualdades cuadren

La [matriz de límites](MiniUW_Limites_4_D14.csv) conserva cuatro condiciones observadas en el ejemplo base sin alteraciones:

| Condición | Estado que conserva el modelo |
| --- | --- |
| Autenticidad y completitud | La autoridad de las fuentes y la revisión profesional no están verificadas. Un cuadre no acredita pagos bancarios o completitud del inventario. |
| Criterios y decisión | Los diez criterios empiezan vacíos; faltantes, conflictos o bandas conservan PENDING. Una igualdad no suministra un umbral de inversión. |
| Capital y CoC | Falta stock declarado y base anual de capital. Aportes menos cobros, una TIR o un saldo de caja no completan esas definiciones. |
| Retorno personal | Faltan términos aplicables de asignación. El retorno agregado del proyecto no define lo que cobra una persona. |

Estas condiciones ya coexisten con las 24 igualdades del ejemplo base sin diferencias. Se preservan las declaraciones, los ceros explícitos y los faltantes. No se convierte una fuente ausente en cero, una discrepancia en ajuste ficticio o un nombre/checkbox en aprobación auténtica.

## Alcance conservado

La [verificación documental](D14-design-validation.json) reproduce las vistas y los residuales, comprueba sus hashes y conserva los archivos anteriores. El ejercicio ejecuta ocho comprobaciones de errores aritméticos en memoria, sin añadir pruebas de software a la suite ni componentes de runtime. Los controles existentes de T111 conservan su comportamiento; aquí no se probó ni cambió su rechazo de estas vistas.

Las 20 conexiones, los 55 campos y las 23 salidas de [D11](MiniUW_Activacion_y_Aceptacion_D11.md) mantienen su alcance. Los 54 mapeos semánticos pendientes y la aceptación financiera siguen abiertos. No se recalculó TIR ni se adoptaron valores de las vistas alteradas. Datos sintéticos, sin despliegue, decisiones reales, contacto con Lorena o ampliación Full UW.
