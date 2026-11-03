# T85–T87 — Mini-UW v1, integración sintética

## T85: entrada única y ejecución

Una entrada JSON versionada contiene identificación/revisión, contexto sintético, instante UTC, los 55 campos originales, diez criterios nuevos por deal, fuentes financieras estructuradas y registro de vigencia. El perfil v1 admite obra por draws → misma deuda operativa → renta residencial por tramos → gastos → tenencia → venta, sin refinanciación intermedia. Los demás perfiles anteriores se conservan y no se presentan como integrados en esta ruta. No es adaptación terminada de la hoja real de Lorena ni cierre de los 84 contratos financieros.

El catálogo de 55 campos permanece completo y separado del expediente complementario. Un campo puede vincularse explícitamente mediante JSON Pointer a una fuente de la entrada, con valor, unidad, período y base de mapeo declarados; el valor debe coincidir exactamente. Campos no mapeados o faltantes siguen pendientes y bloquean la decisión global; no se proclama que los 55 alimenten el motor. El perfil puede mostrar su proyección sintética condicionada desde las fuentes complementarias completas y vigentes, con la incompletitud del formulario visible. No se ignora una entrada contradictoria ni se aplican rangos o unidades aprobados inexistentes.

La corrida reconstruye todos los productores desde las fuentes declarativas. Sólo genera hashes, referencias y enlaces técnicos; no completa importes, fechas, inventarios económicos, eventos financieros, criterios, bases de reparto o declaraciones de autoridad. Requiere slots de equity y mapas completos expresamente suministrados. No contiene resultados esperados ni paquetes precalculados como entrada económica. Una inconsistencia previa detiene sus dependencias y retira cifras actuales; otra corrida debe usar fuentes compatibles, sin reparaciones para obtener PASS.

La vigencia conserva los hashes/localizadores y fechas expresos del registro. No se reacepta evidencia al modificar un dato ni se infiere TTL. El nuevo cálculo genera fuentes exactas que deben coincidir con ese registro. Los diez criterios empiezan sin umbrales; sólo EM se ofrece al comparador como valor puntual derivado en este alcance. IRR conserva todas sus raíces/intervalos y no se convierte en un punto elegido. Las otras métricas permanecen pendientes con motivo; valores hipotéticos de Lorena nunca sustituyen resultados propios. Comparaciones son simulaciones y la decisión operacional siempre PENDING.

## T86: una página, evidencia y comprobación técnica

Una orden local produce results.json, paquete recuperable de ejecución, resumen PDF de exactamente una página, manifiesto de cifras/ubicaciones, comprobación técnica y package.json con hashes. El resumen muestra aportes/cobros y fechas, referencia por 10 y base, operación/refi/cash-in/venta, EM/IRR, capital/equity/CoC pendientes, diez métricas y criterios, bloqueos y riesgos. La simulación no autoriza una decisión real o entrega financiera externa.

Las cifras se obtienen únicamente del resultado reproducido. El PDF usa redondeo de presentación explícito, sin tolerancia financiera ni selección de raíz. Una fuente vencida o cálculo bloqueado impide mostrar sus cifras históricas como actuales. Desbordes, caracteres incompatibles y resultados no representables se rechazan sin recortar cifras o agregar páginas. La comprobación determinista reproduce el resultado y el PDF, verifica una página/texto/huellas y registra su alcance; no es auditoría financiera o revisión humana independiente.

El directorio de salida se materializa completo tras las comprobaciones, sin reemplazar una corrida diferente. Una repetición idéntica sólo se acepta tras verificar cada archivo y el inventario exacto. Esto protege artefactos locales de prueba; no implementa publicación productiva, autenticación, servicios, bases runtime o bots externos.

## T87: contratos de Dots y bots

Se definen siete Dots y los 17 roles históricos de bot, con entradas, salidas, dependencias, bloqueos y estado real de implementación. Es una consolidación funcional nueva basada en las fuentes conservadas, no prueba de agentes desplegados. Lectores de planos/finanzas y búsqueda/verificación oficial quedan con contrato y bloqueos; no realizan extracción, takeoff o consultas externas. Los roles operativos existentes se conectan al ejecutor local de prueba. El rol 16 tiene comprobación determinista, no independencia profesional; el 17 corresponde a pruebas de versión y no se afirma ejecutado en cada deal.

La banda intermedia y los faltantes permanecen PENDING por decisión del usuario. Los criterios históricos no son defaults. Las recomendaciones de modelos, proveedores, plataformas, fuente jerárquica o publicación contenidas en documentos históricos no se adoptan. Full UW/condominios, aprobación real, parámetros sin evidencia, auditoría financiera y despliegue siguen fuera del alcance.
