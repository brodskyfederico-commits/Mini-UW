# Matriz de cobertura y continuación del modelo

Esta matriz es una revisión inicial exhaustiva de las categorías identificadas en los archivos suministrados, no una declaración de completitud del modelo ni una certificación de todas las transcripciones. La cantidad de filas mide inventario, no porcentaje de preparación. Puede ampliarse al recuperar materiales ausentes o cotejar visualmente los documentos.

Cada fila enlaza requisito/variable, original y SHA-256, ubicación precisa, definición documentada, definición operativa vigente o pendiente, consumidor, evidencia, estado y trabajo faltante. Incluye requisitos adicionales de los originales, incluso campos Full UW fuera de la fase inicial. «no_explicito» indica que el detalle no aparece explícitamente en el traspaso, aunque el tema general pueda estar mencionado.

Abrir [CSV completo](coverage-matrix.csv) o [JSON completo](coverage-matrix.json). El CSV conserva cifras históricas en columnas de evidencia, nunca como configuración activa. Filtrar por grupo, estado, módulo o mención en el traspaso. Los valores activos de criterios de inversión siguen vacíos.

## Conteos de inventario

| Grupo | Filas |
|---|---:|
| instruccion_actual | 18 |
| input_sheet | 55 |
| regla_master_original | 30 |
| contrato_metrica | 10 |
| politica_original | 33 |
| driver_historico | 15 |
| decision_experta | 20 |
| parametro_tecnico | 9 |
| campo_dominio_gc | 35 |
| regla_control_gc | 17 |
| contrato_dominio | 5 |
| responsabilidad_propuesta | 17 |
| requisito_adicional | 10 |
| aceptacion_original | 21 |
| evidencia_y_faltantes | 7 |
| decision_fase_cero | 5 |
| contrato_nuevo_propuesto | 6 |

| Estado | Filas |
|---|---:|
| REGLA_ACTUAL_DOCUMENTADA_SIN_VALIDACION_PRODUCTO | 18 |
| DEFINICION_PENDIENTE | 262 |
| CONFLICTO_ABIERTO | 27 |
| PROPUESTA_NO_VALIDADA | 6 |

Total: 313 filas. Cobertura financiera verificada de extremo a extremo: **ninguna fila**. Esto no afirma que todas estén mal: falta evidencia de un producto recuperado y validado.

## Cómo interpretar la evidencia

- Hash/copia: confirma identidad de bytes, no autenticidad ni corrección financiera.
- Página/párrafo/celda: permite encontrar una afirmación, no demuestra que la regla esté aprobada.
- Workbook: los 55 campos y sus vacíos se comprobaron directamente en XML; eso no prueba suficiencia del esquema para el modelo completo.
- Regla actual: viene de la instrucción del usuario, pero todavía necesita especificación, implementación y pruebas para acreditar cumplimiento del producto.
- Fuente histórica: su texto puede estar claramente definido y aun así contradecir instrucciones actuales u otra fuente. Conservar ambas afirmaciones.
- Aceptación: las 21 descripciones fueron localizadas; no se ejecutaron contra una aplicación recuperada.

Las ubicaciones del manual usan páginas físicas del PDF (1–74), no la numeración reiniciada dentro de cada sección. Los párrafos DOCX son índices de la extracción preservada, incluyendo párrafos de celdas de tabla. La matriz no activa prompts archivados ni sustituye una revisión visual independiente.

## Siguiente desarrollo independiente

1. Cerrar el contrato de cantidades, dimensiones y calendario antes de calcular: distinguir GSF/NRSF, mes/fecha y momento del flujo.
2. Diseñar el libro bruto de aportes/distribuciones, reservas y deuda; mantener separados datos, caja y comparación de inversión.
3. Precisar costos/financiación con referencias de celdas y dependencias circulares, dejando parámetros pendientes sin valor.
4. Formular NOI/impuestos y ocupación de equilibrio como contratos completos; preservar el conflicto bruto/efectivo.
5. Definir refi/tenencia/venta y retornos, incluidos dominios indefinidos y raíces, sin elegir políticas expertas.
6. Diseñar objetivos de precio soportado y escenarios con configuración explícita; no llamar RLV certificado al soporte de dos métricas.
7. Convertir cada contrato cerrado en casos de aceptación independientes; el código de producción continúa pausado.

No se contacta a Lorena. Preguntas de política que no puedan resolverse documentalmente se consolidan para revisión posterior. La recuperación de app original, referencias matemáticas, Excel Full UW y paquete cloud sigue pendiente.

Ampliación: F0-01–F0-05 separadas, alternativas Q1–Q20 explícitas y seis contratos nuevos propuestos. Q8 opción A mezcla monto con ratio en el texto original: requiere aclaración, no corrección silenciosa. Ver [contratos de caja](model-cash-contracts.md).

## Extensión M2

Se agregan M2-01 a M2-08: ahora 321 filas. Los conteos de las secciones anteriores corresponden al hito inicial de 313; esta extensión no certifica cobertura de producto. Ver contrato de operación y prueba algebraica condicionada. Full UW se entregará al final según instrucción actual.

## Extensión M3/M4 y decisión

M3-01:M3-06 y M4-01:M4-06 más confirmación DEC-PENDING: total vigente 334 filas. Recuentos anteriores son históricos. Una instrucción directa en chat no tiene SHA de archivo original; se registra esa procedencia sin inventar un hash. Ver contratos de presupuesto/calendario, entrada de Lorena y cierre de módulos.

## Extensión M5

Se añaden M5-01:M5-10, total vigente 344 filas. Los conteos previos describen hitos históricos. La referencia de financiación sólo valida una ecuación reducida y una recurrencia bajo hipótesis explícitas; ninguna fila certifica cierre financiero de producto.

## Extensión M6

M6-01:M6-10 amplían refinanciación; total vigente 354 filas. La validación propia es algebraica y condicionada; no acredita cierre bancario ni producto integrado. Conteos anteriores describen sus hitos históricos.
