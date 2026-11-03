# T82–T84 — disponibilidad por tramos y renta parcial

## T82: capacidad, disponibilidad y fracción suministrada

El perfil sintético reproduce una fuente T21 de mes de referencia por cada tramo fechado y escala sus resultados por una fracción de mes suministrada. No calcula esa fracción a partir de días ni elige 30/360, actual/actual u otra convención. Fechas y base de prorrateo son declaraciones distintas: que la cuenta concilie no autentica su compatibilidad contractual. La fracción debe estar explícita, entre cero y uno, con referencia de base; desconocido no equivale a cero incluso con disponibilidad cero.

Se exige una capacidad física declarada por grupo y un inventario completo de esos mismos grupos en cada tramo T21, incluidos ceros explícitos. Las unidades de T21 representan disponibilidad propuesta y no pueden superar la capacidad, ser negativas o fraccionarias. Área y base de renta deben coincidir con la capacidad suministrada. Disponibilidad no equivale a ocupación física, contrato firmado, permiso de uso o entrega acreditada; puede aumentar o disminuir sólo mediante otro dato explícito del tramo.

Los tramos particionan exactamente el período semiabierto, en orden y sin huecos o solapamientos, y no cruzan el mes calendario de referencia. Cada fuente T21 conserva contexto, moneda, ID del tramo y un mes regular de referencia. Para un mes completo cubierto las fracciones suman exactamente uno; para el mes parcial del borde suman como máximo uno. Es una regla del perfil experimental, sin adopción contractual. Un mes omitido no se interpreta como disponibilidad cero.

Potencial, pérdida, concesión y renta efectiva del mes de referencia se multiplican por la misma fracción y se conservan separados. Los gastos T21 deben ser placeholders cero: el NOI y T76 siguen suministrando los gastos por separado. Ningún importe parcial se exporta ante faltantes, inventarios incompatibles o exceso de presupuesto aritmético. La disponibilidad ponderada se expresa como unidades-mes bajo las fracciones suministradas, sin afirmar ocupación ni exposición física medida por días.

## T83: conexión con el recorrido de caja e inversor

Se reproduce todo el paquete T77 de obra, misma deuda operativa, gastos, tenencia, venta y retorno T74. Cada período operativo requiere su propio T82 en inventario completo ordenado. Contexto, moneda, fechas y hashes NOI/caja deben coincidir exactamente. La renta efectiva por tramos iguala la fila residencial vinculada del NOI; las demás filas de ingreso se inventarían y son cero explícito dentro de este perfil residencial reducido.

La capacidad/grupos/área/base y el ID de ingreso residencial deben mantenerse entre períodos; la disponibilidad puede cambiar sólo en los tramos suministrados. No se completa ni sobrescribe el NOI. Cambiar disponibilidad o fracción exige nueva evidencia compatible y recalcular la cadena completa; un total de renta igual no permite superar capacidad o cambiar su inventario. Los períodos parciales T82 sólo se conectan si coinciden con la ventana operativa declarada, sin extender deuda o crear caja de apertura.

El camino compatible expone exactamente el ledger, EM/IRR y riesgos ya reproducidos. No añade rentas como otro cobro ni vuelve a restar gastos; no ajusta aportes, deuda o distribución para reparar el caso. Capital, equity retenido, CoC y reparto personal conservan sus pendientes. Cualquier fallo previo o de tramos retira el retorno exportable. El transporte JSON acotado a 32 MiB incluye fuentes exactas y resultado, reconstruye todas las etapas bajo versiones compatibles y conserva casos bloqueados; hashes recalculados no autentican resultados alterados.

## T84: vigencia e informe interno

El control actual exige el inventario completo de fuentes previo más el manifiesto/transporte nuevos, cada calendario por tramos y cada fuente T21 de referencia. La capacidad y bases están contenidas en las fuentes exactas de calendario, sin tratar su serialización como evidencia oficial independiente. T46 debe reproducirse al mismo instante UTC explícito con ID/hash/localizador/contexto exactos y todas las fuentes vigentes según sus declaraciones sintéticas.

El informe interno conserva aportes/cobros/normalización/EM/todas las raíces de IRR/riesgos y agrega disponibilidad, fracción y desglose de rentas por tramo, junto a los gastos por período. Un vencimiento, estimación, revisión pendiente, sustitución o cálculo bloqueado retira todas las cifras actuales y preserva la historia recuperable. No hay reloj/TTL/monitor ni aprobación implícita por una fecha o aceptación de prueba.

Datos sintéticos y perfil optativo: no acredita capacidad real, entrega, permisos, ocupación, contratos, convenciones de prorrateo, cobros, reglas fiscales, financiación o revisión profesional. No completa activos/devengos/TDC ni el PDF externo. Originales, I01, criterios vacíos y ejemplos anteriores intactos; PENDING, sin despliegue ni decisiones reales.
