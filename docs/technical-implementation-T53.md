# T53 — frontera contrastada con un cierre completo suministrado

Se reproduce el análisis por tramos T51 y, por separado, un caso candidato completo T49. No se generan automáticamente precios, escenarios o cambios destinados a obtener PASS. El llamador suministra el caso y conserva sus fuentes originales.

## Compatibilidad con la curva

El proyecto, deuda, operaciones, refi, slots del inversor, funding y NOI forward deben permanecer idénticos al caso de referencia. Solo se permiten cambios de valor/fuente del exit cap, precio bruto y linaje, hashes derivados de costos/límites/conexión e ID de revisión. Cargos, límites, fechas, moneda, reglas y referencias de hipótesis no se sustituyen silenciosamente. Cambiar una condición fija requiere un nuevo análisis y su evidencia.

El candidato debe estar dentro del dominio y compilar por sus propios controles de valoración, cierre, deuda, continuidad de caja, capacidad bancaria y aportes/targets. Un cálculo de frontera no reemplaza esos controles. Se conservan los bloqueos del candidato y de la referencia.

## Comprobación exacta

Se evalúan todas las fórmulas de los tramos que contienen el precio candidato, incluidos los dos tramos en un quiebre compartido. Deben coincidir entre sí y con el costo y resultado neto de caja del caso completo. Las diferencias son racionales exactas, sin tolerancia o redondeo adoptado. Se conservan aportes/cobros brutos, EM e intervalos/raíces IRR del candidato; resultado cero no equivale a aprobación.

Se comprueban casos explícitos antes, en y después de una frontera y de los puntos donde se activan mínimos/topes. Un precio que no compila por funding, valoración, banco o costo queda bloqueado, aunque la ecuación aislada tenga resultado positivo.

## Alcance y evidencia

El estado matched_synthetic_full_case valida únicamente compatibilidad matemática con las hipótesis y fuentes dadas. No autentica contratos, mercado, revisión, vigencia documental o capital disponible. La vigencia debe evaluarse separadamente con T50/T52 y registros correspondientes; esta comprobación no autoriza publicación financiera. Retorno personal, pérdida económica definitiva y decisiones reales siguen pendientes.

Los hashes ligan referencia, análisis, candidato, código y definición. Replay rechaza resultados alterados incluso con hash actualizado. Presupuesto aritmético agotado bloquea sin comparación parcial. No se cambia el perfil T51 ni sus conjuntos; no se agrega un bundle SQLite runtime, despliegue o Full UW. Validación técnica sintética, sin cierre de aceptación financiera original.
