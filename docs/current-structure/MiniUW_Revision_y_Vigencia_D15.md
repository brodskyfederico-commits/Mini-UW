# Cambios de fuentes y vigencia de resultados del Mini-UW

Dos versiones del ejemplo sintético pueden cuadrar por separado y resultar incompatibles al mezclar sus inputs y resultados. Esta comparación reproduce ese caso con las variantes existentes `matched` y `twelve` de T111: cada pareja coherente satisface las 24 conciliaciones de D13; las dos mezclas dejan cinco diferencias y no conservan el vínculo entre el hash del input y su resultado.

La comparación también conserva una vista con fuente vencida: la hoja está conciliada, pero los 11 grupos de cifras actuales están retirados. El bloque distingue evidencia histórica, resultado compatible con sus propias fuentes y resultado admisible como actual dentro del perfil sintético. No adopta una versión activa, cambia reglas financieras ni habilita decisiones reales.

## Versiones y evidencia utilizada

La referencia procede de la entrada y el resultado T111 guardados. La versión comparada utiliza una fixture ya existente con modificación del seguro del segundo período. Se volvió a ejecutar una vez el productor T111 existente y su resultado coincidió exactamente con el hash registrado en la validación original de ese componente.

Ese resultado se conserva como [reproducción interna](MiniUW_Version_Comparada_T111_D15.json). No se escribió sobre los inputs, los resultados anteriores o el PDF; no se generó un PDF nuevo ni se añadió código de producto. El [registro de comparación](MiniUW_Revision_y_Vigencia_D15.json) conserva el recibo de reproducción y los vínculos explícitos de las fuentes seleccionadas.

La dirección de las diferencias se eligió expresamente: versión comparada menos referencia. Ambas comparten contexto declarado, UTC de evaluación, moneda, alcance del equity, ventana y los IDs, clases, categorías y fechas de los movimientos. Las dos declaraciones de hoja indican revisión 1. Esas etiquetas iguales no prueban igualdad de contenido, cronología o aprobación; los hashes y vínculos de cada snapshot se comprueban aparte.

## Qué cambió en las cifras suministradas

En la variante comparada, el seguro del segundo período pasa de 10 a 12 como fuente explícita. Las fuentes relacionadas y sus bindings también cambian. La tabla muestra diferencias observadas entre las versiones completas; no atribuye causalidad aislada a una única celda ni activa una conversión desde C59 de la hoja.

Todos los importes son **USD ficticios de los ejemplos existentes**, salvo el múltiplo.

| Salida | Referencia | Comparada | Diferencia |
| --- | ---: | ---: | ---: |
| Aportes brutos del proyecto | 1.400 | 1.400 | 0 |
| Cobros brutos | 778 | 776 | −2 |
| Neto de caja | −622 | −624 | −2 |
| Cobro neto de venta | 578 | 576 | −2 |
| Caja libre al final de operación | 213 | 211 | −2 |
| Pagos operativos | 25 | 27 | +2 |
| Equity multiple | 389/700 | 97/175 | −1/700 |

Las distribuciones operativas de 200, la reserva final operativa de 100 y la liquidación del seguro al corte de 5 permanecen iguales en estos ejemplos. La [tabla de diez salidas](MiniUW_Diferencias_Salidas_D15.csv) conserva sus fuentes, unidades y diferencias exactas.

Los netos negativos conservan su alcance de caja dentro de la ventana, sin convertirse automáticamente en pérdida económica final o retorno personal. La reproducción del productor conserva sus resultados numéricos de TIR; esta comparación no elige un punto ni resta tasas o raíces.

## Qué se conserva y qué debe vincularse de nuevo

La [tabla de fuentes](MiniUW_Cambios_Fuentes_D15.csv) compara los 155 punteros utilizados por la comprobación aritmética de D13. En ese conjunto acotado, 146 valores JSON permanecen idénticos y nueve cambian. No es un inventario completo de dependencias económicas ni una certificación de los 55 mapeos financieros de la hoja.

Los archivos envolventes y sus hashes cambian, incluso para un valor interno que se conserva. La igualdad de ese valor permite documentar continuidad; para usarlo bajo otro snapshot debe conservarse su procedencia compatible. Un componente interno idéntico podría conservar evidencia si su contexto y dependencias lo justifican. Este bloque no instala reutilización incremental ni acredita independencia de todos los resultados.

La referencia y sus conciliaciones se conservan como evidencia histórica de sus propios inputs. La versión comparada tiene sus propios vínculos y comprobaciones. Ninguna reemplaza automáticamente a la otra por aparecer después, tener otro nombre o producir un resultado más favorable. Una modificación profesional futura exige su revisión y recálculo pertinentes, sin ajustar variables automáticamente para obtener PASS.

## Comprobación de las mezclas

Se aplicaron las mismas 24 expresiones de [D13](MiniUW_Conciliaciones_D13.md) con mapas de versiones explícitos. Las cuatro parejas producen 96 evaluaciones aritméticas; también se comprobaron sus 23 condiciones de perfil en cada pareja.

| Pareja | Vínculo entre input y resultado | Conciliación observada |
| --- | --- | --- |
| Input y resultado de referencia | Coincide | 24 igualdades sin diferencias. |
| Input y resultado comparados | Coincide | 24 igualdades sin diferencias. |
| Input comparado con resultado de referencia | No coincide | Cinco diferencias. |
| Input de referencia con resultado comparado | No coincide | Cinco diferencias. |

Las mezclas afectan A16, A20, A21, A22 y A24: cobro de venta, cobros brutos, neto, múltiplo y caja anual. Las otras 19 igualdades siguen cuadrando en estas mezclas; eso no convierte la pareja en un snapshot actual compatible. Los resultados de cada igualdad y los hashes seleccionados permanecen en el registro, sin modificar las fuentes originales.

Estas mezclas son comprobaciones de revisión en memoria, no escenarios financieros ni un nuevo controlador del runtime. T111 conserva sus mecanismos de fuente y vigencia. La documentación no habilita publicar cifras parciales porque algunas igualdades coincidan.

## Fuente vencida y retiro de cifras

La quinta vista conserva el ejemplo T111 guardado con una fuente vencida. Su resultado está vinculado al hash de su input y la puerta de conciliación de la hoja está abierta. Aun así, la vigencia global está bloqueada y los 11 grupos `current_` están vacíos, con 59 requerimientos de fuentes registrados.

Para esa vista no se calculan diferencias monetarias actuales, no se convierten vacíos en cero ni se utiliza la referencia como reemplazo. La evidencia histórica conserva su identidad separada. Cuadrar la hoja, tener un hash propio o disponer de cifras anteriores no renueva una fuente vencida.

## Pendientes conservados

Las dos parejas coherentes conservan decisión PENDING, diez criterios vacíos, autoridad de fuentes y revisión profesional no verificadas, capital/CoC sin sus bases y retorno personal sin términos aplicables. Las 20 conexiones, los 55 campos y las 23 revisiones de salida de [D11](MiniUW_Activacion_y_Aceptacion_D11.md) mantienen sus pendientes; los 54 mapeos semánticos siguen abiertos.

La [verificación documental](D15-design-validation.json) reproduce las diferencias y conciliaciones, verifica las fuentes y conserva los archivos anteriores. Se mantiene el código T111 y sus 1.619 pruebas existentes. Datos sintéticos, sin despliegue, decisiones reales, contacto con Lorena o ampliación Full UW.
