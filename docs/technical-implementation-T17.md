# Registro local de propuestas y concurrencia

T17 implementa un registro SQLite exclusivo de propuestas sintéticas, separado del archivo de evidencia. Permite registrar, retirar o sustituir por un descendiente exacto. Sus estados `recorded`, `withdrawn` y `superseded` describen el ciclo de la propuesta; ninguno significa aprobado, seleccionado para inversión o publicado.

Registrar exige recuperar y reproducir un paquete T16. Sustituir exige verificar tanto la propuesta anterior como la nueva y comprobar que la base nueva es exactamente el caso y ejecución candidatos anteriores, con el mismo documento y deal. Un fork distinto no sustituye una propuesta por coincidir en nombre. La retirada conserva la evidencia y los eventos; puede registrarse aunque la evidencia haya quedado inaccesible, sin afirmar que fue verificada.

Cada operación exige revisión global esperada, identidad de operación, etiqueta de actor y motivo. Revisión y evento avanzan juntos en una transacción local. Dos escritores que esperan la misma revisión no pueden confirmar ambos. Una operación con identidad y solicitud idénticas devuelve su recibo histórico, incluso después de cambios posteriores; esto no afirma que su estado siga vigente. Reutilizar la identidad con otra solicitud produce conflicto. Una propuesta retirada o sustituida no se vuelve a activar mediante otra retirada o un registro con el mismo nombre.

El registro conserva eventos y una proyección actual. Leer la proyección no reproduce automáticamente la evidencia y se marca `evidence_replayed=false`. `verify_entry` recupera el paquete y compara sus referencias antes de informar reproducción. La recuperación verifica hashes de recibos, sin convertirlos en prueba de identidad o protección frente a un administrador que pueda reescribir toda la base. No hay autenticación ni matriz de autoridad implementadas.

El archivo y la cola son dos bases distintas: no se afirma atomicidad entre ellas. Un paquete ya archivado puede quedar sin entrada si falla el registro posterior. La verificación cubre el momento de la operación o lectura; no es una garantía de vigencia distribuida ni una aprobación financiera. Las bases runtime se excluyen de GitHub y del ZIP documental.

API: `ProposalQueue(path)`, `record`, `withdraw`, `supersede`, `snapshot`, `history` y `verify_entry`. El formato tiene identidad de aplicación propia y rechaza una base del archivo de evidencia como cola. No tiene acciones de aprobar, publicar o invertir.

Son 17 pruebas nuevas: historia, padre exacto, evidencia anterior ausente, reintentos, identidad reutilizada, revisión obsoleta, nombre duplicado, rollback completo, evidencia faltante, reapertura, base incompatible, recibo alterado, validación de entradas, aislamiento de copias y dos escritores concurrentes reales. El fallo antes del commit conserva juntos la revisión, proyección e historial anteriores. Estos controles no cierran la publicación financiera atómica de M9.
