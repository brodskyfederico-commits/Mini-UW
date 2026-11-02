# T09 — Perfil candidato DSCR con bases y productores explícitos

T09 agrega el primer perfil nombrado de cálculo sintético: DSCR = NOI declarado / servicio de deuda declarado del mismo período. No deriva el NOI, no construye el calendario de deuda, no autentica bases bancarias y no compara el resultado con mínimos de aprobación. Permanece PENDING, sin despliegue ni decisiones reales.

## Definición y ubicaciones comprobadas

El despacho conserva ruta, línea y SHA-256 de cuatro referencias existentes, sin modificarlas ni atribuir aprobación profesional:

- `docs/model-refinance-contract.md:41`: cociente DSCR=N/DS y servicio cero indefinido.
- `docs/refinance-capacity-bridge.md:13`: equivalente anualizado de la cuota regular separado del efectivo de un año fechado.
- `docs/refinance-capacity-bridge.md:29`: servicio cero no produce DSCR cero o infinito.
- `sources/originals/95a304fd3e53__Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt:84`: contexto original de sizing por NOI/DSCR/constante anual, no implementación de esa capacidad ni activación de parámetros históricos.

La definición candidata del cociente está explícita en el contrato, no se considera cubierta solo porque el prompt nombre DSCR. Los documentos continúan con sus advertencias de alcance/revisión. Este perfil no cierra M6-05, M6 completo ni el contrato de servicio de deuda: esas ramas requieren definiciones, términos y resultados financieros adicionales.

## Entradas y enlace de productores

`DscrBinding` selecciona únicamente `SYNTHETIC-DECLARED-DSCR-v1` y exige revisión, dos nodos ascendentes distintos, revisiones esperadas de ambos productores, referencias de base de NOI y servicio, tipo de base temporal, unidad, moneda y período explícitos. El calculador T08 y la normalización T07 deben reproducirse exactamente desde el mismo snapshot y perfiles antes de usar cualquier importe.

El NOI y servicio deben ser cantidades `money_per_period` con unidad, moneda y período idénticos a los declarados. Un saldo de principal `money` no sustituye servicio. Bases, nombres de nodos y revisiones son declaraciones técnicas: no prueban que un NOI sea admisible para un banco ni que M2/M6 hayan producido correctamente esos flujos. La salida conserva `producer_role_claims_only=true` y `upstream_contracts_financially_verified=false`.

El perfil acepta dos bases diferenciadas: `declared_dated_period` y `regular_annual_sizing_equivalent`. La segunda exige la unidad canónica explícita `currency/annual-sizing-equivalent`; no se toma un importe mensual y se etiqueta como anual. No se multiplican cuotas, convierten calendarios ni verifican fechas desde identificadores opacos. La primera sigue siendo una declaración de período fechado, no evidencia de un calendario real ya conciliado.

Las etiquetas de salida distinguen `synthetic_dscr_for_declared_dated_period` de `synthetic_sizing_dscr_equivalent`, aunque coincidan los números. No se mezcla el NOI del inversor con NOI bancario por defecto; la referencia de base se exige y conserva sin certificar su contenido.

## Dominio y cálculo

Servicio cero o negativo queda fuera del dominio positivo de este perfil y bloquea el resultado. No hay infinito, cero inventado ni FAIL de inversión. NOI cero con servicio positivo produce cero; NOI negativo conserva el cociente negativo como álgebra, sin clasificación económica automática. Un productor bloqueado, revisión incompatible, unidad/moneda/período distintos o presupuesto técnico insuficiente también bloquean.

Al pasar los controles se compila un nodo de cociente sobre los productores explícitos y se reejecuta con T08, conservando todos los resultados ascendentes y huellas. La salida es una fracción exacta, con unidad de presentación `x` (veces), no una tasa porcentual. El fixture 1250/1000 produce 5/4 = 1,25x, sin concluir PASS/FAIL, crédito aprobado, precio admisible ni viabilidad. No se lee ni completa C72/min DSCR o los diez criterios de inversión.

## Evidencia y recuperación

El registro inmutable conserva binding completo, referencias documentales, source/contexto, hashes de normalización/grafo/ejecución ascendente, versiones del calculador/decodificador/dispatcher y la ejecución compilada o los bloqueos. Mantiene policy_adopted=false, financially_validated=false, run_ready=false y producción desautorizada. Cambiar la base o revisión sin aportar evidencia compatible no autentica un resultado.

T03 incorpora `save_scoped_profile` y `load_scoped_profile`, reutilizando la tabla de objetos sin migración. Se archiva snapshot, perfiles, normalización, grafo, resultado ascendente, binding, resultado y fuentes. Captura/recuperación reproducen toda la cadena y comprueban localizadores originales. Un resultado alterado con hash actualizado se rechaza por reproducción. Se requiere código y versiones documentales compatibles; los documentos se recuperan desde la misma revisión del repositorio y no se incrustan de nuevo en cada paquete runtime. Los bytes del paquete siguen disponibles por hash cuando no pueda reproducirse con el entorno actual.

El archivo no certifica autoría, revisión, vigencia frente a una cabecera que cambie después ni publicación atómica. Las bases runtime permanecen excluidas de GitHub y del ZIP documental. No se define jerarquía de fuentes, política de aceptación o mínimo bancario por la mera existencia de una referencia de base.

## Fixture y demostración

Las cuatro plantillas `synthetic-dscr-source.json`, `synthetic-dscr-profiles.json`, `synthetic-dscr-upstream-graph.json` y `synthetic-dscr-binding.json` declaran importes y roles ficticios. Los slots INPUT_C8/C9 se usan únicamente como portadores numéricos del fixture dentro de la interfaz existente; no se reasignan los significados del Input Sheet original ni se afirma que rentas de unidades sean NOI o servicio de deuda. Esta no es la conexión productiva M1→M2→M6. Los nodos se llaman explícitamente declared_noi y declared_service y el binding conserva que no fueron derivados por los módulos/calendarios financieros.

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_dscr.py
```

La demostración recupera exactamente 5/4x con referencias de documentos y mantiene cero criterios poblados y PENDING. Opera en memoria.

Dieciocho pruebas nuevas verifican el cociente/compilación, referencias documentales, servicio cero/negativo, NOI cero/negativo, faltantes, unidades/moneda/período y stock frente a flujo, revisiones de productores, bases no autenticadas, sizing equivalente separado, bindings inválidos, resultados ascendentes adulterados/de otro snapshot, inmutabilidad, recuperación desde disco, ratio falso con hash recalculado, fuente ausente, rollback y versiones de código/documentos incompatibles. Total: 205 pruebas técnicas; se mantienen aparte 26 suites de referencia, ocho fallos estructurales y 36 casos de aceptación financiera sin ejecutar contra producto integrado.

## Pendiente

Producción financiera del NOI admisible y servicio real, calendarios, integración con M2/M6/M7, dominio/aplicabilidad completa, comparación contra criterios documentados, revisión auténtica y publicación atómica. T09 es una implementación acotada de dispatcher candidato para IMP-02, con infraestructura IMP-01/IMP-06, y no cierra paquetes ni puertas financieras. No se implementa la capacidad de préstamo N/(DSCR mínimo×K) ni se deriva un mínimo de este diagnóstico.
