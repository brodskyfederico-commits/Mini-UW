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
