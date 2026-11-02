# Mini-UW — estructura integral de armado I01

Repositorio privado de fuentes, diseño y referencias. La consolidación del armado independiente se verifica por ocho entregables explícitos; la validación financiera, los datos reales, las decisiones expertas y la implementación completa conservan sus puertas abiertas. Producción, evaluación de deals y despliegue siguen pausados.

## Leer el paquete consolidado

- [Especificación integral en español](docs/Especificacion_Integral_Armado_I01.md).
- [PDF interno integral I01](docs/review/MiniUW_Especificacion_Integral_Armado_I01.pdf).
- [Acta y criterios del cierre de armado](docs/independent-structure-closeout.json).
- [Registro de 84 contratos, 33 salidas y dependencias](docs/structural-integration-register.json).
- [Inventario final de pendientes externos y de implementación](docs/final-dependency-register.json).
- [Matriz de cobertura](docs/coverage-matrix.csv) y [guía de evidencia](docs/coverage-guide.md).

La matriz mantiene 398 filas y no certifica cobertura financiera de extremo a extremo. Los originales suministrados son 16 archivos únicos en [el registro de fuentes](docs/source-register.json); sus 19 ocurrencias se conservan. El Input Sheet contiene 55 campos vacíos; los diez criterios de la plantilla siguen sin umbral. Ningún número histórico se activa por defecto.

## Límites y operación del paquete

Faltantes de datos/reglas requeridos mantienen PENDING sin PASS/FAIL. Lorena aportará su hoja/criterios por deal; las demás fuentes GC/banco y reglas aplicables también requieren evidencia. Full UW se entregará al final y no fue requisito para consolidar este diseño. [Instrucciones de entrada y decisión](docs/decision-input-contract.md).

El PDF externo futuro del deal será exactamente una página; I01 es documentación interna extensa. R01/R02 permanecen intactos y la revisión pendiente sigue vinculada a R02: I01 no es aprobación profesional. [Puertas financieras por módulo](docs/module-closure.json), [recuperación histórica](docs/recovery-status.md) y [conflictos](docs/requirements-conflicts.md).

El paquete registra 25 suites de referencias acotadas y una de consolidación estructural. [Cómo ejecutar el control](docs/reference-check-runbook.md). GitHub Actions comprueba el commit exacto; su resultado no certifica otros commits ni el modelo completo. El comprobante externo de respaldo conserva SHA remoto, blobs verificados, resultado CI y exclusiones.

GitHub preserva los materiales publicados; runtime, bases de datos, secretos, documentos de deals reales y la aplicación original no recuperada quedan fuera de este backup. No hay despliegue o sincronización de servicios configurados. [Historial de hitos y límites](WORK_LOG.md).

## Implementación técnica posterior a I01

El usuario autorizó implementar con datos sintéticos, sin despliegue ni decisiones reales. El primer componente T01 conserva declaraciones literales, fuentes declaradas y versiones transaccionales locales; no calcula ni emite PASS/FAIL. [Alcance, uso y pruebas T01](docs/technical-implementation-T01.md), [estado técnico vigente](docs/technical-implementation-status.json) y [restauración comprobada del respaldo I01](docs/backup-restoration-I01.json). Los registros I01 permanecen como fotografía del diseño; el estado técnico posterior se registra aparte.

T02 agrega ejecución de dependencias sintéticas y detección de resultados afectados por cambios de fuente, definición o contexto. Mantiene por separado la vigencia del snapshot completo y las huellas de ramas independientes. [Alcance y demostración T02](docs/technical-implementation-T02.md). Total actual: 52 pruebas técnicas; la ejecución financiera integrada y publicación siguen pendientes.

T03 agrega un archivo durable local de fuentes sintéticas y paquetes de ejecución. Al recuperar, verifica los bytes, localizadores y reproducción con la versión compatible del ejecutor. [Alcance y demostración T03](docs/technical-implementation-T03.md). Total: 74 pruebas técnicas. Las bases runtime quedan fuera del respaldo documental de GitHub; las demostraciones usan archivos temporales.

T04 conecta hojas CSV sintéticas con la importación, procedencia y recuperación de ejecuciones, sin ejecutar fórmulas ni asumir el formato final de Lorena. [Contrato y demostración T04](docs/technical-implementation-T04.md), [ejemplo sintético](templates/synthetic-sheet-example.csv). Total: 96 pruebas técnicas. La lectura XLSX y el motor financiero integrado siguen pendientes.

T05 agrega un primer lector XLSX sintético: conserva referencias de celdas y distingue literales, vacíos, fórmulas y cachés. Las fórmulas y errores mantienen el valor sin resolver; nunca se ejecutan ni se adopta su caché. [Contrato y demostración T05](docs/technical-implementation-T05.md), [fixture XLSX](templates/synthetic-workbook-example.xlsx). Total: 118 pruebas técnicas. Este perfil de prueba no completa la adaptación de la hoja real de Lorena ni el motor financiero integrado.

T06 conecta una copia sintética del Input Sheet original: los 55 campos de `Inputs` se mapean por celda exacta, con unidades y metadatos verificados contra el formato documentado. No infiere moneda/período ni rellena criterios. [Contrato y demostración T06](docs/technical-implementation-T06.md), [fixture nativo marcado](templates/synthetic-native-inputs-example.xlsx). Total: 136 pruebas técnicas. No certifica una hoja real completada ni el motor financiero.

T07 decodifica números sintéticos con perfiles explícitos y precisión racional exacta. Bloquea metadatos ausentes/incompatibles y conflictos; no interpreta `$` como moneda ni reutiliza automáticamente valores ante una nueva fuente vacía. [Contrato y demostración T07](docs/technical-implementation-T07.md). Total: 162 pruebas técnicas. La conversión sintáctica no completa la normalización financiera ni habilita decisiones.

T08 conecta números normalizados con aritmética sintética exacta y tipada: suma/resta, escala por fracción explícita y cocientes compatibles. Bloquea división por cero e incompatibilidades de unidad/moneda/período y reproduce la cadena completa desde evidencia archivada. [Contrato y demostración T08](docs/technical-implementation-T08.md). Total: 187 pruebas técnicas; las fórmulas y decisiones financieras del motor integrado siguen pendientes.

T09 agrega un perfil candidato de DSCR a partir de NOI/servicio declarados y reproducibles, con revisiones y bases explícitas. Separa servicio de período declarado del equivalente anual de sizing; no deriva NOI/deuda ni aplica mínimos o PASS/FAIL. [Contrato y demostración T09](docs/technical-implementation-T09.md). Total: 205 pruebas técnicas; el motor financiero integrado sigue pendiente.

T10 produce cuotas y saldos sintéticos desde términos explícitos, distingue amortización/maturity/balloon y agrupa importes debidos por fechas suministradas. DSCR puede consumir este servicio calculado, con selección explícita de balloon y sin afirmar efectivo pagado. [Contrato y demostración T10](docs/technical-implementation-T10.md). Total: 229 pruebas técnicas; ningún paquete financiero completo queda cerrado.

T11 compara métricas y criterios sintéticos expresos, preserva bandas/conflictos y prioriza PENDING ante faltantes. Las clasificaciones son solo simulaciones; la decisión operacional queda PENDING. [Contrato y demostración T11](docs/technical-implementation-T11.md). Total: 250 pruebas técnicas. El usuario resolvió la banda intermedia en T12: PENDIENTE para revisión profesional.

T12 aplica la decisión del usuario de conservar bandas intermedias PENDIENTES y prepara su revisión sin alterar variables automáticamente. Nuevos valores/criterios requieren nueva evidencia y recalculación; las versiones previas se conservan. [Regla, alcance y pruebas T12](docs/technical-implementation-T12.md). Total: 254 pruebas técnicas. No habilita decisiones reales ni despliegue.

T13 registra propuestas sintéticas de revisión, conserva el caso original y vuelve a comparar una versión candidata con cambios explícitos y evidencia declarada. [Contrato y demostración T13](docs/technical-implementation-T13.md). Total: 273 pruebas técnicas. Las propuestas no equivalen a revisión profesional autenticada ni a decisiones reales.

## Ampliación del diseño de revisión

[Propuestas, revisión y vigencia](docs/review-lifecycle-design.md) desarrolla M9 después de T13: estados separados, revisión del contexto, revocación, concurrencia y entrega externa. Incluye 15 reglas trazables y 28 casos de aceptación especificados, aún sin ejecutar. Es diseño documental; no añade código runtime ni habilita decisiones reales. [Estado de ampliaciones de diseño](docs/design-evolution-status.json).

[Entrada de métricas y criterios D03](docs/metric-intake-design.md) especifica la hoja aportada, metadatos, conciliación y bloqueos sin inventar su layout. Conserva diez IDs del catálogo y agrega una plantilla vacía y 28 casos futuros, sin código runtime. D02/D03 suman 56 casos de diseño especificados, no ejecutados.

T14 ejecuta el comparador con la tabla documentada de Lorena y métricas ficticias, sin activar umbrales para deals. Reproduce PASS/FAIL/PENDIENTE en alcance Base y revela once bloqueos de compatibilidad en Base/Downside: el contrato actual exige FAIL por escenario, mientras la fuente sólo define FAIL Base, y asking/RLV Downside carece de PASS. [Alcance y reproducción T14](docs/technical-implementation-T14.md), [resultados del ensayo](docs/documented-threshold-rehearsal-validation.json). Total: 290 pruebas técnicas; el Mini-UW completo sigue pendiente.
