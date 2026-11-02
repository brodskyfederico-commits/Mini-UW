# T02 — Dependencias y vigencia de ejecuciones sintéticas

Implementación autorizada con datos sintéticos, sin despliegue ni decisiones reales. T02 continúa la base T01 mediante un ejecutor de grafos acíclicos explícitos y un observador de vigencia. No implementa ni certifica los 84 contratos financieros del diseño I01.

## Comportamiento comprobado

Cada nodo declara identidad, operación, revisión de definición, dependencias y campos fuente. Se rechazan identidades repetidas, dependencias desconocidas, ciclos y configuraciones mutables. Los ciclos financieros del diseño requieren pasadas o solvers expresos posteriores; este ejecutor no los resuelve ni elige iteraciones.

Se ejecutan únicamente tres operaciones de demostración: conservar un literal/valor, contar caracteres de texto y sumar enteros derivados. Son herramientas para comprobar la infraestructura: no calculan rentas, costos, retornos ni umbrales. No interpretan porcentajes, monedas, fórmulas o fechas. El texto `=1+1` permanece texto. Una declaración no verificada solo se inspecciona como fixture sintético; nunca se convierte en evidencia financiera validada.

Los campos vacíos o con declaraciones contradictorias bloquean su nodo y sus descendientes. Las ramas independientes pueden producir resultados sintéticos. Una incompatibilidad de tipo se registra como bloqueo, sin reemplazarla por cero ni FAIL. Los criterios vacíos permanecen vacíos; agregar una declaración sintética no adopta una política.

La ejecución conserva fuente exacta (borrador, revisión, SHA-256 y contexto), definición de grafo, hash de los bytes del ejecutor, declaraciones con sus localizadores y huellas de las dependencias. Los objetos devuelven copias JSON; no reescriben revisiones T01. El resultado completo sigue `PENDING`, `run_ready=false`, sin autorización de producción.

## Invalidación y vigencia

La huella de cada nodo incluye su definición, referencias, declaraciones completas, procedencia, contexto de deal/escenario/run/definiciones y huellas ascendentes. Un cambio de fuente invalida el nodo y todos sus descendientes incluso si el texto y el resultado numérico coinciden. Las ramas independientes conservan su huella. Cambios de operación, versión, conexión, nodos añadidos o eliminados también se exponen. Se incluye la identidad del código de `execution.py`; no se certifica aquí un entorno completo firmado o reproducible.

La revisión global de inputs se conserva en la ejecución, pero no se incorpora a cada huella de rama para permitir observar dependencias selectivas. Si cambia un campo no referenciado, puede no haber ramas afectadas, pero la ejecución antigua NO queda vigente para la nueva revisión. `entire_run_current` exige coincidencia de fuente exacta y grafo completo; significa únicamente vigencia observada, no corrección financiera, completitud ni permiso de publicar.

`observe_freshness` compara contra el snapshot suministrado por el llamador. No relee por sí solo la cabecera de la base y no bloquea cambios posteriores: no es la verificación transaccional de publicación futura. El llamador debe obtener el snapshot observado desde T01. No se usa caché: todos los nodos se vuelven a ejecutar, aunque sus huellas no hayan cambiado. La evidencia T02 es un objeto serializable en memoria; su archivo durable y la publicación atómica permanecen pendientes.

## Reproducir

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_dependencies.py
```

La demostración usa SQLite en memoria, no modifica archivos y cuenta los caracteres de `abc` y `xy` (3 y 2, total 5). Añade una segunda fuente para el mismo texto y muestra invalidados `length-a` y `total-length`, con `length-b` sin cambios. La ejecución antigua deja de estar vigente.

Las 21 pruebas T02 verifican orden topológico, propagación de faltantes/conflictos, aislamiento de contextos, versiones y topología, cambios no referenciados, integridad de snapshots, tipos, criterios y una ruta completa importación T01 → almacenamiento → ejecución T02. Sumadas a las 31 pruebas T01, son 52 pruebas técnicas. Se mantienen aparte las 26 suites de referencias y los 36 casos de aceptación financiera del producto todavía no ejecutados.

## Pendientes independientes y externos

Sigue pendiente implementar almacenamiento durable de ejecuciones/fuentes, adaptadores adicionales sintéticos, integración de perfiles de cálculo definidos y validación de sus unidades/fechas. T02 cubre parcialmente IMP-06; no cierra paquetes del plan completo. Las reglas financieras, escenarios y criterios no definidos/aportados siguen bloqueados hasta contar con evidencia; ninguna operación de demostración los sustituye. No hay deploy, API pública, datos de deals reales, aprobación profesional ni decisión de inversión.
