# T79–T81 — entrada en operación, renta mensual y retorno

## T79: calendario mensual de renta residencial

El perfil reducido reproduce cada fuente T21 suministrada para un mes calendario completo, desde el primer día hasta el primer día del siguiente mes. Exige inventario completo, fechas contiguas, contexto/moneda/períodos exactos, y bases expresas de calendario e inventario. No interpola un mes faltante, no copia ocupación/renta anterior ni convierte un período parcial en un mes completo. Conserva un inventario fijo de grupos, unidades y área/basis de renta durante el calendario; disponibilidad física por etapas requiere otro perfil.

Cada mes suministra renta, fracción de pérdida y concesión con su base T21. Se conservan renta potencial, pérdida, concesión y renta efectiva por separado, incluyendo cero y resultados negativos matemáticos sin clamping. La pérdida T21 no demuestra ocupación física: puede representar conceptos distintos según su fuente. El ejemplo declara vacancia como su única pérdida, sin adoptar esa clasificación para deals. No se inventan contratos, absorción, velocidad de alquiler, fecha de estabilización o políticas de mercado.

T79 sólo produce ingreso residencial. Los campos de gasto exigidos por T21 deben ser placeholders explícitos de importe cero; un gasto mensual no cero bloquea este perfil para evitar excluirlo o sumarlo dos veces. Los gastos reales del alcance sintético siguen suministrados por separado al NOI y se concilian con T76/T77. Se suman exactamente los resultados mensuales; cualquier fallo, fuente faltante o exceso del presupuesto aritmético retira todos los totales exportables.

## T80: renta a NOI, caja y retorno de compra a venta

Se reproduce íntegramente el paquete T77 y su recorrido T75/T74, junto con un calendario T79 para cada período operativo, en inventario completo ordenado. Cada calendario coincide en fechas, período, moneda y contexto con la fuente NOI/caja correspondiente. Su renta efectiva debe igualar exactamente la fila residencial vinculada del NOI. Todas las demás filas de ingreso deben inventariarse expresamente y valer cero en este perfil residencial; no se declara que el proyecto carece de otras fuentes reales.

El objetivo conserva su ID económico y el inventario físico declarado entre períodos. Se requieren hashes exactos de las fuentes NOI/caja y del paquete anterior, más bases de alcance/no solapamiento y reconocimiento del período. El detalle mensual no se usa para completar o sobrescribir el NOI. Un cambio de renta exige nueva fuente NOI/caja y reproducción de toda la cadena; no basta con modificar el ledger final. No se valida liquidez intramensual o distribución antes de generar/cobrar ingresos.

Sólo una cadena compatible expone exactamente el ledger y retorno ya reproducidos, sin sumar rentas como un segundo cobro ni restar nuevamente los gastos. Conserva aportes/cobros brutos, normalización expresa, EM, todas las raíces/intervalos de IRR y riesgos. El retorno personal, CoC, capital y equity retenido conservan sus bases pendientes. Una renta incompatible, un mes/período omitido o cualquier bloqueo de deuda/gastos/caja retira los retornos exportables. No se genera aporte, financiación o cambio de reparto para reparar el caso.

El paquete portable JSON acotado a 32 MiB contiene fuentes exactas, manifiestos y resultado esperado. La recuperación verifica versiones y reconstrucción integral de cada productor. Casos compatibles/bloqueados se reproducen; un resultado o fuente alterado no se valida por recalcular un hash. No ejecuta instrucciones ni busca fuentes externas.

## T81: vigencia e informe interno

El inventario actual incluye todas las fuentes del recorrido anterior, el nuevo transporte/manifiesto, cada calendario y cada fuente mensual T21. Se exige T46 al mismo instante UTC explícito y coincidencia exacta de ID/hash/localizador/contexto. Todas las fuentes deben ser vigentes según sus declaraciones sintéticas, y todos los cálculos compatibles, antes de mostrar retorno o renta actuales. Una fuente mensual vencida no se reemplaza por el manifiesto reciente.

El informe interno conserva el relato del inversor T56 y agrega el desglose mensual de renta potencial, pérdidas, concesiones y efectiva. Ante vencimiento, estimación, revisión pendiente, sustitución o bloqueo, retira cifras actuales y conserva el cálculo histórico recuperable. No hay TTL/reloj/monitor implícito, autoridad documental o aprobación profesional por marcar una declaración de prueba.

Perfil optativo con datos sintéticos, sin despliegue o decisiones reales. No acredita contratos, ocupación física, cobros, cobertura del seguro, reglas fiscales, datos de Lorena, financiación real ni cierre financiero de activos/devengos/TDC. Los originales, ejemplos previos, I01, criterios vacíos y pendientes profesionales se conservan.
