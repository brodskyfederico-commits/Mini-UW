# T08 — Conexión de números exactos con aritmética sintética tipada

T08 conecta los números decodificados por T07 con un grafo explícito de operaciones aritméticas. Implementa una base de cálculo técnico, no los 84 contratos financieros ni las políticas de underwriting. El alcance sigue siendo sintético, sin despliegue ni decisiones reales.

## Operaciones y contratos

Cada operando identifica un input normalizado o un nodo ascendente. Cada nodo declara identidad, revisión, operación y operandos; el grafo declara ID sintético y revisión. Se rechazan ciclos, nodos duplicados, dependencias desconocidas, constantes implícitas, expresiones ejecutables y aridades inválidas. No hay solver automático ni evaluación de fórmulas del Excel.

Operaciones disponibles: identidad, suma no vacía, diferencia ordenada, escala por una fracción explícita y cociente entre cantidades compatibles. Los resultados conservan fracciones exactas; no se introducen floats, redondeos ni tolerancias financieras. Una suma vacía no se convierte por defecto en cero. Los signos se conservan como álgebra; esto no aprueba un presupuesto negativo ni resuelve dominios financieros pendientes.

Suma/diferencia/cociente exigen coincidencia exacta de tipo de cantidad, unidad, moneda y período. Un cociente compatible produce una fracción adimensional y una escala conserva la cantidad del operando izquierdo. El factor de escala debe declarar tipo scalar, unidad fraction, sin moneda/período: una etiqueta decimal no se reinterpreta silenciosamente como fraction. No se convierten aliases de unidades, monedas, meses/años ni calendarios. Estas comprobaciones comparan contratos declarados; no certifican que una definición económica esté aprobada ni validan un calendario real.

Dividir por cero queda bloqueado, sin infinito, cero inventado ni FAIL. Un input bloqueado por T07 bloquea su nodo y descendientes; las ramas independientes pueden producir resultados sintéticos. Cada input usado debe tener un perfil numérico explícito: no se crea uno por defecto.

## Integración y límites

`calculate_synthetic` exige que la normalización suministrada se reproduzca exactamente desde el snapshot/perfiles actuales. Rechaza números modificados o procedentes de otra revisión/contexto, aunque sus hashes hayan sido actualizados. No se conecta automáticamente un resultado de normalización con el grafo textual T02 ni se modifica ese ejecutor histórico.

Cada resultado conserva la definición del nodo, referencias y huellas de operandos, cantidad de salida, fracción y bloqueos. La ejecución completa conserva snapshot/contexto, hash de normalización, versión del decodificador, grafo y versión del calculador. Es inmutable y siempre mantiene PENDING, run_ready=false, financially_validated=false y producción desautorizada. No modifica inputs ni criterios de inversión.

Límites técnicos: 256 nodos, 256 operandos por nodo y 4096 bits por numerador/denominador reducido. Si un resultado intermedio excede el límite, se bloquea y propaga el bloqueo sin redondearlo. Los operandos ya están acotados antes de operar; este límite controla crecimiento computacional, no precisión ni aceptación del modelo. No hay caché ni reutilización automática: cada ejecución vuelve a calcular sus nodos.

## Dependencias y vigencia

Las huellas vinculan código, contexto de deal/escenario/run/definiciones, grafo/nodo y evidencia/perfiles de cada input o nodo ascendente. Cambiar una definición de perfil o nodo invalida su rama y descendientes, aunque el número final coincida. Las ramas independientes pueden conservar su huella.

La vigencia del registro completo exige además coincidencia exacta de snapshot, normalización, grafo y calculador. Si cambia un input no usado, puede no haber ramas afectadas, pero la ejecución antigua no se presenta como vigente para el nuevo snapshot. El informe de vigencia es una observación sobre el snapshot proporcionado; no bloquea ediciones posteriores, certifica corrección financiera ni autoriza publicar.

## Archivo reproducible

T03 incorpora `save_calculation` y `load_calculation` con un esquema de paquete tipado, reutilizando la tabla de objetos sin migración. El paquete conserva snapshot completo, perfiles numéricos, normalización, grafo, ejecución, versiones e inventario de fuentes. Captura y recuperación comprueban las fuentes y reproducen toda la cadena. Un hash recalculado de un resultado falso no supera esa reproducción.

Se requiere código compatible tanto para decodificar como para calcular; una versión distinta bloquea la recuperación verificada, mientras los bytes siguen disponibles por hash. Los hashes no autentican personas ni garantizan resistencia frente a un administrador que reescriba toda la evidencia. La transacción del archivo no concede vigencia de la cabecera del borrador ni implementa publicación atómica. Las bases runtime siguen excluidas del repositorio y ZIP documental.

## Demostración y pruebas

`templates/synthetic-calculation-graph.json` reutiliza los datos/perfiles de ejemplo T07. La demostración escala 1250 por 1/20 para obtener 125/2, calcula la diferencia 2375/2 y el cociente 19/20. Son operaciones ficticias de prueba, no NOI, rentabilidad, DSCR ni métricas financieras aprobadas. Otra rama permanece bloqueada por moneda ausente, su descendiente hereda el bloqueo y un factor con unidad incompatible también se bloquea.

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_calculation.py
```

Veinticinco pruebas nuevas verifican operaciones exactas, orden topológico/procedencia, cero y signos, división indefinida, moneda/período/unidad/tipo incompatibles, factores explícitos, faltantes/conflictos, perfiles requeridos, rechazo de normalización falsa o de otro snapshot, grafos inválidos, inmutabilidad, aislamiento de criterios, invalidación selectiva/global, crecimiento computacional, reapertura/reproducción, resultado falsificado, fuente ausente, rollback y versiones incompatibles. Total: 187 pruebas técnicas. Se mantienen aparte 26 suites de referencia, ocho fallos estructurales y 36 casos de aceptación financiera sin ejecutar contra producto completo.

## Pendiente

Este bloque aporta infraestructura aritmética para la futura implementación de IMP-02 y trazabilidad de IMP-01/IMP-06; no cierra ninguno de esos paquetes. Faltan dispatcher de perfiles financieros definidos, integración de los contratos/calendarios, reglas de completitud/comparación, resoluciones profesionales, revisión auténtica y publicación atómica. La normalización financiera y el motor integrado permanecen pendientes.
