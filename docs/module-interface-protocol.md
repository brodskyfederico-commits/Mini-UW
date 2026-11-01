# Interfaces de módulos y vocabulario estructural — candidato 0.1

Trabajo independiente de la revisión: definir cómo se intercambian registros y bloqueos, sin escoger umbrales o políticas financieras. Se añaden nueve interfaces M1–M9 y un vocabulario común en `schemas/`. Son contratos de estructura para diseño/referencias, no motor de producción ni representación completa de todos los detalles económicos.

## Qué separa el protocolo

Cada registro identifica deal, escenario, corrida, revisión de entradas y conjunto de definiciones. Hechos documentales, términos bancarios, criterios de inversión y resultados derivados deben tener procedencias y espacios separados en el paquete de ejecución. La estructura no copia datos de Base a otro escenario ni completa criterios vacíos. Compartir fuentes requiere una referencia expresa/versionada.

La cantidad conocida lleva valor racional exacto, dimensiones, unidad literal/normalizada, moneda explícita cuando es monetaria, rol de medida, base, período y fuentes. Stock, total de período, cotización por unidad/tiempo, ratio, conteo y superficie no son intercambiables. La misma dimensión física no hace equivalentes GSF y NRSF ni un importe de distintos períodos. El símbolo $ no determina moneda.

Valores faltantes, inválidos, contradictorios o indefinidos no contienen un número de sustitución; preservan causas. No aplicable necesita razón/regla/fuente; citar una regla no acredita por sí solo su autoridad. Un cero conocido conserva su fuente y unidad; no es faltante ni necesariamente una entrada financieramente válida.

Cada módulo entrega puertos agregados y sus estados; los ledgers y desgloses detallados conservan sus contratos específicos y se vincularán por evidencia en la futura integración. Tener todos los puertos no demuestra que exista toda la evidencia necesaria. El bloque financiero circular sigue pendiente de solución y validación real.

## Tres niveles de validación

1. Esquema: campos/tipos/estados y forma de referencias, con JSON Schema 2020-12 y resolución local, sin consultas de red.
2. Semántica de intercambio: coherencia de contexto, moneda/unidad/base/período, valor racional y causas de bloqueo. El ejemplo aritmético es referencia aislada, no regla de underwriting.
3. Modelo financiero y liberación: aplicabilidad, fuentes auténticas, criterios aprobados, fórmulas/integración/casos independientes y autorización. No están acreditados por los niveles anteriores.

Los registros usan siempre autorización `not_granted` y propósito de diseño/referencia. `candidate_complete` describe únicamente disponibilidad estructural del ejemplo; no equivale a PASS, autenticación, validación financiera ni producto listo. El módulo M9 bloqueado sólo permite PENDING. El precio límite distingue máximo alcanzado de supremo/no solución/indeterminado; no es automáticamente una cotización admitida.

## Propagación de causas

Si una operación requiere dos cantidades y una falta o es contradictoria, se conserva la unión de sus causas y no se calcula un cero. Si una rama no depende de ese dato, puede seguir diseñándose/validándose de forma independiente. Esto no libera un deal real detenido por C1 ni autoriza a publicar resultados parciales como conclusión.

No se suman cantidades de monedas, unidades, bases o períodos diferentes sin transformación explícita y respaldada. No se convierten años/meses o tasas por conveniencia. División por cero devuelve estado indefinido con causa, no infinito o cero. La no aplicabilidad de un operando requiere una regla del cálculo; no se toma como cero automáticamente.

La prueba estructural/semántica se ejecuta en `references/validate_interface_contracts.py`. No valida un motor, una identidad oficial, persistencia, una aprobación humana o publicación transaccional. R02 permanece intacto para revisión; estos contratos son posteriores a su corte.
