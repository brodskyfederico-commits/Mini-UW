# T46–T47 — vigencia explícita de fuentes y salida sintética

Aplica el requerimiento de conservar PENDING ante evidencia vencida, estimada o sin revisar (observación profesional al resumen, p.1 punto 3). Es un perfil técnico sintético, sin autenticar documentos reales ni aprobación profesional. No sustituye la matriz de cobertura o la revisión financiera.

## T46: registro por fuente y localizador

La entrada declara contexto, inventario completo y requisitos ligados a SHA-256/localizador. Cada registro de evidencia identifica el requisito, la misma fuente/localizador, fecha de emisión, inicio/fin de vigencia, estado de revisión sintética, estado del valor, reemplazo por otra fuente y base de la declaración. Se conservan registros y conflictos: no se selecciona automáticamente el más reciente. Registros múltiples para un requisito necesitan resolución explícita en una nueva versión; no se borran evidencias anteriores del historial publicado.

La evaluación recibe una fecha/hora explícita UTC, con segundos y Z. La convención del perfil es [inicio, fin): inicio incluido y fin excluido; no se adopta como regla contractual o fiscal real. Se requiere emisión ≤ inicio < fin. Si falta cualquiera de esas fechas, se conserva PENDING; no se inventa TTL, antigüedad máxima o vigencia ilimitada. Fecha futura, expiración, fuente/localizador distinto, sustitución, base ausente, revisión pendiente/rechazada o valor estimado/no resuelto bloquean el requisito. Un registro de sustitución no habilita automáticamente su sucesor.

El estado accepted_synthetic es una etiqueta suministrada en una prueba, no un revisor autenticado ni autorización. Los resultados son válidos solo al instante indicado. Evaluar en otro instante requiere otra ejecución y produce otro hash; no hay reloj implícito, monitor o actualización automática de archivos.

## T47: conexión con venta y retornos

Se reproduce T44 completo y T46 exactamente al instante solicitado. El inventario debe cubrir cada binding de bytes de fuente de la cadena: NOI/caja operativa, cierres/deuda/préstamos, manifiesto, slots del inversor, fuentes de sizing y sus especificaciones, NOI forward, valoración, costos y especificación de la conexión. Los aliases con mismos bytes se conservan por binding. Faltantes, extras, cambios de hash/localizador/contexto bloquean; el orden de las filas no afecta la comparación.

Estos bindings describen fuentes técnicas transportadas por el prototipo. No prueban que sus referencias textuales enlacen todos los documentos externos originales ni que sus valores sean auténticos, actuales o aprobados en un deal real. Completitud financiera y autenticación de originales siguen pendientes aun con todos los registros de prueba vigentes.

Solo cuando el cálculo guardado compila y el registro coincide/está vigente se expone el resumen sintético de equity del proyecto a ese instante. Ante vencimiento se retira ese resumen del nuevo resultado actual; se conserva el hash y los bloqueos del cálculo histórico sin modificar sus cifras ni fuentes. Bloqueos bancarios/valoración/impuestos también permanecen visibles, incluso si la evidencia está vigente. La salida sigue PENDING para decisiones: ni cifras calculables ni vigencia técnica completan el retorno personal o autorizan publicación financiera.

La conexión es optativa y nueva; los APIs anteriores siguen como cálculos sintéticos aislados y no adquieren esta validación retroactivamente. No hay despliegue, PDF externo, base SQLite nueva, aprobación ni decisiones reales.

## Validación

Pruebas de límites temporales exactos, fecha ausente/expirada/futura, cambio de fuente/localizador, estimaciones/revisión/sustitución, conflictos y completitud; integración con todos los bindings, conservación de fallos conocidos y de cifras históricas, y rechazo de resultados manipulados aun con hashes recalculados. Un registro renovado necesita nueva fuente/ejecución y no desbloquea otros faltantes. Las demostraciones son completamente sintéticas y no cierran casos financieros originales.
