# Evidencia para activar conexiones y validar salidas del Mini-UW

El Mini-UW necesita distinguir la descripción de una conexión, su implementación compatible y la aceptación financiera de sus resultados. Las 20 fichas de [D09](MiniUW_Contratos_Financieros_Prioritarios_D09.md) y [D10](MiniUW_Contratos_Financieros_Complementarios_D10.md) describen los 55 campos originales; para activarlas hacen falta fuentes, definiciones y comprobaciones del alcance correspondiente.

Este plan reúne un expediente por conexión y una revisión independiente de las 23 salidas del inversor. Permite avanzar en preparación y diseño sin asignar valores, tasas, umbrales, responsables o aprobaciones que todavía no estén sustentados. Las conexiones financieras desde la hoja permanecen PENDING. La implementación sintética conservada es T111.

## Evidencia de cada conexión

Cada uno de los 20 expedientes enlaza a su ficha original mediante hash y ubicación exacta. Conserva sus campos, cantidades, bases, fuentes complementarias, brecha frente al perfil técnico y dos comprobaciones condicionales. Son las mismas 40 comprobaciones propuestas en D09/D10; reunirlas no equivale a ejecutarlas.

La [matriz de conexiones](MiniUW_Activacion_20_Conexiones_D11.csv) resume los expedientes. El [registro completo](MiniUW_Activacion_y_Aceptacion_D11.json) permite revisar seis clases de evidencia:

| Evidencia | Qué debe quedar sustentado |
| --- | --- |
| Identidad, fuente y vigencia | Original y localizador, revisión, deal, escenario y UTC compatibles. Las discrepancias conservan sus afirmaciones originales. |
| Unidades, cantidades y período | Moneda, formato, cantidad elegible, base, período y conversión documentada. Un cero explícito conserva su identidad frente a un dato ausente. |
| Definición y aplicabilidad | Relación financiera vigente, inclusiones, clasificación y alcance. Una regla oficial necesita evidencia aplicable cuando intervenga en el cálculo. |
| Conexión técnica compatible | Prueba de cómo cada campo llega a su cantidad, base y destino dentro de un perfil que soporte la relación. El cotejo de la hoja acredita representación; la proyección requiere su propio vínculo. |
| Resultado esperado independiente | Caso con unidades, fechas y alcance definidos; resultado esperado y conciliación que no dependan únicamente de repetir la misma implementación. La precisión o tolerancia necesita una definición expresa si corresponde. |
| Salida y revisión del snapshot | Cifras, criterios, fuentes y PDF vinculados a la misma versión; pendientes visibles y revisión pertinente antes de cualquier uso real. La entrega externa conserva una página. |

Estas clases organizan evidencia existente y futura. No son seis archivos obligatorios ni un circuito nuevo de aprobaciones por paso. Una fuente puede respaldar varias clases; su alcance debe demostrarlo. Cuando una conexión no aplique al caso, esa conclusión también necesita evidencia. Una celda vacía o cero no resuelve su aplicabilidad.

La [plantilla conjunta vacía](../../templates/activation-review-D11-empty.json) contiene 20 revisiones de conexión y 23 revisiones de salida. Las referencias, definiciones, resultados esperados y evidencias de aceptación comienzan vacíos. Es un registro de revisión documental; el runtime actual no lo acepta como autorización de cálculo. Los diez criterios de inversión originales siguen vacíos por deal.

## Revisión de las salidas del inversor

La [matriz de 23 salidas](MiniUW_Aceptacion_23_Salidas_D11.csv) conserva las definiciones de [D08](MiniUW_Expediente_y_Conexiones_D08.md), sus fuentes complementarias y el puntero al resultado sintético T111 guardado. Separa lo observado en ese ejemplo de lo que falta para su aceptación financiera.

En ese resultado hay 17 salidas disponibles dentro del alcance condicional del proyecto, dos salidas con cero explícito del perfil sin refinanciación y cuatro pendientes específicos. Los dos ceros corresponden a cash-out y cash-in de refi: están declarados en las categorías del ejemplo, con ausencia de eventos de refi. No se convierten en supuestos para un proyecto que sí refinancie.

| Salida pendiente | Evidencia necesaria para resolverla |
| --- | --- |
| Capital aún invertido | Stock con fecha, alcance, base y fuente. Aportes menos cobros describe una diferencia de caja; no define este stock. |
| Equity retenido | Valor y participación sustentados a la fecha correspondiente, separados del efectivo distribuido. |
| CoC anual | Base anual de capital positiva y cobertura del año operativo compatibles con la definición. Una TIR disponible no suministra ese denominador. |
| Retorno personal | Términos de reparto y asignación aplicables a aportes y cobros fechados. El retorno agregado y la referencia por 10 conservan su alcance de proyecto. |

Los 15 conjuntos complementarios de D08 siguen vinculados al plan. Incluyen programa físico, calendario, costos, deuda, operación, refi, venta, términos personales, capital, criterios, reglas oficiales, escenarios, procedencia, normalización y aceptación. La hoja de 55 campos no reemplaza esas evidencias. Tampoco una salida disponible del ejemplo demuestra que todas las entradas financieras del deal estén completas.

## Comprobaciones conjuntas previstas

Además de las 40 comprobaciones por conexión, se especifican seis situaciones conjuntas para una futura aceptación. Sus resultados numéricos esperados permanecen sin completar hasta disponer de las definiciones y casos pertinentes.

1. Una hoja coincidente con una cantidad, base o período sin definir conserva el bloqueo financiero del cálculo afectado.
2. Ingresos comerciales o complementarios requieren un perfil compatible; omitirlos o introducir cero para superar la puerta no resuelve el caso.
3. Un cambio de presupuesto necesita una cadena de financiación sustentada. Capacidad bancaria, compromiso, draw y aporte efectivo conservan identidades separadas.
4. Un pago o reserva que alcance operación y venta se concilia por concepto y contrapartida para impedir un segundo descuento.
5. Una historia de caja calculable mantiene por separado los pendientes de stock, CoC y reparto personal.
6. Una revisión o vencimiento exige comprobar de nuevo el snapshot y sus dependencias. La coincidencia de la hoja no restaura cifras anteriores como actuales.

Estas seis situaciones se enlazan a los casos A01–A08 de D08. Su especificación no añade pruebas de software ni acredita aceptación financiera. En T111, los bloqueos del perfil actual retiran las cifras actuales de forma conjunta; las listas documentales de este plan no modifican esa conducta ni habilitan publicación parcial.

## Trabajo preparado y límites vigentes

Ya puede revisarse la suficiencia de un expediente, localizar qué falta por conexión y preparar casos independientes con sus fuentes. Un faltante de Lorena, GC, banco, regla aplicable o definición profesional conserva PENDING en el alcance que necesita esa información. Los nombres de esos participantes no asignan por sí solos propiedad o autoridad a una fuente.

La [verificación documental](D11-design-validation.json) comprueba la conservación de los 55 campos, los 20 expedientes, las 23 salidas, los 15 conjuntos de fuentes, las referencias y las 43 filas vacías de revisión. La aceptación financiera ejecutada y las nuevas conexiones activadas siguen en cero. Se conserva el código T111 y sus 1.619 pruebas existentes, con datos sintéticos, sin despliegue ni decisiones reales. La ampliación a condominios, preventa y sellout permanece para Full UW.
