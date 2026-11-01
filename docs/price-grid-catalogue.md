# Catálogo de precios y condiciones por escenario — referencia candidata

Se amplía M8 con `schemas/price-grid-catalogue.schema.json` y `references/validate_price_grid_catalogue.py`. La referencia enumera una grilla finita explícita y evalúa relaciones polinómicas normalizadas expresamente suministradas. No deriva esas relaciones del modelo económico ni convierte el resultado en RLV aprobado.

## Dominio y unidades

El dominio declara límites inferior/superior, extremos abiertos/cerrados, origen de grilla, incremento, moneda/unidad/base/corte y una unidad monetaria positiva de normalización. Todos esos valores son entradas; no hay paso, tolerancia, origen cero o rango histórico predeterminado. Los precios negativos sólo aparecen si el dominio recibido los incluye; no se recortan silenciosamente.

La variable del polinomio es `x = precio / unidad monetaria de normalización`, por tanto adimensional. Los coeficientes racionales se suministran en orden ascendente de potencia y la condición declara comparación con cero (`>=`, `>`, `<=` o `<`). Se conserva la referencia a definición, revisión de criterio y evidencia. Que una relación sea sintácticamente válida no prueba que represente correctamente YoC, TIR, límites bancarios u otros cálculos de M1–M7.

Los índices admitidos se obtienen exactamente a partir de límites, origen y paso, conservando apertura/cierre. El conteo del dominio se calcula sin materializar todos sus puntos; sólo se recorren tantos como permita el presupuesto explícito de evaluaciones. Ese presupuesto limita puntos de esta referencia, no todas las operaciones internas ni el tamaño de los coeficientes.

## Escenarios, criterios y bloqueos

Se exige inventario explícito de escenarios y, en cada escenario, inventario de restricciones. Sus IDs deben corresponder exactamente a los registros recibidos; contextos de deal, corrida y revisiones deben coincidir, con el ID propio del escenario. No se completan restricciones desde Base, por posición de celda o por “última versión”.

Exclusión de un escenario necesita motivo, regla y evidencia expresos. Eso registra una afirmación de exclusión, no su autenticidad o aprobación. Un conjunto sin escenarios requeridos queda indeterminado, en lugar de afirmar soporte por una conjunción vacía.

Faltantes, conflictos, indefinidos y revisiones/definiciones no suministradas mantienen sus afirmaciones originales. Si una restricción requerida no se resuelve, el punto queda indeterminado aunque otra condición conocida no se satisfaga. Una grilla sin puntos tampoco convierte en resueltas las restricciones faltantes. Un cero conocido de precio o coeficiente se evalúa como tal.

## Clasificación acotada

| Evidencia | Salida de referencia |
|---|---|
| Todos los puntos recorridos y todas las relaciones requeridas definidas; alguno satisface la conjunción declarada | Máximo alcanzado dentro de la grilla declarada |
| Dominio finito completo y ninguna cotización satisface las relaciones declaradas | Conjunto vacío dentro de esa grilla |
| Presupuesto agotado, inventario/relación incompleto o conflicto | Indeterminado; conservar mejor candidato conocido sólo como diagnóstico |

La enumeración continúa después de una condición incumplida: no presupone monotonía ni una única frontera. Un ejemplo matemático usa `(x−1)(x−3)>=0` en [0,4], con componentes [0,1] y [3,4]; revisar sólo la primera frontera perdería el extremo 4. Añadir una condición de otro escenario puede cambiar el máximo de la intersección a 1. Ninguno de esos números es un dato o criterio de un deal.

Una grilla discreta y un intervalo continuo son dominios diferentes. Esta referencia no declara supremos continuos, ausencia de soluciones fuera del dominio ni un óptimo global de compra. La definición de todas las condiciones de precio de la casa, Q3, datos reales, derivación económica y su validación independiente siguen abiertas. “Candidato conocido” no autoriza una oferta ni un PASS/FAIL.

## Evidencia y límites

Se retienen 52 controles, incluidos 324 casos de grilla contrastados con una enumeración independiente de índices pequeños. Cubren extremos, origen distinto de cero, precios negativos, singleton/grilla vacía, no monotonía, escenarios y restricciones ausentes, conflictos, presupuesto parcial y conteos grandes sin recorrer el dominio completo.

Las salidas conservan PENDING, publicación desautorizada, `financial_model_certified=false` y `global_continuous_optimum_claimed=false`. No acreditan fuente auténtica, suficiencia del conjunto económico, aprobación de criterios/exclusiones, producto, RLV ni auditoría financiera. Los criterios reales y parámetros pendientes de Lorena continúan vacíos; R02 y originales permanecen intactos.
